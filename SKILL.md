---
name: kakao-wiki
description: >-
  Collect a KakaoTalk chat room's conversation history, normalize it into structured
  messages, store it into your local Obsidian/LLM-wiki vault, and (optionally) summarize
  and send a digest out to KakaoTalk / Discord / Slack. A portable, installable skill
  built around the common summarize-and-send workflow, with a provider abstraction and
  pre-send verification gates (message length + quote citation).
  macOS(osascript GUI export) is the GREEN/default path; manual(a txt/csv you export from
  the KakaoTalk app yourself — the Windows/WSL today-path) is GREEN; Windows(pywinauto
  auto-export) ships as an experimental scaffold; a DB-direct(kakaocli) path is provided
  as an opt-in experiment.
  Use when the user wants to "collect a KakaoTalk room", "summarize a kakao chat", "turn
  a kakao chat into my wiki", "set up kakao-wiki", "export kakaotalk to obsidian", "use
  kakao-wiki on Windows/WSL", or "automate a kakao chat digest".
---

# kakao-wiki — collect → summarize → verify → send, KakaoTalk to your vault

This skill packages the common **"summarize a chat room and send it out"** workflow as a
**portable, installable** skill, with a provider abstraction for collection and
**pre-send verification gates** so a digest does not go out silently truncated, and so
misquoted lines can be caught before sending.

The pipeline is six stages. Stages 1-2 are required; stages 3-6 are optional depending on
what you want:

```
1 collect → 2 normalize → 3 summarize → 4 verify → 5 send → 6 record
  (provider)  (parser)     (optional)    (gates)   (optional) (to vault)
```

Only **collect → normalize** is mandatory (you always need messages first). Summarize,
verify, send and record are opt-in; record can run any time after normalize. **If you
send, the length gate runs automatically inside `send.py`.** The citation gate is a
manual step: **if you build a cited summary, run it yourself before sending.**

> **Provenance.** Generalized from (a copy of — the original was not changed) a
> production KakaoTalk collection-and-digest pipeline: a GUI-export recipe, a message
> parser, and the length/citation gates that pipeline learned it needed the expensive way.
> Design rationale + Windows feasibility grading: `references/architecture.md`.
> How that production pipeline runs today (schedule, gates, failure paths, and which parts
> this skill does *not* ship): `docs/WORKFLOW.md`. Note: it now collects by reading the
> messenger's local DB directly, with GUI export as fallback — that does **not** promote
> this skill's `db` provider, which stays experimental. It also never logs in
> automatically (a person does); the optional unattended-login mode below is something
> this skill adds on top.

## Honesty contract (status labels are earned, not assumed)
- **macOS provider = GREEN** — verified by a real KakaoTalk export run (see `references/macos-provider.md` → "검증 로그 (Verification log)").
- **manual provider = GREEN** — it only picks up a file you exported with KakaoTalk's own export; basis = the official export format plus the parser tests (`tests/test_normalize_pc_txt.py`, `tests/test_normalize_windows_txt.py`).
- **Windows provider = `spike-pending` / experimental** — code-complete *scaffold*. The export click path (room ≡ menu → 대화 내보내기 → 텍스트만 저장) was hand-measured once on a real machine (2026-06-25), but the scaffold itself has not been run end-to-end there. Do **not** report it as "working" until a Windows spike confirms it. `collect.py --provider windows` always stops at a guard after printing the checklist; to try the scaffold, run `scripts/providers/windows_pywinauto.py` directly (see `references/windows-provider-spike.md`).
- **DB-direct provider = experimental** — depends on `kakaocli` key-derivation succeeding on the host.

## Capabilities map (what's reused vs new)

| Layer | Source | Status |
|-------|--------|--------|
| macOS GUI export recipe | generalized export recipe (mutex + room assert + CSV room-check) | **GREEN** (copied/generalized) |
| message normalize/parse | generalized message parser | **GREEN** (copied/generalized) |
| **length gate (pre-send)** | `scripts/gates/length_gate.py` | **shipped** — refuses silent truncation |
| **citation gate (verbatim quotes)** | `scripts/gates/citation_gate.py` | **shipped** — verifies quotes against the raw export |
| provider abstraction | `collect(room, provider)` dispatch | this skill |
| manual provider | auto-discovery of a txt/csv you exported yourself + room fail-fast | **GREEN** (Windows/WSL today-path) |
| Windows guide | `windows_guide.py` env-detect + install guide | this skill |
| Windows provider | pywinauto menu export (≡ → 대화 내보내기 → 텍스트만 저장) | **spike-pending** |
| DB-direct provider | `kakaocli messages` wrapper | experimental |
| vault store | normalized → LLM-wiki md | this skill |
| send abstraction | `send(channel,msg)` kmsg/Discord/Slack, length gate at the gateway | this skill |

