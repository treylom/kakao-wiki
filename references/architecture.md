# kakao-wiki — Architecture

> provider 추상화, 데이터 흐름, 윈도우(Windows) 자동화 현실성 등급.
> 근거 = 프로덕션 KakaoTalk 수집 파이프라인의 내보내기 자동화 조사.

## 데이터 흐름

```
collect(room, provider)
   │   provider ∈ {macos(GREEN), manual(GREEN), windows(spike-pending), db(experimental)}
   ▼
raw export  (out/<ROOM>-<DATE>.raw.csv  또는 .txt)
   │   normalize.py  (봇/공지 필터, since 컷, 순수 파서 — GUI 무관)
   ▼
normalized.json  {schema_version, proof_class, source, count, unique_users,
                  filtered_bot_announcement, messages:[{time,user,msg}] ...}
   ├─► store_to_wiki.py  →  vault/<subdir>/<ROOM>-<DATE>.md  (LLM wiki 적재)
   └─► digest(요약) ──► [검증] ──► send(channel, msg)
                          │            channel ∈ {kakao, discord, slack}
                          ├ length_gate.py   : send.py 안에서 자동 실행(발송 前 길이)
                          └ citation_gate.py : 직접 실행(digest 안 인용을 raw export 와 verbatim 대조)
```

두 게이트는 normalized.json 이 아니라 **digest(요약문)** 를 검사한다.

## provider 추상화 계약

각 provider 는 `(room, out_dir) → raw_export_path` 한 가지를 만족하면 교체 가능:

| provider | 메커니즘 | OS | 상태 | 비고 |
|---|---|---|---|---|
| `manual` (collect.py 안) | 사용자가 카카오톡에서 직접 내보낸 txt/csv 를 자동 탐색해 이어받음 | 모든 OS(macOS 가 아니면 기본값) | **GREEN** | GUI 자동화 없음. 자동 탐색한 파일은 방 이름 검증(fail-fast) |
| `macos_osascript.sh` | KakaoTalk GUI 메뉴를 osascript(AX)로 클릭 → 텍스트 export CSV | macOS | **GREEN** | GUI 내보내기 레시피 복제·일반화. Kakao mutex + 방 hard-assert(GUI·CSV) |
| `windows_pywinauto.py` | 방 창의 ≡ 메뉴 → 대화 내보내기 → 텍스트만 저장(pywinauto UIA, 안 잡히는 버튼은 좌표 폴백) | Windows | **spike-pending** | 실기 end-to-end 검증 전까지 성공으로 보고하지 않음(검증 플래그 없이는 체크리스트 출력 후 exit 4) |
| `db_kakaocli.sh` | kakaocli auth(키유도) → `kakaocli messages` 로 DB 직접 read | macOS(주)·Windows(미검증) | **experimental** | GUI 를 거치지 않아 가장 견고. 키유도 성공 시만 |

normalize.py 가 CSV/txt 를 동일 normalized 스키마로 흡수 → 하위(store/send)는 provider 무관.

## 사용자 자격증명(무인) 흐름 — Windows (설계 결정, 2026-06)

기본 provider 계약 `(room, out_dir) → raw` 는 **로그인·방 열림을 가정**한다. Windows 에서 사람 개입 없이 돌리려면(`--unattended`) 그 앞에 두 단계를 더한다(`_unattended_prelude`):

```
[로그인]     로그인 화면이면 비밀번호 칸(Edit[1])에 비밀번호만 입력 → Enter
             (이미 세션 유지면 skip)              · 비밀번호는 출력하지 않음 (_credentials.py)
   ▼
[방 자동오픈]  키보드 검색 → 방이름 타이핑 → Enter (좌표 클릭 ❌)
   ▼
[export]      방 창 ≡ 메뉴 → 대화 내보내기 → 텍스트만 저장
```

