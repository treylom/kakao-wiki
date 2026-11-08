#!/usr/bin/env python3
"""
length_gate.py — pre-send message-length gate for kakao-wiki.

Why this exists
---------------
Chat apps — KakaoTalk especially — can SILENTLY truncate a message that is too
long. The recipient sees text cut off mid-sentence, and *the sender is never
told*. This gate refuses to let an over-length message go out unnoticed.

It is deliberately small and domain-neutral: give it the text (a file, or stdin)
and a character limit; it exits non-zero if the text would be truncated.

Design philosophy (carried over from a production pipeline that learned these
the expensive way — kept general on purpose):

  1. The goal is not to BLOCK, it is to prevent SILENCE. Every check can be
     waived with --waiver "<reason>", but the waiver PRINTS its reason to stdout
     so it lands in logs/reports. A silent bypass is the exact thing we guard
     against.
  2. State what the gate does NOT check. A gate that hides its blind spots
     breeds overconfidence, so this one says — on every run — that it measures
     length ONLY (not accuracy, not citation fidelity, not coverage).

Exit codes:
  0  — within limit, or explicitly waived
  2  — would be truncated (over limit)
  64 — usage error (bad/missing arguments, unreadable file, empty waiver reason)
"""
from __future__ import annotations

import argparse
import sys

# Default character budget. This is a MEASURED value from one environment
# (KakaoTalk's silent-truncation point was observed near ~3,976 characters, so a
# margin is left below it). It is NOT a universal constant — measure your own
# channel and pass --max-chars accordingly.
DEFAULT_MAX_CHARS = 3900

BLIND_SPOTS = (
    "length only — does NOT check: factual accuracy · quote/citation fidelity · "
    "topic coverage · whether the content is appropriate to publish"
)


class UsageArgumentParser(argparse.ArgumentParser):
    """ArgumentParser whose usage errors exit 64 (argparse's default is 2).

    Exit 2 is reserved for a real gate FAIL (over the limit), so a caller can tell
    "bad flags" from "message too long".
    """

    def error(self, message: str):  # type: ignore[override]
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(64)


def _read_text(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str] | None = None) -> int:
    ap = UsageArgumentParser(
        description="Refuse to send a message that a chat app would silently truncate.",
    )
    ap.add_argument(
        "--file",
        "-f",
        default="-",
        help="Message file to check (default: stdin).",
    )
    ap.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"Character budget (default: {DEFAULT_MAX_CHARS}, a measured value — tune for your channel).",
    )
    ap.add_argument(
        "--waiver",
        default=None,
        metavar="REASON",
        help="Bypass the length check. REASON is required and is printed to stdout so it is never silent.",
    )
    args = ap.parse_args(argv)

    if args.max_chars <= 0:
        print("length-gate: usage error — --max-chars must be a positive integer", file=sys.stderr)
        return 64

    try:
        text = _read_text(args.file)
    except OSError as exc:
        print(f"length-gate: usage error — cannot read message: {exc}", file=sys.stderr)
        return 64

    # Count Unicode codepoints of the message body, ignoring a single trailing
    # newline (an editor artifact, not part of what gets sent).
    body = text[:-1] if text.endswith("\n") else text
    n = len(body)
    limit = args.max_chars

    # Blind-spot declaration prints on EVERY run (philosophy #2).
    print(f"length-gate: measured {n} chars against limit {limit} — {BLIND_SPOTS}")

    if args.waiver is not None:
        reason = args.waiver.strip()
        if not reason:
            print("length-gate: usage error — --waiver requires a non-empty REASON", file=sys.stderr)
            return 64
        # Waiver is allowed but never silent (philosophy #1).
        print(f"length-gate: WAIVED (reason: {reason}) — {n} chars, limit {limit}")
        return 0

    if n > limit:
        over = n - limit
        print(
            f"length-gate: FAIL — {n} chars exceeds limit {limit} by {over}. "
            f"This message would be truncated silently. Shorten it, raise --max-chars "
            f"if your channel allows, or pass --waiver \"<reason>\" to send anyway.",
            file=sys.stderr,
        )
        return 2

    print(f"length-gate: OK — {n} chars within limit {limit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