## Layout
```
kakao-wiki/
  SKILL.md
  scripts/
    collect.py              # provider dispatch: collect(room, provider) -> normalized.json (incl. manual)
    windows_guide.py        # Windows/WSL diagnosis + export steps + katok-windows install hint (read-only)
    normalize.py            # raw export (CSV/txt) -> normalized messages (parser, no GUI)
    store_to_wiki.py        # normalized -> vault markdown note
    summarize.py            # pick a summary STYLE (prints a preset prompt; hints at the /prompt skill if present)
    send.py                 # send(channel, message): kakao | discord | slack (length gate at gateway)
    gates/
      length_gate.py        # pre-send: refuse a message a chat app would silently truncate
      citation_gate.py      # verify every quoted span appears verbatim in the raw export
    providers/
      macos_osascript.sh    # GREEN: KakaoTalk GUI export -> CSV (mutex + room asserts)
      windows_pywinauto.py  # SPIKE-PENDING: menu export to a local txt (click offsets via ENV)
      windows_send.py       # SPIKE-PENDING: send a message to a room on Windows (pywinauto)
      _credentials.py       # loads KW_KAKAO_ID / KW_KAKAO_PW for the optional unattended login
      db_kakaocli.sh        # EXPERIMENTAL: kakaocli DB read -> CSV
  prompts/
    summary-styles.md       # preset summary-style prompts + shared discipline (voice/quote/budget)
  references/
    architecture.md         # provider abstraction + data flow + Windows feasibility grades
    macos-provider.md       # osascript dependency points + verification log
    windows-provider-spike.md  # Windows scaffold + spike checklist (what to verify)
    send-channels.md        # kmsg(kakao)/Discord(REST)/Slack(webhook or MCP) notes
  docs/
    WORKFLOW.md             # how the production pipeline this skill came from runs
  tests/                    # parser and Windows-provider contract tests (python3 -m unittest)
```

# Workflow

Run from the skill root. `ROOM` = the exact KakaoTalk room name. `OUT` = a working dir.

### 1. Collect (provider-abstracted)
```bash
# macOS (default on macOS, GREEN):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out

# manual (default on Windows/WSL/Linux, GREEN) — picks up a txt you exported from the
# KakaoTalk app yourself (Ctrl+S, or the room menu's export).
#   Without --input it searches the newest KakaoTalk export in ~/.kakao-wiki/exports,
#   Documents, Downloads and Desktop (on WSL also the same folders in each Windows user profile under /mnt/c).
#   A file picked automatically whose header/name does not mention the room stops the run
#   (fail-fast); a file you pass with --input only produces a warning.
python3 scripts/collect.py --room "<ROOM>" --provider manual [--input <exported.txt>] --out ./out

# Windows auto-export (experimental scaffold — always stops at its guard until spike-verified):
python3 scripts/collect.py --room "<ROOM>" --provider windows --out ./out

# DB-direct (experimental):
python3 scripts/collect.py --room "<ROOM>" --provider db --out ./out
```
Produces `out/<ROOM>-<DATE>.raw.csv` (or .txt) and `out/<ROOM>-<DATE>.normalized.json`.

> **Windows / WSL users (agent instruction):** first run
> `python3 scripts/windows_guide.py --room "<ROOM>"` and show its output — it detects the
> environment, walks the manual export, previews auto-discovery, and checks for the
> katok-windows search CLI. Today's path on Windows = KakaoTalk's own export → the
> `manual` provider above. The `windows` auto-export provider is spike-pending — don't
> promise it "just works".
>
> **Unattended login (opt-in, Windows scaffold only):** `windows_pywinauto.py --unattended`
> can log in by typing only the password (`KW_KAKAO_ID`/`KW_KAKAO_PW` are loaded by
> `_credentials.py`). The PC app allows one logged-in PC per account, so logging in
> elsewhere can end another PC session — leave this off unless you accept that.

### 2. Normalize
`collect.py` already emits `normalized.json`. If you *already have* a raw export (someone
sent you an exported txt, or you have a CSV), normalize it directly:
```bash
python3 scripts/normalize.py --raw <raw.csv|raw.txt> --out out/<ROOM>-<DATE>.normalized.json
```
Optional: `--since <date>` cuts older messages (see `normalize.py --help`).
The parser absorbs CSV and txt into one message schema, so every later stage is
provider-agnostic. (Topic clustering / analysis is intentionally out of scope — this skill
takes you to normalized messages.)

