# kakao-wiki

Turn a **KakaoTalk** chat room into a structured note in your local Obsidian / LLM‑wiki vault — and optionally push a summary back out to KakaoTalk, Discord, or Slack.

(한국어 README: [README.md](README.md))

📈 How the production pipeline behind this skill actually runs twice a day (chart + step-by-step spec, in Korean): [docs/WORKFLOW.md](docs/WORKFLOW.md)

The workflow is six stages. Stages 1 collect and 2 normalize are required; stages 3–6 are optional (record can run any time after normalize). What sets this skill apart is that the **verify (4)** slot — the one home‑grown pipelines often skip and later regret — is filled with real gates:

```
1 collect → 2 normalize → 3 summarize
→ 4 verify (length · citation) → 5 send → 6 record
```

**collect → normalize** is the only mandatory part. Summarize, verify, send and record are opt‑in — but **if you send a summary the length gate runs automatically inside `send.py`**, and **if the summary carries quotes, run the citation gate yourself first.**

KakaoTalk has no public API, so collection drives the app's own **GUI export menu**; the parsing, verification, vault storage, and multi‑channel send are plain Python code that gives the same output for the same input, with no LLM involved.

> ⚠️ You are responsible for how you use this tool and for the data you collect with it.

---

## Status — provider matrix, as it stands

This repo does **not** pretend every path is production‑ready. Each provider self‑labels:

| Provider | What it does | Platform | Status |
|----------|--------------|----------|--------|
| `macos` (default on macOS) | Drives the KakaoTalk GUI export menu via `osascript` (Accessibility), then parses the CSV | macOS | ✅ **GREEN** — verified by a real export run (`references/macos-provider.md`) |
| `manual` (default on Windows/WSL) | Picks up a txt/csv you exported yourself from KakaoTalk (**Ctrl+S**) — if `--input` is omitted, searches the default save folders, preferring a file whose name contains the room name, then the newest | any OS | ✅ **GREEN** — the export is KakaoTalk's official feature; everything after is a parser with no LLM involved |
| `windows` | `pywinauto` scaffold that drives KakaoTalk's export-chat menu | Windows | ⚠️ **spike‑pending** — the parts that do not depend on on-screen elements are built, but it will not report success until it has been checked on a real Windows KakaoTalk (non-zero exit by default) |
| `db` | Reads the local KakaoTalk DB directly via `kakaocli` | macOS (Win TBD) | 🧪 **experimental** — depends on `kakaocli` key‑derivation succeeding on the host |

On macOS use `macos`; on Windows/WSL use `manual`. `windows`/`db` are shipped transparently so a contributor can finish them — they are **labeled, not hidden**.

### On Windows today — katok-windows + official export (recommended)

KakaoTalk for Windows keeps its local chat DB strongly protected, so there is no macOS-style automatic DB read. The **path that actually works on Windows** is KakaoTalk's official **"Export chat (.txt)"**:

- **If you want search** → use [katok-windows](https://github.com/Hostingglobal-Tech/katok-windows), a CLI that indexes exported `.txt` files for keyword / BM25 / semantic search (a separate project from this repo).
- **If you want the wiki pipeline (this skill)** → feed the same exported `.txt` (Ctrl+S in the chat window) into the `manual` provider:
  ```bash
  # point at the exported file directly —
  python3 scripts/collect.py --room "<ROOM>" --provider manual --input <exported.txt> --out ./out
  # or save exports into C:\Users\<you>\.kakao-wiki\exports (or Documents/Downloads/Desktop) and omit --input (auto-discovery):
  python3 scripts/collect.py --room "<ROOM>" --provider manual --out ./out
  ```
  On WSL, `C:\Users\<you>\...` is `/mnt/c/Users/<you>/...` — `--input` accepts both spellings. Auto-discovery first picks files whose name contains the room name, then the newest. If the room name cannot be confirmed in an auto-picked file, it stops with an error (exit code 4) rather than collect the wrong room (a file you pass with `--input` only gets a warning).
  The parser supports both the PC `[Name] [오후 2:30]`-style export (date separators, multi-line messages) and the `2026. 6. 18. 오후 8:19, Name : message` style (오전/오후 = AM/PM; Korean-locale KakaoTalk exports only). Automating the export itself (the `windows` provider) remains spike-pending as described below.
- **Not sure where to start** → run the one-shot environment guide:
  ```bash
  python3 scripts/windows_guide.py --room "<ROOM>"
  ```
  It detects Windows/WSL, prints the Ctrl+S steps, previews auto-discovered exports, and checks for katok-windows (with install commands if missing).

So on Windows, "official export → katok-windows for search / kakao-wiki for the wiki" is the combination that works today.

- **Sending summaries/links back to KakaoTalk** → a Windows send channel now exists (`scripts/providers/windows_send.py`, pywinauto) — same rule as the collector: **spike-pending until verified on a real PC** (non-zero exit by default; checklist inside the file). On macOS the existing kmsg path works today. Sending to KakaoTalk is not supported on WSL or Linux (macOS or native Windows only).

---

## Requirements

- **Python 3.9+** (standard library only — no pip install needed for the core flow).
- **macOS provider**: KakaoTalk desktop app + the `kmsg` command-line tool (must be on your PATH; it is not bundled with this repo) + **Accessibility permission** granted to your terminal and `kmsg` (System Settings → Privacy & Security → Accessibility). KakaoTalk must save the exported file as `KakaoTalk_Chat_*.csv` in `~/Downloads` (the script watches only that folder).
- **For document conversion** (optional): `kordoc` + `pdfjs-dist@4` (see "Document conversion" below).
- **send.py**: `DISCORD_BOT_TOKEN` (Discord), `SLACK_WEBHOOK_URL` (a Slack Incoming Webhook), or `kmsg` (KakaoTalk, macOS). All optional — only needed if you send.

---

## Install

```bash
git clone https://github.com/treylom/kakao-wiki.git
cd kakao-wiki
# core flow needs no dependencies; Windows provider (optional): pip install pywinauto
```

Or drop it into a Claude Code / agent skills directory as the `kakao-wiki` skill (see `SKILL.md`).

---

## Usage

`ROOM` = the exact KakaoTalk room name. `OUT` = a working directory. The numbers below match the stage numbers in the flow above.

### 1–2. Collect · Normalize
```bash
# macOS (default, GREEN):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out

# Windows / WSL (default = manual): pick up a txt you exported with Ctrl+S
python3 scripts/collect.py --room "<ROOM>" --provider manual [--input <exported.txt>] --out ./out
```
Produces `out/<ROOM>-<DATE>.raw.csv` (or .txt) and `out/<ROOM>-<DATE>.normalized.json`. Collect (1) and normalize (2) both finish in this one run.

### 3. (optional) Summarize
See "Choosing a summary style" below.

### 4. (optional) Verify before sending — length + citation gates
```bash
# Length — refuse a message a chat app would SILENTLY truncate. Runs inside send.py too.
python3 scripts/gates/length_gate.py --file summary.txt --max-chars 3900
# Citation — if the summary quotes people, every quoted span must appear verbatim in the raw export. (send.py does not run this for you — run it yourself)
python3 scripts/gates/citation_gate.py summary.txt out/<ROOM>-<DATE>.raw.csv
```
- **A truncated message doesn't look truncated — it looks like a short message.** Nothing records that the tail was cut, so without a length gate the sender never knows. That's why `send.py` runs the length gate at the single send gateway (per‑channel defaults: kakao 3900 · Discord 2000 · Slack 4000, tune with `--max-chars`).
- Both gates print **what they do NOT check** on every run (the length gate prints that it does not judge accuracy, quote fidelity, topic coverage, or publication‑appropriateness). The `--waiver "<reason>"` bypass exists only on `length_gate.py` and `send.py`, and the reason is printed. The citation gate has no bypass option.
- **The citation gate does not check short quotes.** A quoted span shorter than `--min-len` (default 4 characters) is skipped, and the gate prints how many it skipped and what they were. If you quote short phrases, check that list by eye.
- Exit codes of both gates: 0 pass · 2 fail · 64 usage error (unknown option, etc.).
- **A gate that has never failed is either perfect or not running.** Being able to ask "is this gate actually running right now?" matters more than adding another gate — so if the gate file is missing, `send.py` **refuses** to send (deleting a gate must not be the shortcut to a pass). Bypass only with an explicit `--allow-missing-gate`.
- ⚠️ **Characters vs bytes**: length is counted in Unicode **codepoints** (one Hangul syllable = 1). Logs and tools often say "N chars" but actually mean bytes (which inflate Hangul ~3×), so double‑check whether any counter you wrote yourself counts bytes or characters.
- **Publication‑appropriateness is not the tool's call** — these gates check *fidelity* (length, quote accuracy) only. Whether content *should* go out depends on your room, audience, and rules; if you must block certain content (personal data, off‑limits topics), add your own check here.

### 5. (optional) Send a summary
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target "<#channel>" --message-file summary.txt
```
`send.py` unifies the *interface*; the transport differs per channel (KakaoTalk = `kmsg` / Discord = REST API / Slack = Incoming Webhook — if the env var `SLACK_WEBHOOK_URL` is unset, nothing is sent and it exits with code 3; see `references/send-channels.md`). The length gate runs at the gateway first, and nothing is sent if it's over budget (bypass with `--waiver "<reason>"`; the reason is printed).

`send.py` does not confirm that a message actually arrived on any channel (KakaoTalk, Discord or Slack); the exit code only means the command or HTTP request finished. Check important sends yourself. Main exit codes: 1 input problem (token, room name, empty body, etc.) · 2 length gate refused (a Discord or Slack HTTP error is also 2) · 3 Slack webhook not set · 66 gate file missing · 6 on Windows, the keystrokes were sent to KakaoTalk but delivery is unconfirmed. KakaoTalk sends pass through the exit code of `kmsg` or the Windows sender, so on the Windows path 2 and 3 mean something else and 5 (UI step failed) is added — see `references/send-channels.md` for the full list.

### 6. (optional) Store into your vault
```bash
python3 scripts/store_to_wiki.py \
  --normalized out/<ROOM>-<DATE>.normalized.json \
  --room "<ROOM>" \
  --vault "/abs/path/to/your/vault" \
  --subdir "Research/<ROOM>"
```
Writes a markdown note with frontmatter (`type`, `tags`, `aliases`, stats). Without `--room`, the room name is taken from the filename up to its first `-`, so a room name containing `-` would be cut short — always pass it. Storing can run any time after normalize, independent of sending.

---

## Unattended collection (Windows, user-credential mode — designed, spike-pending)

To collect on Windows with zero human interaction (auto-login + auto-open room + export):

```bash
# 1) Set credentials LOCALLY (never commit — .gitignored)
#    env:   set KW_KAKAO_ID=...  &  set KW_KAKAO_PW=...
#    or a file outside the repo:  ~/.kakao-wiki/credentials.env  (KW_KAKAO_ID= / KW_KAKAO_PW=)
# 2) Run unattended
python scripts/providers/windows_pywinauto.py --room "<ROOM>" --out ./out \
  --unattended --i-have-verified-on-real-windows
```

- **Credentials are yours**: the ID/PW are set *locally by you*. The public repo never stores a password, and the code is written not to put the password in any log (`scripts/providers/_credentials.py`). Auto-login types only into the password field of the login window and never types the ID. But if it cannot find the password field in the login window, it may type into whichever field has focus — so do not assume the password is never shown on screen until this has been checked on a real Windows machine.
- **Status**: credential loading is implemented, and the only thing covered by a unit test is that the password is masked in its string representation (repr). Credentials are looked up in this order: environment variables → `~/.kakao-wiki/credentials.env` → `<repo>/.env`. The login/search UI automation is promoted to GREEN only after it has been checked on a real KakaoTalk for Windows and the coordinates/controls are pinned down (`references/windows-provider-spike.md`). The export step clicks the room menu (≡) → export chat → text only, by coordinates, and the coordinates can be adjusted through environment variables (`KW_MORE_X_FROM_RIGHT` and others).

> ⚠️ **Single-session constraint (KakaoTalk platform)**: KakaoTalk for PC allows one account to be logged in on one PC at a time. When unattended collection logs in, KakaoTalk on another PC may be logged out. Run it so that "this PC takes the session only while collecting." This is a KakaoTalk limitation, not a bug in this tool.

> Note: the production pipeline in [docs/WORKFLOW.md](docs/WORKFLOW.md) deliberately does not auto-login — a person logs in — because of that session problem. This skill's unattended mode is an optional extra, separate from it.

---

## Choosing a summary style

You can pick how the digest **reads** (voice / format). The tool detects the environment and tells you what to use:

- **If the `/prompt` skill is present**, `summarize.py` prints a one-line hint to use that skill. It does not call the skill itself, and the prompt it prints is still the bundled preset.
- Pick a style from the **bundled presets** (`prompts/summary-styles.md`) — e.g. `brief` (3 short lines) · `detailed` · `bullets` · `formal` (polite report tone) · `casual` (informal tone). Every preset carries a shared discipline (no interpretive or editorializing voice · quote verbatim · length budget).

```bash
# list the presets
python3 scripts/summarize.py --list
# print the summary prompt for a style (pass it straight to your summarizing LLM)
python3 scripts/summarize.py --style brief --normalized out/<ROOM>-<DATE>.normalized.json
```
See `prompts/summary-styles.md` and `SKILL.md` ("3. Summarize") for details.

---

## Document conversion (optional — kordoc)

If a collected attachment/document is in a format you can't just read — **HWP, HWPX, complex XLSX/DOCX tables, Korean PDFs** — convert it to markdown first with [kordoc](https://github.com/chrisryugj/kordoc).

⚠️ **For PDFs, `pdfjs-dist@4` must live in the same `node_modules` as kordoc** (v6 is incompatible). `npx -y kordoc <pdf>` alone fails on PDFs, so for PDFs do this once:
```bash
mkdir kordoc-tmp && cd kordoc-tmp && npm init -y && npm install kordoc pdfjs-dist@4
./node_modules/.bin/kordoc <file>.pdf -d ./out
# HWPX/DOCX/XLSX only, no extra install: npx -y kordoc <file>.hwpx -d ./out
```

---

## How collection works (macOS)

KakaoTalk's only export is a GUI menu, so `macos_osascript.sh` reproduces the human click path with Accessibility, with two safety checks so you never silently collect the **wrong** room:

1. Focus the app, open the chat tab, open the target room.
2. **GUI room check** — confirm the room window exists before exporting.
3. Settings → 대화 내용 관리 → "텍스트 파일로 저장" → confirm.
4. **CSV room check** — confirm the produced CSV's *file name* contains the target room name (NFC‑normalized substring); otherwise stop immediately with an error (fail‑fast).

A global lock (`/tmp/kakao-gui.lock`) keeps concurrent runs from colliding. If another run holds the lock, it waits up to 90 seconds, then takes the lock over and continues (the two room checks above are what guard against a collision then); a lock left over more than 600 seconds is cleaned up. Selectors depend on KakaoTalk's macOS UI (window names, button indices, menu text) — if KakaoTalk updates its UI, re‑derive them; the checks stop with an error instead of silently collecting the wrong room.

---

## Layout

```
kakao-wiki/
  SKILL.md                  # skill manifest (agent-loadable)
  docs/
    WORKFLOW.md             # the original production pipeline: chart + step-by-step spec (Korean)
  scripts/
    collect.py              # provider dispatch: collect(room, provider) -> normalized.json
    normalize.py            # raw export (CSV/txt) -> normalized messages (parser, no GUI)
    store_to_wiki.py        # normalized -> vault markdown note
    summarize.py            # pick a summary style (/prompt detect + presets)
    send.py                 # send(channel, message): kakao | discord | slack (length gate at gateway)
    windows_guide.py        # Windows/WSL environment guide + usage-path hints (read-only)
    gates/
      length_gate.py        # pre-send: refuse a message a chat app would silently truncate (per-channel defaults + waiver)
      citation_gate.py      # verify every quoted span appears verbatim in the raw export (short quotes skipped and listed)
    providers/
      macos_osascript.sh    # GREEN: KakaoTalk GUI export -> CSV (lock + room checks)
      windows_pywinauto.py  # SPIKE-PENDING: menu export + unattended login/open scaffold (coordinate ENV)
      windows_send.py       # SPIKE-PENDING: Windows KakaoTalk send (pywinauto)
      _credentials.py       # user-credential loading (local ID/PW, password never echoed — keep ID/PW local, never commit)
      db_kakaocli.sh        # EXPERIMENTAL: kakaocli DB read -> CSV
  tests/                    # unit tests for the parser and the Windows provider contract (python3 -m unittest)
  prompts/
    summary-styles.md       # preset summary-style prompts + shared discipline
  references/
    architecture.md         # provider abstraction + data flow + Windows feasibility grades
    macos-provider.md       # osascript dependency points + verification log
    windows-provider-spike.md  # Windows spike checklist
    send-channels.md        # kmsg(kakao) / Discord(REST) / Slack(Webhook) notes
```

---

## Contributing

The highest‑value contribution is finishing the **Windows provider spike** (`references/windows-provider-spike.md` lists exactly what to verify) or hardening the **db provider**. Please do not relabel any provider GREEN until it is verified on a real machine.

## License

MIT — see [LICENSE](LICENSE).
