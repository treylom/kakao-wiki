# kakao-wiki — send channels (kmsg / Discord / Slack)

`scripts/send.py` 는 `send(channel, message)` **인터페이스만** 통일한다. 실제 전송 수단은 채널별로
완전히 다르다(연구 §3.3 정정 — "kmsg가 카톡/디스코드/슬랙 다 보낸다"는 오해).

| 채널 | 전송 수단 | 메커니즘 | 대상 인자 | 인증 |
|---|---|---|---|---|
| **kakao** | macOS: `kmsg send <room> <msg>` / Windows: `providers/windows_send.py`(⚠️ spike-pending) | macOS AX / Windows pywinauto — **KakaoTalk 전용** | 방 *이름*(chat_id ❌) | macOS AX 권한 / Windows: `KW_WINDOWS_SEND_VERIFIED=1`(실기 검증 후) |
| **discord** | Bot REST `POST /channels/{id}/messages` | Discord Bot API | channel_id | `DISCORD_BOT_TOKEN` + **User-Agent 헤더 필수**(Cloudflare 1010 회피) |
| **slack** | Incoming Webhook 또는 Slack MCP | Slack Web API | `#channel` | `SLACK_WEBHOOK_URL` 또는 MCP OAuth |

## kakao (kmsg — macOS / windows_send — Windows, spike-pending)
- **Windows**: `scripts/providers/windows_send.py` (pywinauto — 방 검색 열기 → 클립보드 UTF-16 붙여넣기 → Enter).
  ⚠️ 실기 검증 전 spike-pending: 기본 비-0 종료, `--i-have-verified-on-real-windows` 로만 실행(수집 provider와 동일 정직 원칙).
  send.py 의 kakao 채널이 `sys.platform == "win32"` 이면 자동으로 이 경로로 분기하며, 실기 검증을 마친 운영자가 `KW_WINDOWS_SEND_VERIFIED=1` 을 설정한 경우에만 스파이크 플래그가 전달된다(미설정 = 안내 + 비-0 종료).

## kakao (kmsg)
- 방 *이름* 만 — `chat_id`(chat_xxx) 넣으면 SEARCH_MISS(aktofu #78). send.py 가 `chat_` prefix 거부.
- ⚠️ **"✓ sent" 단독 신뢰 ❌**(source-fact §2) — 호출측에서 read-back(방 창 캡처/`kmsg read --json` 최신 author "(me)") 권장. 이미지 발신은 텍스트 read 로 안 보이니 screencapture.
- ⚠️ 극단 종횡비 이미지 silent-drop — 표지류는 4:5 레터박스 변환 후 전송(aktofu prep-kakao-cover 패턴).
- precondition: loggedIn + 채팅 탭(Cmd+2) + 방 대화창 오픈(검색-리스트 ❌).

## discord (Bot REST)
- `DISCORD_BOT_TOKEN`(`Bot ` prefix 자동 제거) + `User-Agent: DiscordBot (...)` 필수.
- thread 발행 등 = `POST /channels/{parent}/threads` 도 동일 User-Agent 필요.
- 이미지 첨부 = multipart `payload_json` + `files[n]`(최대 10/메시지).

## slack (MCP 권장)
- 스크립트 단독 전송은 `SLACK_WEBHOOK_URL` 설정 시만. 미설정이면 send.py 가 안내 후 종료(exit 3).
- **에이전트 세션에서는 Slack MCP `slack_send_message` 사용 권장**(OAuth, 채널 검색 등 풍부) —
  MCP 는 스크립트가 직접 호출 불가하므로 에이전트가 매개.

## "통합 발신" 일반화 메모
한 `send(channel, msg)` 로 묶었지만 전송 계층은 3종 별개. 향후 이미지/첨부 통합·read-back 통합
검증까지 일반화하려면 채널별 어댑터를 더 키워야 함(현재는 텍스트 발신 + Discord 첨부까지).
