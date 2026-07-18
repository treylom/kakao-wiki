#!/usr/bin/env python3
"""windows_send.py — kakao-wiki Windows *send* channel (⚠️ SPIKE-PENDING until verified).

Goal: send a text message (e.g. digest summary + link) to a KakaoTalk room on Windows —
the Windows counterpart of the macOS `kmsg send` path used by scripts/send.py.

Path (expected to be far simpler than collection — still ⚠️ unverified):
  open room via search → focus message input → paste from clipboard → Enter.

Design so a Windows spike is *minimal* (same philosophy as windows_pywinauto.py):
  - Everything that does NOT depend on UI selectors is fully implemented here:
    clipboard round-trip (UTF-16 via built-in `clip`), room-name guard, message file/stdin
    input. (read-back 은 아직 없음 — 수동 확인, 후속 과제.)
  - The ONLY spike-dependent bits are selectors/hotkeys, exposed as ENV VARS:
        KW_KAKAO_TITLE_RE   window title regex for the KakaoTalk main window
                            (default ".*(KakaoTalk|카카오톡).*")
        KW_SEARCH_HOTKEY    room-search hotkey (default "^f" — shared with collector)
        KW_PASTE_HOTKEY     paste hotkey (default "^v")
        KW_SEND_KEY         send key (default "{ENTER}")
        KW_INPUT_WAIT_SEC   seconds to wait after opening the room before pasting (default 2)

🚨 HONESTY GUARD (source-fact §4):
  Not yet verified on real KakaoTalk Windows. Selectors/hotkeys above are *assumptions*.
  Default run = guidance + non-zero exit (never fakes success). Run with
  `--i-have-verified-on-real-windows` AFTER confirming the flow works on a real machine.
  Checklist below + references/windows-provider-spike.md (send section).

Exit codes: 0 = RESERVED (read-back-verified delivery — not implemented yet)
            1 = bad args · 2 = honesty guard / non-Windows · 3 = missing pywinauto
            5 = UI-layer failure (room/input assert 실패 포함 — 전송 안 됨)
            6 = DISPATCHED_UNVERIFIED (keystrokes sent, delivery unverified)

⚠️ Single-session constraint: KakaoTalk allows one desktop session per account —
  same caveat as the collector (see README "무인 수집" note).
"""
from __future__ import annotations
import argparse, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # = providers/

SPIKE_CHECKLIST = """\
[Windows SEND spike — do all before reporting 'works']
 1. KakaoTalk Windows installed + logged in (chat list visible).
 2. Press the search hotkey (default Ctrl+F), type a room name, Enter →
    confirm the ROOM CHAT WINDOW opens with the message input focused.
    If focus lands elsewhere, note what extra key (e.g. {TAB}/click) is needed.
 3. Put Korean text on the clipboard (this script does it via `clip`, UTF-16),
    press Ctrl+V in the input → confirm Korean is pasted intact (no mojibake).
 4. Press Enter → confirm the message is SENT to the room (not a newline).
    If Enter inserts a newline, find the send key and export KW_SEND_KEY.
 5. Read-back: confirm the sent text appears in the room (screenshot or manual check).
    (Automated read-back is NOT implemented yet — manual verification only, follow-up work.)
 6. After ONE real send succeeds: rerun with --i-have-verified-on-real-windows,
    paste the env vars used + verification log into references/windows-provider-spike.md
    (send section), then flip the send row to GREEN in README / architecture.md.
"""


def _clip_set(text: str) -> None:
    """Put text on the Windows clipboard via built-in `clip` (UTF-16 w/ BOM → Korean-safe).
    stdlib-only — no pyperclip dependency (repo principle: core needs no deps)."""
    subprocess.run("clip", input=text.encode("utf-16"), check=True)


