# kakao-wiki — macOS provider (GREEN)

`scripts/providers/macos_osascript.sh` — KakaoTalk GUI 를 osascript(AX)로 구동해 텍스트 export → CSV.

## 왜 osascript인가
KakaoTalk은 공개 API가 없다. 대화 내보내기는 GUI 메뉴에만 있어, 사람이 클릭하는 절차를
macOS Accessibility(`System Events`)로 흉내낸다. → **macOS 전용** 의존.

## osascript 의존 지점 (단계)
1. `activate` — 앱 포커스
2. `key code 53`(Esc) 반복 — 잔여 창 정리(`close_extra_windows`)
3. `click button 2 of window "카카오톡"` — 채팅 탭
4. `kmsg read <room> --keep-window` — 방 열기
5. **GUI 방 hard-assert** — `every window` 순회로 방 창 존재 확인(방교차 차단)
6. `perform action "AXRaise"` + `click menu item "채팅방 설정" of menu bar item "채팅"` — 설정 진입
7. `click button 2 of window "Window"` — 대화 내용 관리 탭
8. `click button "텍스트 파일로 저장" of scroll area 1` — export 트리거
9. `key code 36`(Enter) — 저장 다이얼로그
10. `click button "확인" of sheet 1` — 대용량 완료 sheet 닫기
11. **CSV 방 hard-assert** — `csv_room_matches` 가 추출된 CSV *파일 이름*(내용 아님)에 방 이름이 들어 있는지 NFC 정규화 후 부분 문자열로 비교

## 견고성 장치
- Kakao 전역 mutex `/tmp/kakao-gui.lock` — 같은 락을 잡는 프로세스끼리 GUI 점유를 직렬화합니다. 단 90초 기다려도 못 잡으면 락을 넘겨받고 진행하며(`macos_osascript.sh` 의 steal 단계), 내보내기는 최대 600초 폴링하므로 두 실행이 겹칠 수 있습니다. 이때는 아래 방 assert 가 마지막 방어선입니다.
- GUI 방 assert(창 부재 시 fail-fast exit 2) + CSV 방 assert(불일치 시 exit 3) = 방교차 이중 차단. 종료 코드 1 = 그 밖의 실패(예: CSV 대기 600초 초과).
- 비교 방식이 서로 다릅니다. CSV 검사는 파일 이름을 NFC 로 맞춘 뒤 부분 문자열로 비교하고, GUI 검사는 창 이름이 방 이름과 정확히 같은지만 봅니다(정규화 없음).

## ⚠️ fragility 주의
요소가 창 이름("Window")·버튼 인덱스(2)·메뉴 텍스트("채팅방 설정")에 의존 → KakaoTalk macOS UI
업데이트 시 셀렉터 재유도 필요. CSV/GUI assert 가 깨짐을 fail-fast 로 잡음(silent 오수집 방지).

## 검증 로그 (scenario-replay GREEN)
| 일시(KST) | 명령 | 결과 |
|---|---|---|
| 2026-06-18 21:10 | `collect.py --room "<예시방>" --provider macos --out /tmp/kw-verify` | ✅ GUI export 성공 → `<예시방>-2026-06-18.raw.csv` **59,822줄**(~380명 실제 방), CSV 방 assert(파일 이름에 방 이름 포함) 통과 → normalize 로 약 5만 건 메시지 |
| 2026-06-18 | `normalize.py`(같은 CSV) | ✅ {time,user,msg} 정상 파싱·봇/공지 1,284건 필터 |
| 2026-06-18 | `collect.py --provider windows` 가드 | ✅ 성공으로 보고하지 않고 비-0 exit(spike-pending) |
| 2026-06-18 | `store_to_wiki.py` | ✅ vault md(frontmatter type/tags/aliases/okf_type/stats) 생성 |

→ macOS provider end-to-end **GREEN**(실 KakaoTalk export 1회 + normalize + store 검증).

> 메시지 수 표기: 처음 기록에는 collect 행과 normalize 행에 각각 50,168 과 50,160 이 적혀 있었습니다. 원본 CSV 가 레포에 없어 어느 쪽이 맞는지 다시 확인할 수 없고 차이의 원인도 기록되어 있지 않아, 여기서는 "약 5만 건"으로만 적습니다.

## 전제
- macOS Accessibility 권한(System Settings → Privacy & Security → Accessibility)에 KakaoTalk·kmsg·터미널 등록.
- `kmsg` 명령줄 도구가 PATH 에 있어야 합니다(이 레포에 포함되어 있지 않음).
- 카카오톡이 내보낸 CSV 를 `~/Downloads/KakaoTalk_Chat_*.csv` 에 저장해야 합니다. 스크립트가 그 경로만 보므로, 다른 곳에 저장되면 600초 기다린 뒤 종료 코드 1 로 끝납니다.
