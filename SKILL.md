---
name: kakao-wiki
description: >-
  Collect a KakaoTalk chat room's conversation history, normalize it into structured
  messages, store it into your local Obsidian/LLM-wiki vault, and (optionally) summarize
  and send a digest out to KakaoTalk / Discord / Slack. A portable, installable skill
  built around the common summarize-and-send workflow, with a provider abstraction and
  built-in pre-send verification gates (message length + quote citation).
  macOS(osascript GUI export) is the GREEN/default path; manual(user-exported txt via
  Ctrl+S — Windows/WSL today-path) is GREEN; Windows(pywinauto auto-export) ships as an
  experimental scaffold; a DB-direct(kakaocli) path is provided as an opt-in experiment.
  Use when the user wants to "collect a KakaoTalk room", "summarize a kakao chat", "turn
  a kakao chat into my wiki", "set up kakao-wiki", "export kakaotalk to obsidian", "use
  kakao-wiki on Windows/WSL", or "automate a kakao chat digest".
---

# kakao-wiki — collect → summarize → verify → send, KakaoTalk to your vault

This skill packages the common **"summarize a chat room and send it out"** workflow as a
**portable, installable** skill, with a provider abstraction for collection and
**built-in verification gates** so a digest can't go out silently truncated or with a
misquoted line.

The pipeline is six stages; the middle ones are optional depending on what you want:

```
1 collect → 2 normalize → 3 summarize → 4 verify → 5 send → 6 record
  (provider)  (parser)     (optional)    (gates)    (optional) (to vault)
```

Only **collect → normalize** is mandatory (you always need messages first). Summarize,
verify, send and record are opt-in — but **if you send a summary, the length gate runs
automatically**, and **if you build a cited summary, run the citation gate first.**

> **Provenance.** Generalized (copied, NOT live-modified) from a production KakaoTalk
> collection-and-digest pipeline: a GUI-export recipe, a message parser, and the
> length/citation gates that pipeline learned it needed the expensive way.
> Design rationale + Windows feasibility grading: `references/architecture.md`.

## ⚠️ Honesty contract (status labels are earned, not assumed)
- **macOS provider = GREEN** — verified by a real KakaoTalk export run (see `references/macos-provider.md` → "Verification log").
- **Windows provider = `spike-pending` / experimental** — code-complete *scaffold* only. The KakaoTalk
  Windows UI selectors/keys are NOT verified on a real machine. Do **not** report it as "working" until a
  Windows spike confirms it (selectors re-derived). The script self-labels its status.
- **DB-direct provider = experimental** — depends on `kakaocli` key-derivation succeeding on the host.

## Capabilities map (what's reused vs new)

| Layer | Source | Status |
|-------|--------|--------|
| macOS GUI export recipe | generalized export recipe (mutex + room assert + CSV room-check) | **GREEN** (copied/generalized) |
| message normalize/parse | generalized message parser | **GREEN** (copied/generalized) |
| **length gate (pre-send)** | `scripts/gates/length_gate.py` | **shipped** — refuses silent truncation |
| **citation gate (verbatim quotes)** | `scripts/gates/citation_gate.py` | **shipped** — verifies quotes against the raw export |
| provider abstraction | `collect(room, provider)` dispatch | this skill |
| manual provider | user-exported txt(Ctrl+S) auto-discovery + room fail-fast | **GREEN** (Windows/WSL today-path) |
| Windows guide | `windows_guide.py` env-detect + install guide | this skill |
| Windows provider | pywinauto Ctrl+S local txt | **spike-pending** |
| DB-direct provider | `kakaocli query` wrapper | experimental |
| vault store | normalized → LLM-wiki md | this skill |
| send abstraction | `send(channel,msg)` kmsg/Discord/Slack, length gate at the gateway | this skill |

## Layout
```
kakao-wiki/
  SKILL.md
  scripts/
    collect.py              # provider dispatch: collect(room, provider) -> normalized.json (manual 포함)
    windows_guide.py        # Windows/WSL 환경 진단 + Ctrl+S 경로 + katok-windows 설치 안내 (읽기 전용)
    normalize.py            # raw export (CSV/txt) -> normalized messages (parser, no GUI)
    store_to_wiki.py        # normalized -> vault markdown note
    summarize.py            # pick a summary STYLE (detect /prompt skill, else presets)
    send.py                 # send(channel, message): kakao | discord | slack (length gate at gateway)
    gates/
      length_gate.py        # pre-send: refuse a message a chat app would silently truncate
      citation_gate.py      # verify every quoted span appears verbatim in the raw export
    providers/
      macos_osascript.sh    # GREEN: KakaoTalk GUI export -> CSV (mutex + room asserts)
      windows_pywinauto.py  # SPIKE-PENDING: Ctrl+S local txt export (selectors via ENV)
      db_kakaocli.sh        # EXPERIMENTAL: kakaocli DB read -> CSV
  prompts/
    summary-styles.md       # preset summary-style prompts + shared discipline (voice/quote/budget)
  references/
    architecture.md         # provider abstraction + data flow + Windows feasibility grades
    macos-provider.md       # osascript dependency points + verification log
    windows-provider-spike.md  # Ctrl+S scaffold + spike checklist (what to verify)
    send-channels.md        # kmsg(kakao)/Discord(REST)/Slack(MCP) notes
```

# Workflow

Run from the skill root. `ROOM` = the exact KakaoTalk room name. `OUT` = a working dir.

