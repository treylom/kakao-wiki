# kakao-wiki — Windows provider (⚠️ SPIKE-PENDING / EXPERIMENTAL)

`scripts/providers/windows_pywinauto.py` — KakaoTalk Windows 의 대화 내보내기 메뉴
(방 창 ≡ → 대화 내보내기 → 텍스트만 저장)를 pywinauto(UIA)로 코드화한 **스캐폴드**입니다.
**실 검증 전이라 성공으로 보고하지 않습니다**(검증 플래그 없이 실행하면 체크리스트만 출력하고 비-0 exit).

## 왜 메뉴 내보내기 경로인가
코드가 따르는 경로는 2026-06-25 에 실제 Windows KakaoTalk 에서 사람이 손으로 측정한 것입니다
(`windows_pywinauto.py` 머리말): 트레이에서 창 복원 → 로그인 창 타이틀 "카카오톡" → 비밀번호 칸 `Edit[1]` →
메인 검색 → 방 창 ≡ 메뉴 → 대화 내보내기 → 텍스트만 저장. 창 클래스는 `EVA_Window`.
`Ctrl+S` 단축키 경로는 이 코드가 쓰지 않으며(키 입력을 보내지 않음), 이 레포에는 그 경로를 실기에서 확인한 기록이 없습니다.
(다른 방식: 메뉴 "모든 메시지 내부저장소 저장"=🟡, "텍스트만 보내기"=이메일=🟠, DB 직접=⚪.)

## 🚨 왜 spike-pending인가 (정직 원칙: 확인한 것만 GREEN 으로 적는다)
- KakaoTalk **Windows UI 요소(창 타이틀·컨트롤 식별자)는 Mac 과 다르다** → Mac 셀렉터 전부 무효.
- 위 경로를 손으로 측정했을 뿐, 이 스캐폴드 전체를 실기에서 끝까지 돌려 본 기록은 없다.
- 한국 앱은 custom-draw UI 가 흔해 UIA 노출이 약한 컨트롤이 있다 → ≡ 버튼·메뉴 항목은 이름으로 못 찾으면 창 기준 좌표 클릭으로 폴백한다(아래 ENV).
- **실기 1회 검증 없이 "완성" 보고 ❌.** 스크립트는 `--i-have-verified-on-real-windows` 없이는 체크리스트를 출력하고 exit 4 로 끝납니다. `collect.py --provider windows` 는 이 스크립트를 호출한 뒤 어떤 경우에도 중단합니다(가드).

## Spike 체크리스트 (이 전부 통과 후에만 GREEN 승격)
1. KakaoTalk Windows 설치·로그인.
2. 대상 방을 **더블클릭으로 대화창 오픈**(검색-리스트 상태 ❌ — macOS와 동형 함정).
3. 방 창의 ≡("더보기") → 대화 내보내기 → 텍스트만 저장 → 저장 다이얼로그가 뜨는지 확인. 클릭이 빗나가면 ENV 로 위치를 옮기고(아래 표) 값을 기록.
4. 저장 경로/파일명 패턴 확정(KakaoTalk 이 제안하는 이름을 그대로 두고 폴더만 `--out` 으로 옮김) → `normalize.py` txt 파서(`TXT_LINE_RE`)와 정합 확인(필요 시 파서 보강).
5. `pywinauto` backend='uia' 로 KakaoTalk 창/방 창 타이틀 정규식 재유도(`KW_KAKAO_TITLE_RE`, `KW_ROOM_TITLE_RE`).
6. UIA 약노출 컨트롤은 좌표 폴백 값(`KW_MORE_*`, `KW_EXPORT_MENU_*`, `KW_TEXT_ONLY_*`)으로 맞춤.
7. 1회 실 export 성공 후: `windows_pywinauto.py` 의 검증 플래그 가드 해제 +
   `collect.py` `run_windows` 의 SPIKE-PENDING 가드 해제 + `architecture.md`·`SKILL.md` 상태표를
   GREEN 으로 갱신 + 본 문서에 검증 로그 기록.

## 도구 선택지 (셋 다 UIA 접근 가능)
- **pywinauto**(UIA) — Python·객체수준, macOS AX 모델과 1:1, 1순위(본 scaffold).
- **AutoHotkey** — UIA 컨트롤 클릭 빠름·단독 exe, 키 입력 위주 폴백.
- **PowerShell UIAutomation** — .NET 내장, 추가 런타임 0.

## 셀렉터·좌표 = ENV 주입 (코드 수정 불요)
스파이크를 진행하는 사람은 코드를 고치지 않고 환경변수로 셀렉터와 클릭 위치를 맞춥니다
(`windows_pywinauto.py` 에서 읽는 변수 전체):