### 3. Summarize (optional)
Let the user pick how the digest reads. `summarize.py` always prints a bundled preset
prompt; if it detects the `/prompt` skill it only adds a one-line hint suggesting it.
Pipe the printed prompt to your summary LLM, write the result to `summary.txt`, then
verify and send.
```bash
python3 scripts/summarize.py --list                       # brief | detailed | bullets | formal | casual
python3 scripts/summarize.py --style brief \
  --normalized out/<ROOM>-<DATE>.normalized.json --room "<ROOM>"   # prints a ready prompt
```
Every preset carries a shared discipline (no editorializing voice · quote verbatim, or no
quotes at all · length budget). Add or edit styles in `prompts/summary-styles.md`.

### 4. Verify (before you send a digest)
This is the stage most home-grown pipelines skip and regret. Two shipped gates, plus a
place for your own content policy:

```bash
# a) Length — refuse a message a chat app would SILENTLY truncate. Runs automatically
#    inside send.py too; run it standalone while drafting. (Default budget 3900 = kakao;
#    for Discord/Slack use the channel budgets in section 5.)
python3 scripts/gates/length_gate.py --file summary.txt --max-chars 3900

# b) Citation — if the summary quotes people, every quoted span must appear verbatim in
#    the raw export (catches a model paraphrasing inside quotation marks).
python3 scripts/gates/citation_gate.py summary.txt out/<ROOM>-<DATE>.raw.csv
```
Both gates print **what they do NOT check** on every run. Exit codes for both: `0` pass ·
`2` FAIL · `64` usage error (bad or missing flags, unreadable file), so `2` always means
a real FAIL. Only the length gate can be waived (`--waiver "<reason>"`, and the reason is
printed — never a silent bypass); the citation gate has no waiver. Quotes shorter than
`--min-len` (default 4 characters) are not checked, but the citation gate lists each
skipped quote in its output.

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
> perfect or not running — prove which. That is why the length gate is on by default
> inside `send.py` (the citation gate is a manual step you run yourself), and why both
> print *what they measured* on every run, so "it ran" is something you can see, not
> assume.

### 5. Send (optional)
`kakao` needs the `kmsg` command-line tool on your PATH (not bundled with this repo).
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target <#channel>   --message-file summary.txt   # needs SLACK_WEBHOOK_URL (else exit 3; then the agent posts it with its own Slack tool via MCP)
```
`send.py` runs the **length gate at the single gateway** before any channel dispatch, so a
new caller can't forget it. Over-length → exit 2 (nothing sent); bypass with
`--waiver "<reason>"` (the reason is printed). Tune the budget with `--max-chars`; the
per-channel defaults are **kakao 3900 · discord 2000 · slack 4000**. Other exit codes:
`1` missing token/room/empty body · `3` Slack webhook not set · `66` length-gate file
missing. On Windows the kakao path returns `6` once the keys have been sent
(delivery unconfirmed), never `0`. `send.py` does not confirm delivery on any channel.

### 6. Record (store to your vault)
Archive the normalized conversation as a markdown note in your Obsidian/LLM-wiki vault.
This can run any time after normalize — it does not require summarize/send.
```bash
python3 scripts/store_to_wiki.py --normalized out/<ROOM>-<DATE>.normalized.json \
  --room "<ROOM>" --vault "<ABS vault path>" --subdir "<folder>/<ROOM>"
```
Pass `--room` explicitly: otherwise the room is taken from the part of the file name
before the first `-`, which cuts a room name that contains a hyphen.

## Guardrails
- **No live-pipeline mutation** — this skill is a self-contained copy. It shares only the KakaoTalk GUI
  lock (`/tmp/kakao-gui.lock`) with other exports. The lock serializes runs, but the macOS script
  takes it over after waiting 90 s, while an export can hold it for up to 600 s; the room checks
  (GUI window + CSV file name) are the backstop against a second run driving the GUI.
- **macOS Accessibility permission required** (System Settings → Privacy & Security → Accessibility) for the
  osascript provider and `kmsg`.
- **Windows provider must stay labeled experimental** until a real spike — see honesty contract.
- **`send` ≠ one tool**: KakaoTalk uses `kmsg` (macOS AX, KakaoTalk-only; `windows_send.py` on Windows);
  Discord uses the bot REST API; Slack uses an Incoming Webhook from `send.py`, or the agent's own Slack tool (MCP) when the
  agent posts it. `send.py` unifies the *interface*, not the underlying transport.
- **The gates prevent silence, they don't decide for you** — the length gate is waivable with a printed
  reason, and every gate states its own blind spots. A tool that hides what it doesn't check breeds
  overconfidence.
- **A "✓ sent" is not proof of delivery** — read back where you can (see `references/send-channels.md`).
