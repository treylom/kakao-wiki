# kakao-wiki

**카카오톡** 채팅방 대화를 구조화된 노트로 만들어 내 옵시디언 / LLM 위키 저장소에 쌓고, 필요하면 요약을 다시 카카오톡·디스코드·슬랙으로 보내는 스킬입니다.

(English README: [README.en.md](README.en.md))

📈 이 스킬의 원본 파이프라인이 실제로 하루 두 번 도는 흐름(차트 + 단계별 명세): [docs/WORKFLOW.md](docs/WORKFLOW.md)

흐름은 6단계입니다. 1 수집·2 정규화는 필수이고, 3~6은 필요에 따라 고르는 선택 단계입니다(저장은 정규화 직후 언제든 할 수 있습니다). 직접 만든 파이프라인이 흔히 빠뜨렸다가 뒤늦게 후회하는 **검증(4)** 자리가 게이트로 채워져 있는 게 이 스킬의 핵심입니다:

```
1 수집(collect) → 2 정규화(normalize) → 3 요약(summarize)
→ 4 검증(verify: 길이·인용) → 5 발송(send) → 6 저장(record)
```

**수집 → 정규화**만 필수입니다. 요약·검증·발송·저장은 선택이지만, **요약을 보낼 때 길이 게이트는 `send.py` 안에서 자동으로 돌고**, **인용이 든 요약이면 인용 게이트를 직접 먼저 돌리세요.**

카카오톡은 공개 API가 없어서, 수집은 카카오톡 앱 자체의 **대화 내보내기(export) 메뉴**를 자동으로 구동합니다. 그 뒤의 파싱·검증·저장·다채널 발송은 LLM 없이 같은 입력에 같은 결과를 내는 파이썬 코드가 처리합니다.

> 이 도구를 어떻게 쓰고 어떤 데이터를 모으는지는 사용자 본인의 책임입니다.

---

## 한눈에 — provider(수집 백엔드)별 상태 (현재 상태 그대로)

이 저장소는 모든 경로가 다 된다고 포장하지 않습니다. 각 provider가 스스로 자기 상태를 표시합니다.

| provider | 하는 일 | OS | 상태 |
|----------|---------|----|------|
| `macos` (macOS 기본) | 카카오톡 GUI 내보내기 메뉴를 `osascript`(접근성)로 구동 → CSV 파싱 | macOS | ✅ **검증됨(GREEN)** — 실제 export 1회로 검증 (`references/macos-provider.md`) |
| `manual` (Windows/WSL 기본) | 사용자가 카카오톡에서 **Ctrl+S** 로 직접 내보낸 txt/csv 를 이어받아 처리 — `--input` 생략 시 기본 저장 경로에서 방 이름이 맞는 파일을 먼저, 그다음 가장 최근 파일을 자동 탐색 | 전 OS | ✅ **GREEN** — 내보내기는 카카오톡 공식 기능, 이후는 LLM 없이 도는 파서 |
| `windows` | `pywinauto`로 카카오톡의 대화 내보내기 메뉴를 자동 구동하는 골격 | Windows | ⚠️ **검증 대기(spike-pending)** — 화면 요소에 기대지 않는 부분은 다 만들었지만, 실제 윈도우 카카오톡에서 확인하기 전까지는 성공했다고 표시하지 않습니다(기본은 0이 아닌 코드로 종료) |
| `db` | 로컬 카카오톡 DB를 `kakaocli`로 직접 읽기 | macOS(Win 미정) | 🧪 **실험적** — 호스트에서 `kakaocli` 키 유도가 성공해야 동작 |

macOS 는 `macos`, Windows/WSL 은 `manual` 경로를 쓰세요. `windows`/`db`는 **숨기지 않고 표시**해 둔 미완성 경로입니다(기여 환영).

### Windows에서 지금 바로 쓰려면 — katok-windows + 공식 내보내기 (권장)

Windows 카카오톡은 로컬 대화 DB가 강하게 보호되어 있어 macOS처럼 앱 DB를 자동으로 직독하는 경로가 없습니다. 그래서 Windows의 **실제로 쓸 수 있는 경로**는 카카오톡 공식 **"대화 내보내기(.txt)"** 기반입니다:

- **대화 검색이 목적이면** → [katok-windows](https://github.com/Hostingglobal-Tech/katok-windows)를 쓰세요. 내보낸 `.txt`를 색인해 keyword / BM25 / semantic 검색을 제공하는 CLI입니다(이 저장소와는 별개 프로젝트).
- **위키 저장(이 스킬)이 목적이면** → 같은 공식 내보내기로 뽑은 `.txt`를 `manual` provider 에 넣으면 됩니다:
  ```bash
  # Ctrl+S 로 저장한 파일 경로를 직접 지정하거나 —
  python3 scripts/collect.py --room "<방이름>" --provider manual --input <저장한.txt> --out ./out
  # 권장 위치(C:\Users\<이름>\.kakao-wiki\exports · 문서 · 다운로드 · 바탕화면)에 저장했다면 --input 생략(자동 탐색):
  python3 scripts/collect.py --room "<방이름>" --provider manual --out ./out
  ```
  WSL 에서는 `C:\Users\<이름>\...` 가 `/mnt/c/Users/<이름>/...` 이며 `--input` 은 두 표기 모두 인식합니다. 자동 탐색은 방 이름이 파일 이름에 있는 파일을 먼저 고르고, 그다음 최신 파일을 고릅니다. 자동으로 고른 파일에서 방 이름을 확인하지 못하면 엉뚱한 방을 수집하지 않도록 오류(종료 코드 4)로 멈춥니다(`--input` 으로 직접 지정한 파일은 경고만 합니다).
  파서는 PC 카톡의 `[이름] [오후 2:30]` 형식(날짜 구분선·여러 줄 메시지 포함)과 `2026. 6. 18. 오후 8:19, 이름 : 메시지` 형식을 모두 지원합니다(한국어 카카오톡의 오전/오후 표기 기준). 내보내기 자체를 자동화하는 `windows` provider는 아래대로 여전히 spike-pending입니다.
- **뭐부터 할지 모르겠으면** → 환경 진단 명령 하나로:
  ```bash
  python3 scripts/windows_guide.py --room "<방이름>"
  ```
  Windows/WSL 감지 → Ctrl+S 단계 안내 → 내보내기 파일 자동 탐색 미리보기 → katok-windows 설치 감지·설치 명령 안내까지 출력합니다.

즉 Windows에서는 "공식 내보내기 → katok-windows로 검색 / kakao-wiki로 위키화"가 지금 바로 되는 조합입니다.

- **카카오톡으로 요약·링크 되돌려 보내기(send)** → Windows 채널(`scripts/providers/windows_send.py`, pywinauto)이 추가돼 있습니다 — 단 수집 provider와 같은 원칙으로 **실제 PC에서 검증하기 전까지 spike-pending**(기본은 0이 아닌 코드로 종료, 검증 절차는 파일 안 체크리스트). macOS에서는 기존 kmsg 경로로 지금도 동작합니다. WSL·리눅스에서는 카카오톡 발송을 지원하지 않습니다(카카오톡 발송은 macOS 또는 Windows 네이티브 전용).

---

## 준비물

- **Python 3.9+** (핵심 흐름은 표준 라이브러리만 — 별도 설치 불필요)
- **macOS provider**: 카카오톡 데스크톱 앱 + `kmsg` 명령줄 도구(PATH 에 있어야 하며, 이 저장소에는 들어 있지 않습니다) + 터미널과 `kmsg` 에 **접근성 권한** 부여 (시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용). 카카오톡이 내보낸 파일을 `~/Downloads` 에 `KakaoTalk_Chat_*.csv` 로 저장해야 합니다(스크립트가 이 폴더만 지켜봅니다).
- **PDF 등 문서 변환을 같이 쓸 때**: `kordoc` + `pdfjs-dist@4` (아래 "문서 변환" 참고)
- **send.py**: `DISCORD_BOT_TOKEN`(디스코드) / `SLACK_WEBHOOK_URL`(슬랙 Incoming Webhook) / `kmsg`(카카오톡, macOS) — 보낼 때만 필요

---

## 설치

```bash
git clone https://github.com/treylom/kakao-wiki.git
cd kakao-wiki
# 핵심 흐름은 의존성 0. (윈도우 provider만 선택적으로: pip install pywinauto)
```

또는 Claude Code / 에이전트 스킬 폴더에 `kakao-wiki` 스킬로 넣어 쓸 수 있습니다(`SKILL.md` 참고).

---

## 사용법

`ROOM` = 정확한 카카오톡 방 이름, `OUT` = 작업 폴더. 아래 번호는 위 흐름의 단계 번호와 같습니다.

### 1~2. 수집 · 정규화
```bash
# macOS (기본, 검증됨):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out

# Windows / WSL (기본 = manual): 카카오톡에서 Ctrl+S 로 내보낸 txt 를 이어받음
python3 scripts/collect.py --room "<ROOM>" --provider manual [--input <내보낸.txt>] --out ./out
```
→ `out/<ROOM>-<DATE>.raw.csv`(또는 .txt) 와 `out/<ROOM>-<DATE>.normalized.json` 생성. 수집(1)과 정규화(2)가 이 한 번의 실행으로 끝납니다.

### 3. (선택) 요약
요약 스타일을 고르는 방법은 아래 "요약 스타일 선택" 절을 보세요.

### 4. (선택) 발송 전 검증 — 길이·인용 게이트
```bash
# 길이 — 채팅앱이 조용히 잘라버릴 메시지를 거부. send.py 안에서도 자동으로 돕니다.
python3 scripts/gates/length_gate.py --file summary.txt --max-chars 3900
# 인용 — 요약이 사람 말을 인용하면, 따옴표 안 문장은 원본에 그대로 있어야 합니다. (send.py 가 돌려 주지 않으니 직접 실행)
python3 scripts/gates/citation_gate.py summary.txt out/<ROOM>-<DATE>.raw.csv
```
- **잘린 메시지는 "뒷부분 없는 메시지"가 아니라 "그냥 짧은 메시지"로 보입니다** — 잘렸다는 사실이 아무 데도 안 남아서, 길이 게이트가 없으면 보낸 사람도 모릅니다. 그래서 `send.py`는 발송 관문 한 곳에서 길이 게이트를 자동으로 돌립니다(채널별 기본값: 카톡 3900 · 디스코드 2000 · 슬랙 4000, `--max-chars`로 조정).
- 두 게이트 모두 **못 재는 것을 매 실행 출력**합니다(길이 게이트는 "정확성·인용 충실도·주제 커버리지·발행 적절성은 안 본다"고 매번 찍습니다). 길이 게이트를 우회하는 `--waiver "<사유>"`는 `length_gate.py` 와 `send.py` 에만 있고, 사유는 출력됩니다. 인용 게이트에는 우회 옵션이 없습니다.
- **인용 게이트는 짧은 인용을 검사하지 않습니다.** 따옴표 안 문장이 `--min-len`(기본 4자)보다 짧으면 건너뛰고, 건너뛴 인용의 개수와 내용을 출력합니다. 짧은 말을 인용했다면 그 목록을 눈으로 확인하세요.
- 두 게이트의 종료 코드: 0 통과 · 2 실패 · 64 사용법 오류(알 수 없는 옵션 등).
- **한 번도 실패한 적 없는 게이트 = 완벽하거나 안 도는 것.** 게이트를 *추가*하는 것보다 "이 게이트가 지금 실제로 도는가"를 물을 수 있는 게 중요합니다 — 그래서 게이트 파일이 없으면 `send.py`는 발송을 **거부**합니다(게이트를 지우는 게 통과 지름길이 되지 않도록). 우회는 `--allow-missing-gate` 명시로만.
- ⚠️ **글자 수 vs 바이트**: 길이는 유니코드 **글자 수**로 셉니다(한글 1자 = 1). 로그·도구가 "N chars"라 적고 실제로는 바이트(한글이 3배로 부풀려짐)인 경우가 흔하니, 직접 만든 글자 수 세기 코드가 바이트를 세는지 글자를 세는지 한 번 확인하세요.
- **발행 적절성은 도구가 판정하지 않습니다** — 이 게이트들은 *충실도*(길이·인용 정확성)만 봅니다. "이 내용을 내보내도 되는가"는 방·독자·규칙에 달린 별개 축이라, 막아야 할 내용(개인정보 등)이 있으면 사용자가 자기 검사를 여기 끼워 넣으세요.

### 5. (선택) 요약 발송
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target "<#channel>" --message-file summary.txt
```
`send.py`는 *인터페이스*만 통일합니다. 실제 전송 방식은 채널마다 다릅니다(카카오톡 = `kmsg` / 디스코드 = REST API / 슬랙 = Incoming Webhook, 환경변수 `SLACK_WEBHOOK_URL` 이 없으면 아무것도 보내지 않고 종료 코드 3으로 끝납니다 — `references/send-channels.md`). 발송 관문에서 길이 게이트가 먼저 돌고, 초과 시 아무것도 안 보냅니다(`--waiver "<사유>"`로 우회, 사유는 출력됨).

`send.py` 는 카카오톡·디스코드·슬랙 어느 쪽도 메시지가 실제로 도착했는지는 확인하지 않습니다(종료 코드는 명령이나 HTTP 요청이 끝났다는 뜻일 뿐입니다). 중요한 발송은 직접 확인하세요. 주요 종료 코드: 1 토큰·방 이름·빈 본문 등 입력 문제 · 2 길이 게이트 거부(디스코드·슬랙 HTTP 오류도 2) · 3 슬랙 웹훅 미설정 · 66 게이트 파일 없음 · 6 윈도우 카카오톡에 키 입력은 보냈으나 도착은 확인 못 함. 카카오 발송은 `kmsg`·윈도우 발송기의 종료 코드를 그대로 돌려주므로 윈도우 경로에서는 2·3 의 뜻이 다르고 5(화면 단계 실패)가 더 있습니다 — 전체 목록은 `references/send-channels.md`.

### 6. (선택) 저장소에 저장
```bash
python3 scripts/store_to_wiki.py \
  --normalized out/<ROOM>-<DATE>.normalized.json \
  --room "<ROOM>" \
  --vault "/내/저장소/절대경로" \
  --subdir "Research/<ROOM>"
```
→ 프론트매터(`type`·`tags`·`aliases`·통계) 붙은 마크다운 노트 생성. `--room` 을 빼면 파일 이름의 첫 `-` 앞까지만 방 이름으로 쓰기 때문에, 방 이름에 `-` 가 있으면 잘리니 꼭 넣으세요. 저장은 정규화(2) 뒤 언제든 할 수 있어 발송과 순서가 상관없습니다.

---

## 무인 수집 (Windows 사용자 자격증명 방식 — 설계됨, 실측 대기)

Windows에서 사람 개입 0으로 수집(자동 로그인 + 방 자동오픈 + export)하려면:

```bash
# 1) 자격증명을 로컬에 설정 (절대 커밋 금지 — .gitignore 처리됨)
#    환경변수:  set KW_KAKAO_ID=...  &  set KW_KAKAO_PW=...
#    또는 레포 밖 파일:  ~/.kakao-wiki/credentials.env  (KW_KAKAO_ID= / KW_KAKAO_PW=)
# 2) 무인 실행
python scripts/providers/windows_pywinauto.py --room "<ROOM>" --out ./out \
  --unattended --i-have-verified-on-real-windows
```

- **자격증명은 사용자 소유**: ID/PW는 *본인이 로컬에 직접* 설정합니다. 공개 레포에 비밀번호를 저장하지 않으며, 코드는 비밀번호를 로그에 남기지 않도록 만들었습니다(`scripts/providers/_credentials.py`). 자동 로그인은 로그인 창의 비밀번호 칸에만 입력하고 ID 는 입력하지 않습니다. 단 로그인 창에서 비밀번호 칸을 찾지 못하면 포커스가 있는 칸에 입력할 수 있으니, 실제 Windows에서 확인하기 전에는 화면 어디에도 안 보인다고 단정하지 마세요.
- **상태**: 자격증명 불러오기는 구현돼 있고, 비밀번호가 문자열 표현(repr)에서 가려지는 것만 단위 테스트로 확인했습니다. 자격증명은 환경변수 → `~/.kakao-wiki/credentials.env` → `<repo>/.env` 순서로 찾습니다. 로그인/검색 화면 자동화는 실제 윈도우 카카오톡에서 확인해 좌표·컨트롤을 확정한 뒤에 GREEN 으로 올립니다(`references/windows-provider-spike.md`). 내보내기 단계는 방 메뉴(≡) → 대화 내보내기 → 텍스트만 저장 순서를 좌표로 누르고, 좌표는 환경변수(`KW_MORE_X_FROM_RIGHT` 등)로 고칠 수 있습니다.

> ⚠️ **단일 세션 제약(카카오톡 플랫폼)**: 카카오톡 PC 버전은 한 계정이 한 대의 PC에서만 로그인됩니다. 무인 수집이 로그인하면 다른 PC에서 쓰던 카카오톡의 로그인이 끊길 수 있습니다. *수집이 도는 동안만* 이 PC가 세션을 가져가는 식으로 운영하세요. 도구 결함이 아니라 카카오톡 자체 제약입니다.

> 참고: [docs/WORKFLOW.md](docs/WORKFLOW.md) 의 운영 파이프라인은 위 세션 문제 때문에 일부러 자동 로그인을 하지 않고 사람이 로그인합니다. 이 스킬의 무인 모드는 그것과 별개로 더한 선택 기능입니다.

---

## 요약 스타일 선택 (사용자 커스텀)

발송할 요약의 **말투·형식을 골라** 쓸 수 있습니다. 환경을 감지해 안내합니다:

- **`/prompt` 스킬이 있는 환경**이면 `summarize.py` 가 그 스킬을 쓰라는 안내를 한 줄 출력합니다. 스킬을 직접 호출하지는 않으며, 출력되는 프롬프트는 이 경우에도 번들 프리셋 그대로입니다.
- 번들된 프리셋(`prompts/summary-styles.md`)에서 스타일을 고릅니다 — 예: `brief`(간결 3줄) · `detailed`(상세) · `bullets`(불릿) · `formal`(존댓말 보고체) · `casual`(편한 반말). 모든 프리셋에는 공통 규율(해석·편집자 말투 금지 · 인용은 원문 그대로 · 길이 예산)이 들어 있습니다.

```bash
# 프리셋 목록 보기
python3 scripts/summarize.py --list
# 스타일 골라 요약 프롬프트 출력(요약 LLM에 그대로 전달)
python3 scripts/summarize.py --style brief --normalized out/<ROOM>-<DATE>.normalized.json
```
자세한 건 `prompts/summary-styles.md` 와 `SKILL.md`("3. Summarize") 참고.

---

## 문서 변환 (선택 — kordoc 연계)

수집한 첨부/문서가 **HWP·HWPX·복잡한 표 XLSX/DOCX·한국어 PDF**처럼 그냥 못 읽는 형식이면 [kordoc](https://github.com/chrisryugj/kordoc)으로 md 변환 후 쓸 수 있습니다.

⚠️ **PDF는 `pdfjs-dist@4` 가 kordoc 과 같은 `node_modules` 에 있어야 합니다**(v6 비호환). `npx -y kordoc <pdf>` 단독은 PDF에서 실패하니, PDF를 쓸 땐 한 번만:
```bash
mkdir kordoc-tmp && cd kordoc-tmp && npm init -y && npm install kordoc pdfjs-dist@4
./node_modules/.bin/kordoc <파일>.pdf -d ./out
# HWPX/DOCX/XLSX 만이면 추가 설치 없이: npx -y kordoc <파일>.hwpx -d ./out
```

---

## 수집 원리 (macOS)

카카오톡은 내보내기가 GUI 메뉴뿐이라, `macos_osascript.sh`가 사람이 클릭하는 순서를 접근성으로 재현합니다. **엉뚱한 방을 수집하지 않도록** 두 단계 검증을 넣었습니다:

1. 앱 포커스 → 채팅 탭 → 대상 방 열기
2. **GUI 방 검증** — 내보내기 전에 방 창이 실제로 있는지 확인
3. 설정 → 대화 내용 관리 → "텍스트 파일로 저장" → 확인
4. **CSV 방 검증** — 나온 CSV의 *파일 이름*에 대상 방 이름이 들어 있는지 확인(한글 NFC substring). 아니면 즉시 오류로 멈춥니다(fail-fast).

전역 잠금(`/tmp/kakao-gui.lock`)으로 동시 실행을 막습니다. 다른 실행이 잠금을 쥐고 있으면 최대 90초 기다린 뒤 잠금을 넘겨받아 진행하고(그때는 위 방 검증 두 가지가 충돌을 막습니다), 600초 넘게 남은 잠금은 정리합니다. 셀렉터는 카카오톡 macOS UI(창 이름·버튼 인덱스·메뉴 텍스트)에 의존하므로, 앱 UI가 바뀌면 셀렉터를 다시 잡아야 합니다(검증 단계가 엉뚱한 방을 조용히 수집하는 대신 오류를 내고 멈춥니다).

---

## 폴더 구조

```
kakao-wiki/
  SKILL.md                  # 스킬 매니페스트(에이전트 로드용)
  docs/
    WORKFLOW.md             # 원본 운영 파이프라인: 차트 + 단계별 명세
  scripts/
    collect.py              # provider 디스패치: collect(방, provider) -> normalized.json
    normalize.py            # raw export(CSV/txt) -> 정규화 메시지(GUI 무관 파서)
    store_to_wiki.py        # normalized -> 저장소 마크다운 노트
    summarize.py            # 요약 스타일 선택(/prompt 감지 + 프리셋)
    send.py                 # send(채널, 메시지): kakao | discord | slack (관문에서 길이 게이트)
    windows_guide.py        # Windows/WSL 환경 진단 + 사용 경로 안내(읽기 전용)
    gates/
      length_gate.py        # 발송 전: 채팅앱이 조용히 자를 메시지를 거부(채널별 기본값 + 우회)
      citation_gate.py      # 인용문이 원본 export 에 verbatim 존재하는지 검증(짧은 인용은 건너뛰고 목록 출력)
    providers/
      macos_osascript.sh    # 검증됨: 카카오톡 GUI export -> CSV (잠금 + 방 검증)
      windows_pywinauto.py  # 검증대기: 메뉴 export + 무인 로그인·방오픈 골격 (좌표 ENV)
      windows_send.py       # 검증대기: Windows 카카오톡 발송(pywinauto)
      _credentials.py       # 사용자 자격증명 로딩 (로컬 ID/PW, 비밀번호 비노출 — ID/PW 는 로컬에만 두고 커밋하지 않음)
      db_kakaocli.sh        # 실험적: kakaocli DB read -> CSV
  tests/                    # 파서·윈도우 provider 계약 단위 테스트 (python3 -m unittest)
  prompts/
    summary-styles.md       # 요약 스타일 프리셋 프롬프트
  references/
    architecture.md         # provider 추상화 + 데이터 흐름 + 윈도우 현실성 등급
    macos-provider.md       # osascript 의존 지점 + 검증 로그
    windows-provider-spike.md  # 윈도우 스파이크 체크리스트
    send-channels.md        # 카카오(kmsg) / 디스코드(REST) / 슬랙(Webhook) 메모
```

---

## 기여

가장 값진 기여는 **윈도우 provider 스파이크 완성**(`references/windows-provider-spike.md`에 무엇을 검증해야 하는지 정리)과 **db provider 강화**입니다. 실제 머신에서 검증하기 전에는 어떤 provider도 "검증됨(GREEN)"으로 올리지 말아 주세요.

## 라이선스

MIT — [LICENSE](LICENSE) 참고.
