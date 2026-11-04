# kakao-wiki

Turn a **KakaoTalk** chat room into a structured note in your local Obsidian / LLM‑wiki vault — and optionally push a summary back out to KakaoTalk, Discord, or Slack.

(한국어 README: [README.md](README.md))

📈 How the production pipeline behind this skill actually runs twice a day (chart + step-by-step spec, in Korean): [docs/WORKFLOW.md](docs/WORKFLOW.md)

The workflow is six stages; the middle three are optional. What sets this skill apart is that the **verify (4)** slot — the one home‑grown pipelines routinely skip and regret — is filled with real gates:

```
1 collect → 2 normalize → 3 summarize
→ 4 verify (length · citation) → 5 send → 6 record
```

**collect → normalize** is the only mandatory part. Summarize, verify, send and record are opt‑in — but **if you send a summary the length gate runs automatically**, and **if the summary carries quotes, run the citation gate first.**

It packages a battle‑tested KakaoTalk collection recipe as a **portable, installable skill**. KakaoTalk has no public API, so collection drives the app's own **GUI export menu**; the parsing, verification, vault storage, and multi‑channel send are deterministic Python.

> ⚠️ You are responsible for how you use this tool and for the data you collect with it.

---

## Status — honest provider matrix

This repo does **not** pretend every path is production‑ready. Each provider self‑labels:

| Provider | What it does | Platform | Status |
|----------|--------------|----------|--------|
| `macos` (default on macOS) | Drives the KakaoTalk GUI export menu via `osascript` (Accessibility), then parses the CSV | macOS | ✅ **GREEN** — verified by a real export run (`references/macos-provider.md`) |
| `manual` (default on Windows/WSL) | Picks up a txt/csv you exported yourself from KakaoTalk (**Ctrl+S**) — auto‑discovers the latest export if `--input` is omitted | any OS | ✅ **GREEN** — the export is KakaoTalk's official feature; everything after is a deterministic parser |
| `windows` | `pywinauto` Ctrl+S local‑text export scaffold | Windows | ⚠️ **spike‑pending** — code‑complete scaffold, UI selectors **not** verified on a real machine. Refuses to claim success until a spike confirms it |
| `db` | Reads the local KakaoTalk DB directly via `kakaocli` | macOS (Win TBD) | 🧪 **experimental** — depends on `kakaocli` key‑derivation succeeding on the host |

On macOS use `macos`; on Windows/WSL use `manual`. `windows`/`db` are shipped transparently so a contributor can finish them — they are **labeled, not hidden**.

### On Windows today — katok-windows + official export (recommended)

KakaoTalk for Windows keeps its local chat DB strongly protected (commercial packer + custom encryption), so there is no macOS-style automatic DB read. The **working, verified path on Windows** is KakaoTalk's official **"Export chat (.txt)"**:

