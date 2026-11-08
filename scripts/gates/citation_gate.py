#!/usr/bin/env python3
"""
citation_gate.py — verify that every quote in a digest really appears in the export.

Why this exists
---------------
When you build a *cited* summary of a chat room ("Alice said: ...\""), it is easy
for a language model to paraphrase inside the quotation marks — to put words in
someone's mouth that they never typed. This gate checks the opposite direction of
trust: it assumes **nothing inside quotes is real until it is found, verbatim, in
the raw export**.

It extracts the quoted spans from the digest and searches for each one, as an
exact substring, in the raw export file(s). A quote that is not found verbatim is
reported as UNVERIFIED.

Design philosophy (generalized from a production citation verifier):

  1. "Don't trust a quote until you've seen the source" — verify against the raw
     export, not against your own memory of it.
  2. Check the RIGHT unit (the "measured-object" rule). This gate compares the
     text INSIDE quotation marks — not the surrounding narrative. Paraphrased
     narration is allowed; only quoted spans must be verbatim. Comparing a
     summarized body against the original text is a classic source of false
     "fabricated" verdicts, so this gate never does that.
  3. Cross-file search. Pass every export that could contain the source (e.g. both
     days' exports when a summary window crosses midnight); a quote counts as found if it is verbatim in
     ANY of them.
  4. State the blind spots on every run: this gate checks quote fidelity ONLY.

Short quotes (fewer than --min-len characters, default 4) are skipped, but they
are always listed on stdout so a skipped quote is never silent.

This gate has no waiver option (only length_gate.py and send.py accept --waiver).

Exit codes:
  0  — every extracted quote found verbatim (or no quotes to check)
  2  — one or more quotes NOT found verbatim
  64 — usage error (bad/missing arguments or unreadable files)
"""
from __future__ import annotations

import argparse
import re
import sys

# Minimum quote length to check. Very short spans ("ㅋㅋ", "네") match everything
# and carry no citation risk, so they are skipped (and reported as skipped).
MIN_QUOTE_LEN = 4

# Quote delimiters recognized, as (open, close) pairs. Straight double quotes,
# Korean corner brackets, and typographic curly quotes.
QUOTE_PATTERNS = [
    ('"', '"'),
    ("「", "」"),  # 「 」
    ("“", "”"),  # “ ”
]

BLIND_SPOTS = (
    "quote fidelity only — does NOT check: whether the speaker attribution is "
    "correct, whether the quote is in context, factual accuracy, or coverage"
)


class UsageArgumentParser(argparse.ArgumentParser):
    """ArgumentParser whose usage errors exit 64 (argparse's default is 2).

    Exit 2 is reserved for a real gate FAIL, so a caller can tell "bad flags"
    from "quote not found".
    """

    def error(self, message: str):  # type: ignore[override]
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(64)


def _scan_quotes(text: str) -> list[str]:
    """Return every distinct quoted span (stripped) in first-seen order."""
    seen: dict[str, None] = {}
    for open_q, close_q in QUOTE_PATTERNS:
        o = re.escape(open_q)
        c = re.escape(close_q)
        # Non-greedy, no nested same-delimiter; span must not cross a newline.
        for m in re.finditer(f"{o}([^{c}\n]+?){c}", text):
            span = m.group(1).strip()
            if span and span not in seen:
                seen[span] = None
    return list(seen.keys())


def extract_quotes(text: str, min_len: int = MIN_QUOTE_LEN) -> list[str]:
    """Return the distinct quoted spans in `text` that are at least `min_len` long."""
    return [q for q in _scan_quotes(text) if len(q) >= min_len]


def skipped_quotes(text: str, min_len: int = MIN_QUOTE_LEN) -> list[str]:
    """Return the distinct quoted spans that are shorter than `min_len` (not checked)."""
    return [q for q in _scan_quotes(text) if len(q) < min_len]


def load_sources(paths: list[str]) -> str:
    chunks = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            chunks.append(fh.read())
    # Concatenate with a separator so a quote can't accidentally span two files.
    return "\n \n".join(chunks)


def main(argv: list[str] | None = None) -> int:
    ap = UsageArgumentParser(
        description="Verify every quoted span in a digest appears verbatim in the raw export(s).",
    )
    ap.add_argument("digest", help="Digest/summary file containing quoted spans.")
    ap.add_argument(
        "sources",
        nargs="+",
        help="One or more raw export files (csv/txt). A quote counts as found in ANY of them.",
    )
    ap.add_argument(
        "--min-len",
        type=int,
        default=MIN_QUOTE_LEN,
        help=f"Skip quotes shorter than this many characters (default: {MIN_QUOTE_LEN}).",
    )
    args = ap.parse_args(argv)

    try:
        with open(args.digest, encoding="utf-8") as fh:
            digest_text = fh.read()
        haystack = load_sources(args.sources)
    except OSError as exc:
        print(f"citation-gate: usage error — {exc}", file=sys.stderr)
        return 64

    min_len = max(1, args.min_len)
    quotes = extract_quotes(digest_text, min_len)
    skipped = skipped_quotes(digest_text, min_len)

    print(f"citation-gate: {len(quotes)} quote(s) to verify — {BLIND_SPOTS}")
    if skipped:
        listing = ", ".join(f'"{q}"' for q in skipped)
        print(
            f"citation-gate: skipped {len(skipped)} quote(s) shorter than {min_len} chars "
            f"(not checked): {listing}"
        )

    if not quotes:
        print("citation-gate: OK — no quoted spans found to verify")
        return 0

    misses = []
    for q in quotes:
        # Measured-object rule (philosophy #2): the unit searched is the quote
        # span itself, matched as an exact substring (grep -F semantics).
        if q not in haystack:
            misses.append(q)

    found = len(quotes) - len(misses)
    if misses:
        print(
            f"citation-gate: FAIL — {found}/{len(quotes)} verbatim; "
            f"{len(misses)} NOT found in the export(s):",
            file=sys.stderr,
        )
        for q in misses:
            preview = q if len(q) <= 80 else q[:77] + "..."
            print(f"  UNVERIFIED: \"{preview}\"", file=sys.stderr)
        return 2

    print(f"citation-gate: OK — all {found}/{len(quotes)} quotes found verbatim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
