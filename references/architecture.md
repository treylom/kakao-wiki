# kakao-wiki — Architecture

> provider 추상화 + 데이터 흐름 + 윈도우(Windows) 자동화 현실성 등급.
> 근거 = 프로덕션 KakaoTalk 수집 파이프라인의 내보내기 자동화 조사.

## 데이터 흐름

```
collect(room, provider)
   │   provider ∈ {macos(GREEN), windows(spike-pending), db(experimental)}
   ▼
raw export  (out/<ROOM>-<DATE>.raw.csv  또는 .txt)
   │   normalize.py  (봇/공지 필터, since 컷, 순수 파서 — GUI 무관)
   ▼
normalized.json  {messages:[{time,user,msg}], count, users, first/last_time}
   ├─► store_to_wiki.py  →  vault/<subdir>/<ROOM>-<DATE>.md  (LLM wiki 적재)
   └─► (선택) 분석/인용검증: aktofu citation_gate.py / topic_boundary_gate.py 재사용
                                     │
                                     ▼
                              digest(요약) ──► send(channel, msg)
                                                channel ∈ {kakao, discord, slack}
```

## provider 추상화 계약

각 provider 는 `(room, out_dir) → raw_export_path` 한 가지를 만족하면 교체 가능:

| provider | 메커니즘 | OS | 상태 | 비고 |
|---|---|---|---|---|
| `macos_osascript.sh` | KakaoTalk GUI 메뉴를 osascript(AX)로 클릭 → 텍스트 export CSV | macOS | **GREEN** | aktofu 레시피 복제·일반화. Kakao mutex + 방 hard-assert(GUI·CSV) |
| `windows_pywinauto.py` | 대화창 포커스 → `Ctrl+S` 로컬 txt 저장(pywinauto UIA) | Windows | **spike-pending** | 셀렉터·키 실검증 전 성공 가장 ❌ (비-0 exit 가드) |
| `db_kakaocli.sh` | kakaocli auth(키유도) → DB 직접 read | macOS(주)·Windows(미검증) | **experimental** | GUI 우회 = 최견고. 키유도 성공 시만 |

normalize.py 가 CSV/txt 를 동일 normalized 스키마로 흡수 → 하위(store/send)는 provider 무관.

## 무인(unattended) 흐름 — Windows ⓐ (재경님 결정 2026-06-19)

기본 provider 계약 `(room, out_dir) → raw` 는 **로그인·방 열림을 가정**한다. Windows 무인 요건(사람 개입 0)은 그 앞에 두 단계를 더한다(`_unattended_prelude`):

```
[ⓐ 로그인]  자격증명(로컬 ID/PW) → 로그인 화면이면 키보드 ID→Tab→PW→Enter
            (이미 세션 유지면 skip)              · 비밀번호 echo 0 (_credentials.py)
   ▼
[방 자동오픈]  키보드 검색 → 방이름 타이핑 → Enter (좌표 클릭 ❌)
   ▼
[export]      현 provider Ctrl+S (기존 검증 경로)
```

- 자격증명 = `_credentials.py`(env → `~/.kakao-wiki/credentials.env` → `<repo>/.env`). 공개 레포 미저장, 비밀번호 비노출(`Secret` 래퍼).
- 로그인/검색 셀렉터·단축키는 **ENV 주입 + 🔬 실측 TODO**(`_login_via_keyboard`/`_open_room_via_search`). 실기 spike 전엔 honesty guard 로 실행 차단.
- **단일 세션 제약**: 카카오톡 한 계정=한 기기 → 무인 로그인 시 다른 기기 세션 끊김. Mac AK 파이프라인과 동일 모델(필요 시에만 세션 회수). 플랫폼 제약(도구 결함 아님).
- 검증: 자격증명 레이어 = **deterministic GREEN**(Secret 마스킹·로딩 우선순위 확인). UI 자동화 = spike-pending.

## Windows 현실성 등급 (내보내기 자동화가 실제로 되는가 — 연구 §2.2)

| 방식 | 등급 | 근거 |
|---|---|---|
| `Ctrl+S` → 로컬 txt | 🟢 가능(최우선) | Windows 카톡이 단축키로 로컬 txt 저장 지원. Mac 다단 메뉴보다 단순(키 1발+폴링) |
| 메뉴 → 내부저장소 저장 | 🟡 가능(제약) | 로컬 저장되나 메뉴 UIA 셀렉터 재유도·이미지 폴백 필요 |
| 텍스트만 보내기 → 이메일 | 🟠 제약 큼 | 로컬 파일 아님 → 이메일 fetch 단계 추가(무인 비권장) |
| DB 직접(kakaocli 포팅) | ⚪ 검증 필요 | 최견고하나 Windows 키유도 spike 선결 |

→ Windows provider 는 🟢 `Ctrl+S` 경로를 scaffold. 단 **실기 spike 1회로 셀렉터/키 확정** 후에만 GREEN 승격(현재 spike-pending). 불가(❌) 등급 항목은 없음.

## 도구 선택 (Windows GUI 자동화)
- **pywinauto** (UIA backend) — Python·객체수준 접근, 우리 macOS AX 모델과 1:1, CI 친화 = 1순위.
- **AutoHotkey** — UIA 컨트롤 클릭 빠름, 단독 exe. 키 입력 위주 흐름 보조.
- **PowerShell UIAutomation** — .NET 내장, 추가 런타임 0(장황).

## 라이브 파이프라인 비침습 (guardrail)
- 본 스킬은 aktofu 산출물의 **복제·일반화**(import/symlink 아님). aktofu 파일 수정 0.
- 유일 공유 = `/tmp/kakao-gui.lock`(Kakao GUI mutex) → 동시 GUI 점유 시 직렬화(race 0).

## 검증 사다리 (code-quality §7)
- macOS provider = **scenario-replay**(실 KakaoTalk export 1회) GREEN — `macos-provider.md` 검증 로그.
- Windows provider = 미검증 = spike-pending(deterministic/replay 둘 다 미통과).
- normalize.py = **deterministic**(픽스처 CSV in→normalized out) 확인 가능.
