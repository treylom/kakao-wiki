#!/usr/bin/env python3
"""send.py — kakao-wiki 통합 발신 인터페이스 send(channel, message).

⚠️ 인터페이스만 통일 — 실제 전송 수단은 채널별로 다르다(연구 §3.3 정정):
  kakao   = kmsg send (macOS Accessibility, KakaoTalk 전용). 방 *이름* 만(chat_id ❌).
  discord = Bot REST POST (User-Agent 필수). 토큰 = DISCORD_BOT_TOKEN 환경변수 또는 --token.
  slack   = Slack Incoming Webhook(SLACK_WEBHOOK_URL) — 또는 에이전트 세션에서 Slack MCP
            (slack_send_message) 사용 권장(스크립트 단독 호출 불가, references/send-channels.md).

Usage:
  send.py --channel kakao   --room "<ROOM>"        (--message "..."|--message-file f)
  send.py --channel discord --target <channel_id>  (--message "..."|--message-file f)
  send.py --channel slack   --target "<#channel>"  (--message "..."|--message-file f)
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request, urllib.error
from pathlib import Path


def get_message(a) -> str:
    if a.message_file:
        return Path(a.message_file).read_text(encoding="utf-8")
    if a.message:
        return a.message
    return sys.stdin.read()


def send_kakao(room: str, msg: str) -> int:
    room = (room or "").strip()
    if not room or room.startswith("chat_"):
        print("ERROR: kakao 발신은 비어있지 않은 방 *이름* 만(chat_id ❌)", file=sys.stderr)
        return 1
    if sys.platform == "win32":
        # Windows = providers/windows_send.py (pywinauto, ⚠️ spike-pending — 실기 검증 전
        # 기본 비-0 종료로 성공을 가장하지 않음. 검증 절차는 그 파일 SPIKE_CHECKLIST).
        # 메시지는 stdin 으로 전달 — 자식 argv 에 본문 노출 금지(손석희 리뷰 major-3).
        cmd = [sys.executable, str(Path(__file__).parent / "providers" / "windows_send.py"),
               "--room", room]
        # 스파이크 게이트 통제: 실기 검증을 마친 운영자만 KW_WINDOWS_SEND_VERIFIED=1 로 통과
        # (미설정 = windows_send.py 가 체크리스트 안내 후 비-0 종료 — 성공 가장 없음).
        if os.environ.get("KW_WINDOWS_SEND_VERIFIED") == "1":
            cmd.append("--i-have-verified-on-real-windows")
        r = subprocess.run(cmd, input=msg, capture_output=True, text=True)
        sys.stderr.write(r.stdout + r.stderr)
        # exit 6 = DISPATCHED_UNVERIFIED — keystroke 는 나갔으나 delivery 미검증(성공 아님).
        return r.returncode
    # macOS: kmsg = KakaoTalk 전용 AX. 방 이름으로 검색→입력→전송.
    r = subprocess.run(["kmsg", "send", room, msg], capture_output=True, text=True)
    sys.stderr.write(r.stdout + r.stderr)
    # 도구 "✓" 단독 신뢰 ❌(source-fact §2) — 호출측에서 read-back 권장(references).
    return r.returncode


def send_discord(target: str, msg: str, token: str | None) -> int:
    token = token or os.environ.get("DISCORD_BOT_TOKEN", "")
    token = token.replace("Bot ", "").strip().strip('"').strip("'")
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN 미설정", file=sys.stderr)
        return 1
    url = f"https://discord.com/api/v10/channels/{target}/messages"
    req = urllib.request.Request(url, data=json.dumps({"content": msg}).encode(), method="POST")
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "DiscordBot (https://github.com/treylom/kakao-wiki, 1.0)")  # 필수(Cloudflare 1010 회피)
    try:
        with urllib.request.urlopen(req) as resp:
            print(json.load(resp)["id"])
            return 0
    except urllib.error.HTTPError as e:
        print(f"discord FAIL {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return 2


def send_slack(target: str, msg: str) -> int:
    hook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not hook:
        print("Slack: SLACK_WEBHOOK_URL 미설정. 에이전트 세션이면 Slack MCP(slack_send_message)로 "
              f"채널 {target} 에 발신하세요(references/send-channels.md). 스크립트 단독 전송 불가.",
              file=sys.stderr)
        return 3
    payload = {"text": msg}
    if target:
        payload["channel"] = target
    req = urllib.request.Request(hook, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            print("slack ok", resp.status)
            return 0
    except urllib.error.HTTPError as e:
        print(f"slack FAIL {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, choices=["kakao", "discord", "slack"])
    ap.add_argument("--room", default="")         # kakao
    ap.add_argument("--target", default="")        # discord channel_id / slack channel
    ap.add_argument("--message", default="")
    ap.add_argument("--message-file", default="")
    ap.add_argument("--token", default="")
    a = ap.parse_args()
    msg = get_message(a)
    if not msg.strip():
        print("ERROR: empty message", file=sys.stderr)
        return 1
    if a.channel == "kakao":
        return send_kakao(a.room, msg)
    if a.channel == "discord":
        return send_discord(a.target, msg, a.token)
    return send_slack(a.target, msg)


if __name__ == "__main__":
    sys.exit(main())