- 자격증명 = `_credentials.py`(env → `~/.kakao-wiki/credentials.env` → `<repo>/.env`). 공개 레포 미저장, 비밀번호 비노출(`Secret` 래퍼).
- 검색 단축키(`KW_SEARCH_HOTKEY`)와 로그인 창 타이틀(`KW_LOGIN_WINDOW_RE`)은 ENV 로 바꿀 수 있고, 실기 측정이 더 필요한 항목입니다(`_login_if_needed`/`_open_room_via_search`). 실기 spike 전엔 검증 플래그 없이 실행되지 않습니다.
- **단일 세션 제약**: PC 카카오톡은 한 계정에 PC 한 대만 로그인할 수 있어서, 다른 곳에서 로그인하면 다른 PC 의 세션이 끊길 수 있습니다. 플랫폼 제약이고 도구 결함은 아닙니다.
- **프로덕션 파이프라인과의 차이**: `docs/WORKFLOW.md` 의 프로덕션 파이프라인은 자동 로그인을 하지 않고 로그인을 사람에게 맡깁니다. 이 스킬의 무인 로그인은 Windows 스캐폴드에 얹은 선택 기능입니다.
- 검증: `tests/test_windows_provider_contract.py` 가 비밀번호 마스킹(`Secret`), 기본 로그인 창 패턴, WSL→Windows 경로 변환만 확인합니다. UI 자동화는 spike-pending 입니다.

## Windows 현실성 등급 (내보내기 자동화가 실제로 되는가)

| 방식 | 등급 | 근거 |
|---|---|---|
| 방 메뉴 → 대화 내보내기 → 텍스트만 저장 | 🟢 가능(최우선) | 2026-06-25 에 실기에서 손으로 경로를 측정함. 클릭 위치는 좌표 폴백(ENV)으로 조정 |
| `Ctrl+S` → 로컬 txt | ⚪ 미확인 | 이 레포의 provider 코드는 쓰지 않으며, 레포에 실기 확인 기록이 없음 |
| 텍스트만 보내기 → 이메일 | 🟠 제약 큼 | 로컬 파일 아님 → 이메일 fetch 단계 추가(무인 비권장) |
| DB 직접(kakaocli 포팅) | ⚪ 검증 필요 | 가장 견고하나 Windows 키유도 spike 선결 |

→ Windows provider 는 🟢 메뉴 내보내기 경로를 스캐폴드로 구현합니다. 단 **실기 spike 1회로 셀렉터/클릭 위치를 확정** 한 뒤에만 GREEN 으로 올립니다(현재 spike-pending). 불가(❌) 등급 항목은 없습니다.

## 도구 선택 (Windows GUI 자동화)
- **pywinauto** (UIA backend) — Python·객체수준 접근, macOS AX 모델과 1:1, CI 친화 = 1순위.
- **AutoHotkey** — UIA 컨트롤 클릭 빠름, 단독 exe. 키 입력 위주 흐름 보조.
- **PowerShell UIAutomation** — .NET 내장, 추가 런타임 0(장황).

## 라이브 파이프라인 비침습 (guardrail)
- 본 스킬은 프로덕션 파이프라인 산출물의 **복제·일반화**(import/symlink 아님). 원본 파이프라인 파일 수정 0.
- 유일 공유 = `/tmp/kakao-gui.lock`(Kakao GUI mutex) → 동시 GUI 점유를 직렬화합니다. 단 macOS 스크립트는 90초 기다린 뒤 락을 넘겨받고(내보내기는 최대 600초 걸릴 수 있음), 이때는 방 검증(GUI 창·CSV 파일명)이 마지막 방어선입니다.

## 검증 사다리
- macOS provider = **scenario-replay**(실 KakaoTalk export 1회) GREEN — `macos-provider.md` 검증 로그.
- Windows provider = 실기 end-to-end 미검증 = spike-pending. 계약 테스트(`tests/test_windows_provider_contract.py`: 비밀번호 마스킹·기본 로그인 창 패턴·경로 변환)만 자동 시험을 통과합니다.
- normalize.py = **deterministic** — 코드로 만든 txt 샘플 시험(`tests/test_normalize_pc_txt.py`, `tests/test_normalize_windows_txt.py`)으로 확인합니다. CSV 입력 시험 파일은 레포에 없습니다(macOS 검증 로그의 실 CSV 1회뿐).
