# kakao-wiki

Turn a **KakaoTalk** chat room into a structured note in your local Obsidian / LLM‑wiki vault — and optionally push a summary back out to KakaoTalk, Discord, or Slack.

One provider‑abstracted job:

```
collect(room) → normalize → store to vault   (+ optional send(channel, message))
```

It packages a battle‑tested KakaoTalk collection recipe as a **portable, installable skill**. KakaoTalk has no public API, so collection drives the app's own **GUI export menu**; the parsing, vault storage, and multi‑channel send are deterministic Python.

---

## Status — honest provider matrix

This repo does **not** pretend every path is production‑ready. Each provider self‑labels:

| Provider | What it does | Platform | Status |
|----------|--------------|----------|--------|
| `macos` (default) | Drives the KakaoTalk GUI export menu via `osascript` (Accessibility), then parses the CSV | macOS | ✅ **GREEN** — verified by a real export run (`references/macos-provider.md`) |
| `windows` | `pywinauto` Ctrl+S local‑text export scaffold | Windows | ⚠️ **spike‑pending** — code‑complete scaffold, UI selectors **not** verified on a real machine. Refuses to claim success until a spike confirms it |
| `db` | Reads the local KakaoTalk DB directly via `kakaocli` | macOS (Win TBD) | 🧪 **experimental** — depends on `kakaocli` key‑derivation succeeding on the host |

The `macos` path is the one to use. `windows`/`db` are shipped transparently so a contributor can finish them — they are **labeled, not hidden**.

### On Windows today — katok-windows + official export (recommended)

KakaoTalk for Windows keeps its local chat DB strongly protected (commercial packer + custom encryption), so there is no macOS-style automatic DB read. The **working, verified path on Windows** is KakaoTalk's official **"Export chat (.txt)"**:

- **If you want search** → use [katok-windows](https://github.com/Hostingglobal-Tech/katok-windows), a CLI that indexes exported `.txt` files for keyword / BM25 / semantic search, shipping only the safe & legal official-export path.
- **If you want the wiki pipeline (this skill)** → feed the same exported `.txt` straight into `normalize.py` (`--raw export.txt` — txt parsing is best-effort; format reports welcome). Automating the export itself (the `windows` provider) remains spike-pending as described below.

So on Windows, "official export → katok-windows for search / kakao-wiki for the wiki" is the combination that works today.

- **Sending summaries/links back to KakaoTalk** → a Windows send channel now exists (`scripts/providers/windows_send.py`, pywinauto) — same honesty rule as the collector: **spike-pending until verified on a real machine** (non-zero exit by default; checklist inside the file). On macOS the existing kmsg path works today.

---

## Requirements

- **Python 3.9+** (standard library only — no pip install needed for the core flow).
- **macOS provider**: KakaoTalk desktop app + `kmsg` (`/opt/homebrew/bin/kmsg`) + **Accessibility permission** granted to KakaoTalk, `kmsg`, and your terminal (System Settings → Privacy & Security → Accessibility).
- **send.py**: `DISCORD_BOT_TOKEN` (Discord), Slack MCP (Slack), or `kmsg` (KakaoTalk). All optional — only needed if you send.

> ⚠️ You are responsible for how you use this tool and for the data you collect with it.

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
```
Produces `out/<ROOM>-<DATE>.raw.csv` and `out/<ROOM>-<DATE>.normalized.json`.

### 2. Store into your vault
```bash
python3 scripts/store_to_wiki.py \
  --normalized out/<ROOM>-<DATE>.normalized.json \
  --vault "/abs/path/to/your/vault" \
  --subdir "Research/<ROOM>"
```
Writes a markdown note with frontmatter (`type`, `tags`, `aliases`, stats).

### 3. (optional) Send a summary
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target "<#channel>" --message-file summary.txt
```
`send.py` unifies the *interface*; the transport differs per channel (kmsg / Discord REST / Slack MCP — see `references/send-channels.md`).

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
    send.py                 # send(channel, message): kakao | discord | slack
    providers/
      macos_osascript.sh    # GREEN: KakaoTalk GUI export -> CSV (mutex + room asserts)
      windows_pywinauto.py  # SPIKE-PENDING: Ctrl+S export + unattended (ⓐ) login/open scaffold
      _credentials.py       # ⓐ credential loading (local ID/PW, password never echoed — uncommitted)
      db_kakaocli.sh        # EXPERIMENTAL: kakaocli DB read -> CSV
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