- **If you want search** → use [katok-windows](https://github.com/Hostingglobal-Tech/katok-windows), a CLI that indexes exported `.txt` files for keyword / BM25 / semantic search, shipping only the safe & legal official-export path.
- **If you want the wiki pipeline (this skill)** → feed the same exported `.txt` (Ctrl+S in the chat window) into the `manual` provider:
  ```bash
  # point at the exported file directly —
  python3 scripts/collect.py --room "<ROOM>" --provider manual --input <exported.txt> --out ./out
  # or save exports into C:\Users\<you>\.kakao-wiki\exports (or Documents/Downloads) and omit --input (auto-discovery):
  python3 scripts/collect.py --room "<ROOM>" --provider manual --out ./out
  ```
  On WSL, `C:\Users\<you>\...` is `/mnt/c/Users/<you>/...` — `--input` accepts both spellings.
  The parser supports both the PC `[Name] [PM 2:30]`-style export (date separators, multi-line messages) and the `2026. 6. 18. PM 8:19, Name : message` style. Automating the export itself (the `windows` provider) remains spike-pending as described below.
- **Not sure where to start** → run the one-shot environment guide:
  ```bash
  python3 scripts/windows_guide.py --room "<ROOM>"
  ```
  It detects Windows/WSL, prints the Ctrl+S steps, previews auto-discovered exports, and checks for katok-windows (with install commands if missing).

So on Windows, "official export → katok-windows for search / kakao-wiki for the wiki" is the combination that works today.

- **Sending summaries/links back to KakaoTalk** → a Windows send channel now exists (`scripts/providers/windows_send.py`, pywinauto) — same honesty rule as the collector: **spike-pending until verified on a real machine** (non-zero exit by default; checklist inside the file). On macOS the existing kmsg path works today.

---

## Requirements

- **Python 3.9+** (standard library only — no pip install needed for the core flow).
- **macOS provider**: KakaoTalk desktop app + `kmsg` (`/opt/homebrew/bin/kmsg`) + **Accessibility permission** granted to KakaoTalk, `kmsg`, and your terminal (System Settings → Privacy & Security → Accessibility).
- **For document conversion** (optional): `kordoc` + `pdfjs-dist@4` (see "Document conversion" below).
- **send.py**: `DISCORD_BOT_TOKEN` (Discord), Slack MCP (Slack), or `kmsg` (KakaoTalk). All optional — only needed if you send.

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

`ROOM` = the exact KakaoTalk room name. `OUT` = a working directory.

### 1. Collect
```bash
# macOS (default, GREEN):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out

# Windows / WSL (default = manual): pick up a txt you exported with Ctrl+S
python3 scripts/collect.py --room "<ROOM>" --provider manual [--input <exported.txt>] --out ./out
```
Produces `out/<ROOM>-<DATE>.raw.csv` (or .txt) and `out/<ROOM>-<DATE>.normalized.json`.

### 2. Store into your vault
```bash
python3 scripts/store_to_wiki.py \
  --normalized out/<ROOM>-<DATE>.normalized.json \
  --vault "/abs/path/to/your/vault" \
  --subdir "Research/<ROOM>"
```
Writes a markdown note with frontmatter (`type`, `tags`, `aliases`, stats).

### 3. (optional) Verify before sending — length + citation gates
```bash
# Length — refuse a message a chat app would SILENTLY truncate. Runs inside send.py too.
python3 scripts/gates/length_gate.py --file summary.txt --max-chars 3900
# Citation — if the summary quotes people, every quoted span must appear verbatim in the raw export.
python3 scripts/gates/citation_gate.py summary.txt out/<ROOM>-<DATE>.raw.csv
```
- **A truncated message doesn't look truncated — it looks like a short message.** Nothing records that the tail was cut, so without a length gate the sender never knows. That's why `send.py` runs the length gate at the single send gateway (per‑channel defaults: kakao 3900 · Discord 2000 · Slack 4000, tune with `--max-chars`).
- Both gates print **what they do NOT check** on every run (the length gate prints that it does not judge accuracy, quote fidelity, topic coverage, or publication‑appropriateness), and any bypass prints its **reason** (never a silent skip).
- **A gate that has never failed is either perfect or not running.** Being able to ask "is this gate actually running right now?" matters more than adding another gate — so if the gate file is missing, `send.py` **refuses** to send (deleting a gate must not be the shortcut to a pass). Bypass only with an explicit `--allow-missing-gate`.
- ⚠️ **Characters vs bytes**: length is counted in Unicode **codepoints** (one Hangul syllable = 1). Logs and tools often say "N chars" but actually mean bytes (which inflate Hangul ~3×), so double‑check this axis on any counter you rolled yourself.
- **Publication‑appropriateness is not the tool's call** — these gates check *fidelity* (length, quote accuracy) only. Whether content *should* go out depends on your room, audience, and rules; if you must block certain content (personal data, off‑limits topics), add your own check here.

### 4. (optional) Send a summary
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target "<#channel>" --message-file summary.txt
```
`send.py` unifies the *interface*; the transport differs per channel (kmsg / Discord REST / Slack MCP — see `references/send-channels.md`). The length gate runs at the gateway first, and nothing is sent if it's over budget (bypass with `--waiver "<reason>"`; the reason is printed).

---

## Unattended collection (Windows ⓐ — designed, spike-pending)

To collect on Windows with zero human interaction (auto-login + auto-open room + export):

```bash
# 1) Set credentials LOCALLY (never commit — .gitignored)
#    env:   set KW_KAKAO_ID=...  &  set KW_KAKAO_PW=...
#    or a file outside the repo:  ~/.kakao-wiki/credentials.env
# 2) Run unattended
python scripts/providers/windows_pywinauto.py --room "<ROOM>" --out ./out \
  --unattended --i-have-verified-on-real-windows
```

- **Credentials are yours**: the ID/PW are set *locally by you*. The public repo never stores a password; the password is typed only into KakaoTalk and never shown on screen or in logs (`scripts/providers/_credentials.py`).
- **Status**: the credential layer is complete and verified. The login/search UI automation is GREEN-promoted only after a real KakaoTalk-Windows spike pins the selectors (`references/windows-provider-spike.md`).

> ⚠️ **Single-session constraint (KakaoTalk platform)**: KakaoTalk allows one account on one device at a time. The moment unattended collection logs in, your other device (phone, etc.) gets logged out of KakaoTalk. Run it as "this PC takes the session only while collecting; use other devices freely otherwise." This is a KakaoTalk limitation, not a bug in this tool.

---

## Choosing a summary style

You can pick how the digest **reads** (voice / format). The tool auto‑detects the environment:

- **If the `/prompt` skill is present**, it generates the summary prompt with that skill.
- Otherwise it uses a **bundled preset** (`prompts/summary-styles.md`) — e.g. `brief` · `detailed` · `bullets` · `formal` · `casual`. Every preset carries a shared discipline (no editorializing voice · quote verbatim · length budget).

```bash
python3 scripts/summarize.py --list
python3 scripts/summarize.py --style brief --normalized out/<ROOM>-<DATE>.normalized.json
```
See `prompts/summary-styles.md` and `SKILL.md` for details.

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

KakaoTalk's only export is a GUI menu, so `macos_osascript.sh` reproduces the human click path with Accessibility, with two safety asserts so you never silently collect the **wrong** room:

1. Focus the app, open the chat tab, open the target room.
2. **GUI room hard‑assert** — confirm the room window exists before exporting.
3. Settings → 대화 내용 관리 → "텍스트 파일로 저장" → confirm.
4. **CSV room hard‑assert** — confirm the produced CSV actually belongs to the target room (NFC‑normalized substring), else fail‑fast.

A global mutex (`/tmp/kakao-gui.lock`) serializes GUI access so concurrent runs don't race. Selectors depend on KakaoTalk's macOS UI (window names, button indices, menu text) — if KakaoTalk updates its UI, re‑derive them; the asserts fail loudly rather than mis‑collecting.

---

## Layout

```
kakao-wiki/
  SKILL.md                  # skill manifest (agent-loadable)
  scripts/
    collect.py              # provider dispatch: collect(room, provider) -> normalized.json
    normalize.py            # raw export (CSV/txt) -> normalized messages (parser, no GUI)
    store_to_wiki.py        # normalized -> vault markdown note
    summarize.py            # pick a summary style (/prompt detect + presets)
    send.py                 # send(channel, message): kakao | discord | slack (length gate at gateway)
    gates/
      length_gate.py        # pre-send: refuse a message a chat app would silently truncate
      citation_gate.py      # verify every quoted span appears verbatim in the raw export
    providers/
      macos_osascript.sh    # GREEN: KakaoTalk GUI export -> CSV (mutex + room asserts)
      windows_pywinauto.py  # SPIKE-PENDING: Ctrl+S export + unattended (ⓐ) login/open scaffold
      _credentials.py       # ⓐ credential loading (local ID/PW, password never echoed — uncommitted)
      db_kakaocli.sh        # EXPERIMENTAL: kakaocli DB read -> CSV
  prompts/
    summary-styles.md       # preset summary-style prompts + shared discipline
  references/
    architecture.md         # provider abstraction + data flow + Windows feasibility grades
    macos-provider.md       # osascript dependency points + verification log
    windows-provider-spike.md  # Ctrl+S scaffold + spike checklist
    send-channels.md        # kmsg(kakao) / Discord(REST) / Slack(MCP) notes
```

---

## Contributing

The highest‑value contribution is finishing the **Windows provider spike** (`references/windows-provider-spike.md` lists exactly what to verify) or hardening the **db provider**. Keep the honesty contract: never relabel a provider GREEN until it's verified on a real machine.

## License

MIT — see [LICENSE](LICENSE).
