# kakao-wiki — Windows provider (⚠️ SPIKE-PENDING / EXPERIMENTAL)

`scripts/providers/windows_pywinauto.py` — KakaoTalk Windows 의 `Ctrl+S` 로컬 txt 저장을
pywinauto(UIA)로 코드화한 **스캐폴드**. **실 검증 전이라 성공을 가장하지 않는다**(기본 비-0 exit).

## 왜 Ctrl+S 경로인가 (현실성 등급 🟢 — 연구 §2.2)
Windows 카톡은 대화창에서 **`Ctrl+S` → 내 컴퓨터에 txt 저장**을 지원한다(메뉴 다단 클릭보다 단순).
키 입력 1발 + 저장 다이얼로그 Enter + 파일 폴링이면 끝 → Mac 의 다단 메뉴 흐름보다 오히려 쉽다.
(대안: 메뉴 "모든 메시지 내부저장소 저장"=🟡, "텍스트만 보내기"=이메일=🟠, DB 직접=⚪.)

## 🚨 왜 spike-pending인가 (source-fact §4)
- KakaoTalk **Windows UI 요소(창 타이틀·컨트롤 식별자)는 Mac 과 다르다** → Mac 셀렉터 전부 무효.
- 저장 다이얼로그 구조·파일명 패턴(`KakaoTalk_<방>_<ts>.txt`?)은 실기에서 확인 필요.
- 한국 앱은 custom-draw UI 가 흔해 UIA 노출이 약한 컨트롤이 있을 수 있음 → 키 입력/이미지 폴백 대비.
- **실기 1회 검증 없이 "완성" 보고 ❌.** 스크립트가 기본적으로 비-0(exit 4) 반환 + 안내 출력.

## Spike 체크리스트 (이 전부 통과 후에만 GREEN 승격)
1. KakaoTalk Windows 설치·로그인.
2. 대상 방을 **더블클릭으로 대화창 오픈**(검색-리스트 상태 ❌ — macOS와 동형 함정).
3. 대화창 포커스 → `Ctrl+S` → 로컬 txt 저장 다이얼로그 확인.
4. 저장 경로/파일명 패턴 확정 → `normalize.py` txt 파서(`TXT_LINE_RE`)와 정합 확인(필요 시 파서 보강).
5. `pywinauto` backend='uia' 로 대화창 윈도우 타이틀/컨트롤 재유도(`_export_via_ctrl_s` 의 추정 셀렉터 교체).
6. UIA 약노출 컨트롤은 `send_keys('^s')` + 다이얼로그 `{ENTER}` 폴백.
7. 1회 실 export 성공 후: `windows_pywinauto.py` 의 HONESTY GUARD 해제 +
   `collect.py` `run_windows` 의 SPIKE-PENDING 가드 해제 + `architecture.md`·`SKILL.md` 상태표를
   GREEN 으로 갱신 + 본 문서에 검증 로그 기록.

## 도구 선택지 (셋 다 UIA 접근 가능 — 연구 §2.1)
- **pywinauto**(UIA) — Python·객체수준, 우리 macOS AX 모델과 1:1, 1순위(본 scaffold).
- **AutoHotkey** — UIA 컨트롤 클릭 빠름·단독 exe, 키 입력 위주 폴백.
- **PowerShell UIAutomation** — .NET 내장, 추가 런타임 0.

## 셀렉터 = ENV 주입 (코드 수정 불요)
스파이크 담당자는 코드를 고치지 않고 환경변수로 셀렉터/키만 맞춘다:

| ENV | 의미 | 기본값 |
|---|---|---|
| `KW_KAKAO_TITLE_RE` | KakaoTalk 메인/앱 창 타이틀 정규식 | `.*KakaoTalk.*` (한글 빌드면 `.*카카오톡.*`) |
| `KW_ROOM_TITLE_RE` | 대화방 창 타이틀 정규식 | `.*<방이름>.*` |
| `KW_SAVE_HOTKEY` | 저장 단축키 | `^s` |
| `KW_DIALOG_WAIT_SEC` / `KW_FILE_WAIT_SEC` | 다이얼로그/파일 대기(초) | 8 / 30 |

실행: `python scripts\providers\windows_pywinauto.py --room "<방>" --out .\out --i-have-verified-on-real-windows`
(미검증 시 플래그 없이 돌리면 체크리스트 출력 + exit 4 = 성공 가장 없음.)

## 현재 상태 (2026-06-19 하드닝)
- code: **셀렉터 비의존 로직 전부 구현 완료** — 저장 다이얼로그 경로 주입(키입력 폴백)·파일 폴링·**방 검증(export 헤더 NFC substring, 불일치 시 fail-fast)**·`.raw.txt` 산출(normalize.py txt 파서 정합). 셀렉터/단축키만 ENV 로 스파이크서 확정.
- verification: **0 (Windows 실기 미실행)** — Mac 에서 셀렉터 유도 불가가 유일 잔여.
- 분류: `spike-pending`. 루돌프(WSL/Windows) 또는 재경님 Windows 1회 실 export 성공 → 위 7번 절차로 GREEN 승격.
- ⚠️ Ctrl+S 자체가 KakaoTalk Windows 에서 저장 다이얼로그를 띄우는지부터 스파이크 1번에서 확인(안 되면 메뉴 경로 `KW_SAVE_HOTKEY` 또는 메뉴 클릭으로 전환 — 담당자 보고).
