#!/usr/bin/env python3
"""summarize.py — pick a summary STYLE for a collected chat, emit a ready-to-use prompt.

The actual summarization is done by an LLM; this script only chooses the *style prompt*.
Two modes (auto-detected):
  - If the `/prompt` skill is available in this environment, we point you to it (it can
    craft a richer, model-specific prompt).
  - Otherwise we fall back to the bundled presets in prompts/summary-styles.md.

Usage:
  summarize.py --list
  summarize.py --style brief --normalized out/<ROOM>-<DATE>.normalized.json [--room "<ROOM>"]

Stdlib only. The emitted prompt is printed to stdout — feed it to your summary LLM.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from collections import Counter
from pathlib import Path

STYLES_MD = Path(__file__).resolve().parent.parent / "prompts" / "summary-styles.md"
_HEADER = re.compile(r"^##\s+(\S+)\s*$")


def load_styles() -> dict[str, str]:
    """Parse prompts/summary-styles.md → {style_id: prompt_body}. Body = first ``` block after the header."""
    styles: dict[str, str] = {}
    if not STYLES_MD.exists():
        return styles
    lines = STYLES_MD.read_text(encoding="utf-8").splitlines()
    i, cur = 0, None
    while i < len(lines):
        m = _HEADER.match(lines[i])
        if m:
            cur = m.group(1)
            i += 1
            # skip to opening fence
            while i < len(lines) and not lines[i].startswith("```"):
                i += 1
            if i < len(lines):  # found opening fence
                i += 1
                buf = []
                while i < len(lines) and not lines[i].startswith("```"):
                    buf.append(lines[i]); i += 1
                styles[cur] = "\n".join(buf).strip()
        i += 1
    return styles


def build_context(normalized: Path | None, room: str | None) -> str:
    if not normalized:
        return room or "수집된 카카오톡 대화"
    try:
        d = json.loads(normalized.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return room or "수집된 카카오톡 대화"
    msgs = d.get("messages", [])
    count = d.get("count", len(msgs))
    first, last = d.get("first_time", "?"), d.get("last_time", "?")
    top = Counter(m.get("user", "?") for m in msgs).most_common(3)
    top_s = ", ".join(f"{u}({n})" for u, n in top) if top else "?"
    rm = room or d.get("room") or "(방 미상)"
    return f"방 {rm}, {first}~{last}, {count}건, 주요 발화자 {top_s}"


def prompt_skill_available() -> bool:
    """Best-effort env detection of the /prompt skill (no hard dependency)."""
    if os.environ.get("KW_PROMPT_SKILL"):
        return True
    home = Path.home()
    for p in (home / ".claude" / "skills" / "prompt",
              home / ".claude" / "skills" / "prompt.md",
              home / ".codex" / "skills" / "prompt"):
        if p.exists():
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list available summary styles")
    ap.add_argument("--style", help="style id (see --list)")
    ap.add_argument("--normalized", help="normalized.json from collect/normalize")
    ap.add_argument("--room", help="room name (for context line)")
    a = ap.parse_args()

    styles = load_styles()
    if not styles:
        print("ERROR: no styles found (prompts/summary-styles.md missing or empty)", file=sys.stderr)
        return 2

    if a.list or not a.style:
        print("사용 가능한 요약 스타일:")
        for k in styles:
            first_line = styles[k].splitlines()[0] if styles[k] else ""
            print(f"  - {k:9s} {first_line[:60]}")
        if prompt_skill_available():
            print("\n💡 이 환경에 /prompt 스킬이 있습니다 — 더 정교한 요약 프롬프트는 /prompt 로 만들 수 있습니다.")
        if not a.style:
            return 0

    if a.style not in styles:
        print(f"ERROR: unknown style '{a.style}'. 사용 가능: {', '.join(styles)}", file=sys.stderr)
        return 2

    ctx = build_context(Path(a.normalized) if a.normalized else None, a.room)
    out = styles[a.style].replace("{context}", ctx)
    if prompt_skill_available():
        print("# (참고: /prompt 스킬 사용 가능 — 아래는 프리셋 폴백 프롬프트)\n", file=sys.stderr)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