### 1. Collect (provider-abstracted)
```bash
# macOS (default on macOS, GREEN):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out

# manual (default on Windows/WSL/Linux, GREEN) — 사용자가 카톡에서 Ctrl+S 로 내보낸 txt 를 이어받음.
#   --input 생략 시 기본 저장 경로(~/.kakao-wiki/exports · 문서 · 다운로드 · WSL 이면 /mnt/c/Users/*)
#   에서 최신 카톡 내보내기 파일을 자동 탐색. 방이름 불일치 파일은 fail-fast.
python3 scripts/collect.py --room "<ROOM>" --provider manual [--input <내보낸.txt>] --out ./out

# Windows auto-export (experimental scaffold — refuses to claim success until spike-verified):
python3 scripts/collect.py --room "<ROOM>" --provider windows --out ./out

# DB-direct (experimental):
python3 scripts/collect.py --room "<ROOM>" --provider db --out ./out
```
Produces `out/<ROOM>-<DATE>.raw.csv` (or .txt) and `out/<ROOM>-<DATE>.normalized.json`.

> **Windows / WSL users (agent instruction):** first run
> `python3 scripts/windows_guide.py --room "<ROOM>"` and show its output — it detects the
> environment, walks the Ctrl+S export, previews auto-discovery, and checks for the
> katok-windows search CLI. Today's path on Windows = official export (Ctrl+S) → the
> `manual` provider above. The `windows` auto-export provider is spike-pending — don't
> promise it "just works".

### 2. Normalize
`collect.py` already emits `normalized.json`. If you *already have* a raw export (someone
sent you a Ctrl+S txt, or you have a CSV), normalize it directly:
```bash
python3 scripts/normalize.py --input <raw.csv|raw.txt> --out out/<ROOM>-<DATE>.normalized.json
```
The parser absorbs CSV and txt into one message schema, so every later stage is
provider-agnostic. (Topic clustering / analysis is intentionally out of scope — this skill
takes you to normalized messages.)

### 3. Summarize (optional)
Let the user pick how the digest reads. `summarize.py` auto-detects the `/prompt` skill
(uses it if present) and otherwise emits a bundled preset prompt; pipe its output to your
summary LLM, write the result to `summary.txt`, then verify and send.
```bash
python3 scripts/summarize.py --list                       # brief | detailed | bullets | formal | casual
python3 scripts/summarize.py --style brief \
  --normalized out/<ROOM>-<DATE>.normalized.json --room "<ROOM>"   # prints a ready prompt
```
Every preset carries a shared discipline (no editorializing voice · quote verbatim ·
length budget). Add or edit styles in `prompts/summary-styles.md`.

### 4. Verify (before you send a digest)
This is the stage most home-grown pipelines skip and regret. Two shipped gates, plus a
place for your own content policy:

```bash
# a) Length — refuse a message a chat app would SILENTLY truncate. Runs automatically
#    inside send.py too; run it standalone while drafting.
python3 scripts/gates/length_gate.py --file summary.txt --max-chars 3900

# b) Citation — if the summary quotes people, every quoted span must appear verbatim in
#    the raw export (catches a model paraphrasing inside quotation marks).
python3 scripts/gates/citation_gate.py summary.txt out/<ROOM>-<DATE>.raw.csv
```
Both gates print **what they do NOT check** on every run, and both can be waived with a
reason that is printed (never a silent bypass).

> **c) Content policy is YOURS, not the tool's.** These gates check *fidelity* (length,
> quote accuracy) — they do **not** judge whether the content is *appropriate to publish*.
> Publication-appropriateness is a separate axis from factual accuracy, and it depends on
> your room, your audience, and your rules. If you need to block certain content
> (personal data, off-limits topics), add your own check here — the skill deliberately
> ships no opinion about what you may say.

> **d) Is the gate actually running?** A gate rarely fails by giving the wrong verdict —
> it fails by being **off** (skipped because a flag/env/order wasn't set) or **vacuous**
> (it runs but measures an empty set, or silently skips when its input is missing). Both
> are quiet and both let bad output through. A gate that has *never* failed is either
> perfect or not running — prove which. That is why these gates default ON (length runs
> inside `send.py`; run citation yourself before sending) and print *what they measured*
> on every run, so "it ran" is something you can see, not assume.

### 5. Send (optional)
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target <#channel>   --message-file summary.txt   # via Slack MCP (see references)
```
`send.py` runs the **length gate at the single gateway** before any channel dispatch, so a
new caller can't forget it. Over-length → non-zero exit (nothing sent); bypass with
`--waiver "<reason>"` (the reason is printed). Tune the budget with `--max-chars`.

### 6. Record (store to your vault)
Archive the normalized conversation as a markdown note in your Obsidian/LLM-wiki vault.
This can run any time after normalize — it does not require summarize/send.
```bash
python3 scripts/store_to_wiki.py --normalized out/<ROOM>-<DATE>.normalized.json \
  --vault "<ABS vault path>" --subdir "Library/Research/<ROOM>"
```

## Guardrails
- **No live-pipeline mutation** — this skill is a self-contained copy. It shares only the KakaoTalk GUI
  mutex (`/tmp/kakao-gui.lock`) so it serializes with any running export (no concurrent GUI race).
- **macOS Accessibility permission required** (System Settings → Privacy & Security → Accessibility) for the
  osascript provider and `kmsg`.
- **Windows provider must stay labeled experimental** until a real spike — see honesty contract.
- **`send` ≠ one tool**: KakaoTalk uses `kmsg` (macOS AX, KakaoTalk-only); Discord uses bot REST/MCP; Slack
  uses the Slack MCP. `send.py` unifies the *interface*, not the underlying transport.
- **The gates prevent silence, they don't decide for you** — every gate is waivable with a printed reason,
  and every gate states its own blind spots. A tool that hides what it doesn't check breeds overconfidence.
- **A "✓ sent" is not proof of delivery** — read back where you can (see `references/send-channels.md`).
