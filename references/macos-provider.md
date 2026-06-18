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
11. **CSV 방 hard-assert** — `csv_room_matches`(NFC substring)로 추출 CSV 가 target 방인지 검증

## 견고성 장치 (aktofu에서 계승)
- Kakao 전역 mutex `/tmp/kakao-gui.lock` — 동시 GUI 점유 직렬화(aktofu와 공유).
- GUI 방 assert(창 부재 시 fail-fast exit 2) + CSV 방 assert(불일치 시 exit 3) = 방교차 이중 차단.
- 한글 NFD/NFC 무관 substring 비교.

## ⚠️ fragility 주의
요소가 창 이름("Window")·버튼 인덱스(2)·메뉴 텍스트("채팅방 설정")에 의존 → KakaoTalk macOS UI
업데이트 시 셀렉터 재유도 필요. CSV/GUI assert 가 깨짐을 fail-fast 로 잡음(silent 오수집 방지).

## 검증 로그 (scenario-replay GREEN)
| 일시(KST) | 명령 | 결과 |
|---|---|---|
| 2026-06-18 21:10 | `collect.py --room "<예시방>" --provider macos --out /tmp/kw-verify` | ✅ GUI export 성공 → `<예시방>-2026-06-18.raw.csv` **59,822줄**(~380명 실제 방), CSV 방 assert ⊇ 방이름 통과 → normalize **50,168 메시지** |
| 2026-06-18 | `normalize.py`(같은 CSV, deterministic) | ✅ 50,160 메시지 파싱·{time,user,msg} 정상·봇/공지 1,284 필터 |
| 2026-06-18 | `collect.py --provider windows` 가드 | ✅ 성공 가장 없이 비-0 exit(spike-pending) |
| 2026-06-18 | `store_to_wiki.py` | ✅ vault md(frontmatter type/tags/aliases/okf_type/stats) 생성 |

→ macOS provider end-to-end **GREEN**(실 KakaoTalk export 1회 + normalize + store 검증).

## 전제
- macOS Accessibility 권한(System Settings → Privacy & Security → Accessibility)에 KakaoTalk·kmsg·터미널 등록.
- `kmsg`(`/opt/homebrew/bin/kmsg`) 설치.
