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

## 현재 상태
- code: scaffold 작성 완료(`_export_via_ctrl_s` 추정 셀렉터 + 체크리스트 자가출력).
- verification: **0 (미실행)** — Windows 실기 없음.
- 분류: `spike-pending`. collect.py 가 windows provider 호출 시 성공 가장 없이 안내 후 중단.
