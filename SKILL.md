---
name: kakao-wiki
description: >-
  Collect a KakaoTalk chat room's conversation history, normalize it into structured
  messages, store it into your local Obsidian/LLM-wiki vault, and (optionally) send a
  summary out to KakaoTalk / Discord / Slack. Mirrors the proven aktofu collection
  recipe as a portable, installable skill with a provider abstraction:
  macOS(osascript GUI export) is the GREEN/default path; Windows(pywinauto Ctrl+S) ships
  as an experimental scaffold; a DB-direct(kakaocli) path is provided as an opt-in
  experiment. Use when the user wants to "collect a KakaoTalk room", "turn a kakao chat
  into my wiki", "set up kakao-wiki", "export kakaotalk to obsidian", or "automate a
  kakao chat digest".
---

# kakao-wiki — KakaoTalk → normalized → vault, with multi-channel send

This skill packages the aktofu KakaoTalk collection pipeline as a **portable, installable** skill.
It does **one provider-abstracted job**: `collect(room) → normalized messages → store to vault`, plus an optional `send(channel, msg)`.

> **Provenance.** Generalized (copied, NOT live-modified) from a production KakaoTalk
> collection pipeline: a GUI-export recipe, a message parser, and citation/topic quality gates.
> Design rationale + Windows feasibility grading: `references/architecture.md`.

## ⚠️ Honesty contract (source-fact §4)
- **macOS provider = GREEN** — verified by a real KakaoTalk export run (see `references/macos-provider.md` → "Verification log").
- **Windows provider = `spike-pending` / experimental** — code-complete *scaffold* only. The KakaoTalk
  Windows UI selectors/keys are NOT verified on a real machine. Do **not** report it as "working" until a
  Windows spike confirms it (selectors re-derived). The script self-labels its status.
- **DB-direct provider = experimental** — depends on `kakaocli` key-derivation succeeding on the host.

## Capabilities map (what's reused vs new)

| Layer | Source | Status |
|-------|--------|--------|
| macOS GUI export recipe | aktofu `export-kakaotalk.sh` (mutex + room assert + CSV room-check) | **GREEN** (copied/generalized) |
| message normalize/parse | aktofu `step2-analyze.py` | **GREEN** (copied/generalized) |
| quality gates (citation/topic) | aktofu `citation_gate.py` / `topic_boundary_gate.py` | reused (pointer) |
| provider abstraction | NEW — `collect(room, provider)` dispatch | this skill |
| Windows provider | NEW scaffold — pywinauto Ctrl+S local txt | **spike-pending** |
| DB-direct provider | NEW wrapper — `kakaocli query` | experimental |
| vault store | NEW — normalized → LLM-wiki md | this skill |
| send abstraction | NEW — `send(channel,msg)` kmsg/Discord/Slack | this skill |

## Layout
```
kakao-wiki/
  SKILL.md
  scripts/
    collect.py              # provider dispatch: collect(room, provider) -> normalized.json
    normalize.py            # raw export (CSV/txt) -> normalized messages (parser, no GUI)
    store_to_wiki.py        # normalized -> vault markdown note
    summarize.py            # pick a summary STYLE (detect /prompt skill, else presets)
    send.py                 # send(channel, message): kakao | discord | slack
    providers/
      macos_osascript.sh    # GREEN: KakaoTalk GUI export -> CSV (mutex + room asserts)
      windows_pywinauto.py  # SPIKE-PENDING: Ctrl+S local txt export (selectors via ENV)
      db_kakaocli.sh        # EXPERIMENTAL: kakaocli DB read -> CSV
  prompts/
    summary-styles.md       # preset summary-style prompts (brief/detailed/bullets/formal/casual)
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
# macOS (default, GREEN):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out

# Windows (experimental scaffold — refuses to claim success until spike-verified):
python3 scripts/collect.py --room "<ROOM>" --provider windows --out ./out

# DB-direct (experimental):
python3 scripts/collect.py --room "<ROOM>" --provider db --out ./out
```
Produces `out/<ROOM>-<DATE>.raw.csv` (or .txt) and `out/<ROOM>-<DATE>.normalized.json`.

### 2. Store into vault (LLM wiki)
```bash
python3 scripts/store_to_wiki.py --normalized out/<ROOM>-<DATE>.normalized.json \
  --vault "<ABS vault path>" --subdir "Library/Research/<ROOM>"
```

### 2.5 (optional) Choose a summary style
Let the user pick how the digest reads. `summarize.py` auto-detects the `/prompt` skill
(uses it if present) and otherwise emits a bundled preset prompt; pipe its output to your
summary LLM, write the result to `summary.txt`, then send it.
```bash
python3 scripts/summarize.py --list                       # brief | detailed | bullets | formal | casual
python3 scripts/summarize.py --style brief \
  --normalized out/<ROOM>-<DATE>.normalized.json --room "<ROOM>"   # prints a ready prompt
```
Add or edit styles in `prompts/summary-styles.md` (one `## <id>` + fenced prompt each).

### 3. (optional) Send a summary
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target <#channel>   --message-file summary.txt   # via Slack MCP (see references)
```

### 4. Quality gates (when producing a cited digest)
If you build a cited summary, validate every quote against the raw export with your own
citation gate (each quoted line must appear verbatim in `out/<ROOM>-<DATE>.raw.csv`):
```bash
python3 <your-gates>/citation_gate.py <digest>.md out/<ROOM>-<DATE>.raw.csv
```

## Guardrails
- **No live-pipeline mutation** — this skill is a self-contained copy. It shares only the KakaoTalk GUI
  mutex (`/tmp/kakao-gui.lock`) so it serializes with any running aktofu export (no concurrent GUI race).
- **macOS Accessibility permission required** (System Settings → Privacy & Security → Accessibility) for the
  osascript provider and `kmsg`.
- **Windows provider must stay labeled experimental** until a real spike — see honesty contract.
- **`send` ≠ one tool**: KakaoTalk uses `kmsg` (macOS AX, KakaoTalk-only); Discord uses bot REST/MCP; Slack
  uses the Slack MCP. `send.py` unifies the *interface*, not the underlying transport.