| ENV | 의미 | 기본값 |
|---|---|---|
| `KW_KAKAO_TITLE_RE` | KakaoTalk 메인/앱 창 타이틀 정규식 | `.*(KakaoTalk\|카카오톡).*` (EN+KR 동시 — 한글 로케일 "카카오톡" 자동 포함) |
| `KW_ROOM_TITLE_RE` | 대화방 창 타이틀 정규식 | `.*<방이름>.*` |
| `KW_MORE_X_FROM_RIGHT` / `KW_MORE_Y_FROM_TOP` | 방 창의 ≡ 버튼 클릭 위치(창 오른쪽·위쪽 가장자리에서 떨어진 픽셀) | 34 / 46 |
| `KW_EXPORT_MENU_X` / `KW_EXPORT_MENU_Y` | "대화 내보내기" 항목을 이름으로 못 찾을 때 클릭할 위치(방 창 왼쪽·위쪽 기준 픽셀) | 260 / 180 |
| `KW_TEXT_ONLY_X` / `KW_TEXT_ONLY_Y` | "텍스트만 저장" 항목을 이름으로 못 찾을 때 클릭할 위치(같은 기준) | 210 / 240 |
| `KW_DIALOG_WAIT_SEC` / `KW_FILE_WAIT_SEC` | 저장 다이얼로그/파일 대기(초) | 8 / 30 |
| `KW_LOGIN_WINDOW_RE` | 로그인 창 타이틀 정규식(`--unattended` 전용) | `카카오톡` |
| `KW_LOGIN_WAIT_SEC` | 로그인 창이 있는지 기다리는 시간(초)이자, 비밀번호 입력 뒤 기다리는 시간(초). 같은 변수를 두 곳에서 읽으며 값이 없을 때 기본값이 다름 | 3(창 확인) / 8(입력 뒤) |
| `KW_SEARCH_HOTKEY` | 방 검색 포커스 단축키(`--unattended` 전용) | `^f` |
| `KW_DATA_ROOT` / `KW_EXPORT_DIR` | 스크린샷·내보내기 폴더의 기준 위치를 정하는 보조 함수용 변수. 현재 `main()` 실행 경로는 `--out` 폴더를 쓰며 이 두 값을 읽지 않음 | `~/.kakao-wiki` / `<KW_DATA_ROOT>/exports` |

실행: `python scripts\providers\windows_pywinauto.py --room "<방>" --out .\out --i-have-verified-on-real-windows`
(플래그 없이 돌리면 체크리스트 출력 + exit 4 = 성공으로 보고하지 않음.)

## 무인(사용자 자격증명) 추가 spike — 로그인·방 자동오픈
기존 체크리스트(1~7)는 *방이 이미 열린* export 만 검증합니다. `--unattended` 방식은 그 앞에 2개 더:

8. **자동 로그인**: 다른 곳이 세션을 가져간 뒤 이 Windows 에서 KakaoTalk 재실행 →
   `_login_if_needed` 가 로그인 창을 잡고 비밀번호 칸(`Edit[1]`)에 **비밀번호만** 입력하고 Enter 로 세션을 다시 잡나?
   (ID 는 입력하지 않으며, `Edit` 가 2개 미만이면 `{TAB}` 으로 대신 이동합니다.)
   - 확정: `KW_LOGIN_WINDOW_RE`(로그인 창 타이틀)·필드 순서·**2단계 인증/기기 인증 프롬프트 유무**.
   - 인증 프롬프트가 뜨면 = 완전 무인 불가 → 결과를 기록(전용 기기·세션 유지 같은 대안은 따로 논의). 미리 단정 ❌.
   - ⚠️ 비밀번호는 `_credentials.py` 에서 읽어 KakaoTalk 에만 입력합니다. 로그와 화면에 출력하지 않는다.
   - ⚠️ PC 카카오톡은 한 계정에 PC 한 대만 로그인할 수 있어서, 다른 곳에서 로그인하면 다른 PC 의 세션이 끊길 수 있습니다.
9. **방 자동오픈**: `_open_room_via_search` 가 키보드 검색→방이름→Enter 로 대상 방을 여나?(좌표 클릭 ❌)
   - 확정: `KW_SEARCH_HOTKEY`(검색 포커스 단축키, 기본 추정 `^f`)·결과 선택키·단일창 패널 구조.
10. 8·9 통과 후 `--unattended --i-have-verified-on-real-windows` 무인 1회 성공 → 동작 ENV 값 본 문서에 기록 + GREEN 승격.

## 현재 상태 (2026-06-25 실측 반영)
- code: **셀렉터 비의존 로직은 구현됨** — 저장 다이얼로그 경로 주입(키 입력 폴백)·파일 폴링·**방 검증(export 헤더 NFC substring, 불일치 시 fail-fast)**. 저장 파일 이름은 KakaoTalk 이 제안한 그대로 두고 `--out` 폴더로만 옮깁니다. 셀렉터·클릭 위치만 ENV 로 스파이크에서 확정.
- 실측: 2026-06-25 에 실제 Windows KakaoTalk 에서 경로를 손으로 측정했고(창 클래스 `EVA_Window`·로그인 창 타이틀·비밀번호 칸 `Edit[1]`), txt 형식도 같은 날 Windows/WSL2 spike 로 확인했습니다(`normalize.py` 의 txt 파서 주석). 스캐폴드 자체를 처음부터 끝까지 실기에서 돌린 기록은 없습니다.
- 분류: `spike-pending`. WSL/Windows 사용자의 1회 실 export 성공 → 위 7번 절차로 GREEN 승격.
- ⚠️ ≡ 버튼·메뉴 클릭 위치(좌표 폴백)는 화면 배율·창 크기에 따라 어긋날 수 있어 스파이크 1번에서 먼저 확인합니다(어긋나면 위 ENV 로 조정).

---

## Send-channel spike (windows_send.py — 2026-07-18 신설)

수집과 별개로 *발송* 채널의 스파이크 체크리스트는 `scripts/providers/windows_send.py` 의
SPIKE_CHECKLIST 에 있다(방 열기 → UTF-16 클립보드 붙여넣기 한글 무결 → Enter=전송 확인 →
read-back). 실기 1회 성공 후 이 문서에 사용 ENV·검증 로그를 붙이고 README 의 send 행을
GREEN 으로 승격한다. 그 전까지 spike-pending (기본 비-0 종료).
