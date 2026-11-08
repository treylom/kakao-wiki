# kakao-wiki — send channels (kmsg / Discord / Slack)

`scripts/send.py` 는 `send(channel, message)` **인터페이스만** 통일합니다. 흔히 "kmsg 하나로 카톡·디스코드·슬랙을 다 보낸다"고 오해하지만, 실제 전송 수단은 채널마다 다릅니다.

| 채널 | 전송 수단 | 메커니즘 | 대상 인자 | 인증 |
|---|---|---|---|---|
| **kakao** | macOS: `kmsg send <room> <msg>` / Windows: `providers/windows_send.py`(⚠️ spike-pending) | macOS AX / Windows pywinauto — **KakaoTalk 전용** | 방 *이름*(chat_id ❌) | macOS AX 권한 + `kmsg` 가 PATH 에 있어야 함(레포에 포함되지 않음) / Windows: `KW_WINDOWS_SEND_VERIFIED=1`(실기 검증 후) |
| **discord** | Bot REST `POST /channels/{id}/messages` | Discord Bot API | channel_id | `DISCORD_BOT_TOKEN` + **User-Agent 헤더 필수**(Cloudflare 1010 회피) |
| **slack** | Incoming Webhook(`send.py`) 또는 에이전트의 Slack 도구(MCP, 에이전트가 직접) | 웹훅 URL 로 POST / MCP | `#channel` | `SLACK_WEBHOOK_URL` 또는 MCP OAuth |

`send.py` 종료 코드: `0` 전송 호출 성공 · `1` 토큰·방 이름 누락, 빈 본문 등 · `2` 길이 게이트가 막음(또는 Discord/Slack 서버가 오류 응답) · `3` Slack 웹훅 미설정 · `64` 길이 게이트 사용법 오류(예: 빈 `--waiver` 사유) · `66` 길이 게이트 파일 없음. kakao 는 `kmsg`(또는 Windows 경로)의 종료 코드를 그대로 돌려줍니다. kakao·discord·slack 어느 채널도 전달 확인은 하지 않습니다.

## kakao
### macOS (kmsg)
- 방 *이름* 만 — `chat_id`(chat_xxx) 넣으면 SEARCH_MISS(kmsg 검색은 방 이름 기반). send.py 가 `chat_` prefix 거부.
- ⚠️ **"✓ sent" 단독 신뢰 ❌**(보냈다는 출력만 믿지 않는다는 원칙) — 호출한 쪽에서 read-back(방 창 캡처/`kmsg read --json` 최신 author "(me)") 권장. 이미지 발신은 텍스트 read 로 안 보이니 screencapture.
- ⚠️ 극단 종횡비 이미지는 조용히 누락됨 — 표지류는 4:5 레터박스로 바꿔서 전송.
- precondition: loggedIn + 채팅 탭(Cmd+2) + 방 대화창 오픈(검색-리스트 ❌).

### Windows (windows_send.py, spike-pending)
- `scripts/providers/windows_send.py` (pywinauto — 방 검색 열기 → 클립보드 UTF-16 붙여넣기 → Enter).
- ⚠️ 실기 검증 전 spike-pending: 기본 비-0 종료, `--i-have-verified-on-real-windows` 로만 실행(수집 provider와 같은 원칙).
  send.py 의 kakao 채널이 `sys.platform == "win32"` 이면 자동으로 이 경로로 분기하며, 실기 검증을 마친 운영자가 `KW_WINDOWS_SEND_VERIFIED=1` 을 설정한 경우에만 스파이크 플래그가 전달된다(미설정 = 안내 + 비-0 종료).
- **종료 코드 `6` = DISPATCHED_UNVERIFIED**: 키 입력은 나갔지만 전달은 확인하지 못함. 읽어 되돌려 확인하는 기능이 아직 없어 이 경로는 `0` 을 돌려주지 않습니다(`0` 은 장래 read-back 확인용으로 비워 둠). `send.py` 는 이 코드를 그대로 전달합니다. 그 밖: `1` 인자 오류 · `2` 검증 가드/Windows 아님 · `3` pywinauto 없음 · `5` UI 단계 실패(방·입력창 확인 실패 포함, 전송 안 됨).

## discord (Bot REST)
- `DISCORD_BOT_TOKEN`(`Bot ` prefix 자동 제거) + `User-Agent: DiscordBot (...)` 필수.
- thread 발행 등 = `POST /channels/{parent}/threads` 도 동일 User-Agent 필요.
- 이미지 첨부 = multipart `payload_json` + `files[n]`(최대 10/메시지) 방식이 필요하지만, **`send.py` 에는 구현돼 있지 않습니다**(JSON `{"content": msg}` 텍스트만 보냄).

## slack (웹훅 또는 에이전트의 MCP 도구)
- 스크립트(`send.py`) 단독 전송은 `SLACK_WEBHOOK_URL`(Incoming Webhook) 설정 시만. 미설정이면 send.py 가 안내 후 종료(exit 3).
- 웹훅은 보통 URL 을 만들 때 채널이 정해지므로 `--target` 이 무시될 수 있습니다(Slack 의 일반적인 동작 기준이며 이 레포에서 시험하지는 않았습니다).
- **에이전트 세션에서는 Slack 의 MCP 도구(`slack_send_message`) 사용 권장**(OAuth, 채널 검색 등 풍부) —
  MCP 는 스크립트가 직접 호출할 수 없으므로 에이전트가 대신 보냅니다.

## "통합 발신" 일반화 메모
한 `send(channel, msg)` 로 묶었지만 전송 계층은 3종 별개. 향후 이미지/첨부 통합·read-back 통합
검증까지 일반화하려면 채널별 어댑터를 더 키워야 함. 현재는 **텍스트 발신만** 됩니다(Discord 첨부는 위에 방식만 적어 두었고 구현되어 있지 않음).