def _open_room(room: str):
    """Open the target room via search — with literal-safe input and hard asserts.

    Review fixes (손석희 2026-07-18):
    - The room name goes through the CLIPBOARD (paste), never send_keys — pywinauto
      interprets ^ + % { } as key sequences, so typing a room name literally is unsafe.
    - After Enter we ASSERT the room chat window exists (KW_ROOM_TITLE_RE, default
      re.escape(room)) and that a message-input (UIA Edit) is present & focused.
      No paste/Enter ever happens before both asserts pass (wrong-room send guard)."""
    import re as _re
    from pywinauto import Application  # type: ignore
    from pywinauto.keyboard import send_keys  # type: ignore
    title_re = os.environ.get("KW_KAKAO_TITLE_RE", ".*(KakaoTalk|카카오톡).*")
    app = Application(backend="uia").connect(title_re=title_re, timeout=10)
    main = app.top_window()
    main.set_focus()
    send_keys(os.environ.get("KW_SEARCH_HOTKEY", "^f"))
    time.sleep(0.7)
    _clip_set(room)                                   # literal-safe search input
    send_keys(os.environ.get("KW_PASTE_HOTKEY", "^v"))
    time.sleep(0.7)
    send_keys("{ENTER}")
    time.sleep(float(os.environ.get("KW_INPUT_WAIT_SEC", "2")))
    # 앵커 필수(손석희 재검토): pywinauto title_re 는 regex.match(=prefix 매칭)라
    # escape 만으로는 "room-other" 도 통과한다 → \A..\Z 로 정확 일치 강제.
    # 제목에 접미사가 붙는 UI 는 KW_ROOM_TITLE_RE 로 명시 override.
    room_re = os.environ.get("KW_ROOM_TITLE_RE") or rf"\A{_re.escape(room)}\Z"
    win = app.window(title_re=room_re)
    win.wait("exists ready", timeout=float(os.environ.get("KW_DIALOG_WAIT_SEC", "8")))
    win.set_focus()
    edits = win.descendants(control_type="Edit")
    if not edits:
        raise RuntimeError(
            "message-input (UIA Edit) not found in the room window — spike item: "
            "adjust KW_ROOM_TITLE_RE or note the extra focus step needed")
    edits[-1].set_focus()
    return win


EXIT_DISPATCHED_UNVERIFIED = 6  # keystrokes sent, delivery NOT verified (no read-back yet)


def send_message(room: str, msg: str) -> int:
    from pywinauto.keyboard import send_keys  # type: ignore
    _open_room(room)                                   # hard-asserts room + input focus
    _clip_set(msg)
    send_keys(os.environ.get("KW_PASTE_HOTKEY", "^v"))
    time.sleep(0.5)
    send_keys(os.environ.get("KW_SEND_KEY", "{ENTER}"))
    # Dispatch ≠ delivery (source-fact §2, 손석희 리뷰): until an automated read-back
    # exists, return a distinct non-zero code so no caller can mistake this for
    # verified success. Exit 0 is RESERVED for a future read-back-verified path.
    sys.stderr.write("[send] DISPATCHED_UNVERIFIED (exit 6) — keystrokes sent to the "
                     "asserted room window; verify delivery in the room manually.\n")
    return EXIT_DISPATCHED_UNVERIFIED


def main() -> int:
    ap = argparse.ArgumentParser(description="kakao-wiki Windows send channel (spike-pending)")
    ap.add_argument("--room", required=True, help="room *name* (chat_id not supported)")
    ap.add_argument("--message", help="message text")
    ap.add_argument("--message-file", help="file containing the message")
    ap.add_argument("--i-have-verified-on-real-windows", action="store_true",
                    help="run for real AFTER completing the spike checklist")
    a = ap.parse_args()

    room = a.room.strip()
    if not room or room.startswith("chat_"):
        print("ERROR: send needs a non-empty room *name*, not a chat_id", file=sys.stderr)
        return 1
    if a.message_file:
        msg = Path(a.message_file).read_text(encoding="utf-8")
    elif a.message:
        msg = a.message
    else:
        msg = sys.stdin.read()
    if not msg.strip():
        print("ERROR: empty message", file=sys.stderr)
        return 1

    if sys.platform != "win32":
        print("ERROR: this channel only runs on Windows (use kmsg/macOS path otherwise)",
              file=sys.stderr)
        return 2
    if not a.i_have_verified_on_real_windows:
        sys.stderr.write(SPIKE_CHECKLIST)
        sys.stderr.write("\n[honesty guard] not verified on a real machine yet — refusing to "
                         "claim success. Re-run with --i-have-verified-on-real-windows after "
                         "the checklist passes.\n")
        return 2
    try:
        return send_message(room, msg)
    except ImportError:
        print("ERROR: pip install pywinauto", file=sys.stderr)
        return 3
    except Exception as e:  # selector/timing failures — real spike feedback
        print(f"ERROR: send failed at UI layer: {e}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
