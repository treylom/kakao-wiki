#!/usr/bin/env python3
"""windows_pywinauto.py — kakao-wiki Windows provider (⚠️ SPIKE-PENDING until verified).

Goal: real KakaoTalk-on-Windows chat export, the macOS provider's counterpart.
Path: `Ctrl+S` → local .txt save (graded 🟢 — simpler than KakaoTalk's macOS menu chain).

Design so a Windows spike is *minimal*:
  - Everything that does NOT depend on UI selectors is fully implemented here:
    save-dialog path injection, file polling, room verification, txt normalization handoff.
  - The ONLY spike-dependent bits are the window/control selectors, exposed as ENV VARS
    so the spike operator never edits code:
        KW_KAKAO_TITLE_RE   window title regex for the KakaoTalk main/app window
                            (default ".*KakaoTalk.*"; Korean build may be ".*카카오톡.*")
        KW_ROOM_TITLE_RE    chat-room window title regex (default = the room name)
        KW_SAVE_HOTKEY      save hotkey (default "^s")
        KW_DIALOG_WAIT_SEC  seconds to wait for the save dialog (default 8)
        KW_FILE_WAIT_SEC    seconds to wait for the file to land (default 30)

🚨 HONESTY GUARD (source-fact §4):
  Not yet verified on real KakaoTalk Windows. The selectors above are *assumptions*.
  Default run = guidance + non-zero exit (never fakes success). The spike operator runs
  with `--i-have-verified-on-real-windows` AFTER confirming the hotkey + selectors work.
  Checklist: references/windows-provider-spike.md
"""
from __future__ import annotations
import argparse, os, sys, time
from datetime import date
from pathlib import Path

SPIKE_CHECKLIST = """\
[Windows spike — do all before reporting 'works']
 1. KakaoTalk Windows installed + logged in.
 2. Open the TARGET ROOM as a *chat window* by double-click (NOT the search-list state).
 3. Focus the chat window, press the save hotkey (default Ctrl+S) → confirm a
    "save .txt to my PC" dialog appears. If a different hotkey/menu is needed, note it.
 4. Confirm saved file path + name pattern (e.g. KakaoTalk_<room>_<ts>.txt) and that
    normalize.py's txt parser reads it (adjust TXT parser if the format differs).
 5. Find the window title regex for (a) the KakaoTalk window and (b) the room window.
    Export them as KW_KAKAO_TITLE_RE / KW_ROOM_TITLE_RE (no code edit needed).
 6. If a control is not UIA-exposed, fall back to send_keys for that step.
 7. After ONE real export succeeds: rerun with --i-have-verified-on-real-windows,
    paste the env vars used + the verification log into references/windows-provider-spike.md,
    then flip status to GREEN in architecture.md / SKILL.md.
"""


def _verify_room_in_file(path: Path, room: str) -> bool:
    """Selector-free room check: the export's header/first lines should mention the room.
    Conservative — if we can't read it, we do NOT claim a match."""
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    except OSError:
        return False
    # NFC-insensitive substring (KakaoTalk export usually leads with the room title line)
    import unicodedata
    norm = lambda s: unicodedata.normalize("NFC", s)
    return norm(room) in norm(head)


def _export_via_ctrl_s(room: str, out_dir: Path) -> Path:
    """Real export flow. Selector-dependent steps read ENV; everything else is complete."""
    from pywinauto import Application          # type: ignore
    from pywinauto.keyboard import send_keys   # type: ignore

    kakao_re = os.environ.get("KW_KAKAO_TITLE_RE", ".*KakaoTalk.*")
    room_re  = os.environ.get("KW_ROOM_TITLE_RE", f".*{room}.*")
    hotkey   = os.environ.get("KW_SAVE_HOTKEY", "^s")
    dlg_wait = int(os.environ.get("KW_DIALOG_WAIT_SEC", "8"))
    file_wait = int(os.environ.get("KW_FILE_WAIT_SEC", "30"))

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{room}-{date.today().isoformat()}.raw.txt"
    if target.exists():
        target.unlink()

    app = Application(backend="uia").connect(title_re=kakao_re, timeout=10)
    win = app.window(title_re=room_re)
    win.set_focus()
    time.sleep(0.5)
    win.type_keys(hotkey)  # Ctrl+S → save-as dialog

    # Save dialog (standard Win32 "Save As"): type the absolute path into the filename edit
    # and confirm. We drive it by keystrokes so it works even if the dialog's controls are
    # not richly UIA-exposed: select-all, type path, Enter.
    time.sleep(min(dlg_wait, 3))
    try:
        dlg = app.window(title_re=".*(저장|Save).*")
        dlg.wait("exists ready", timeout=dlg_wait)
        edits = dlg.descendants(control_type="Edit")
        if edits:
            edits[0].set_focus()
            send_keys("^a")
            send_keys(str(target).replace(" ", "{SPACE}"), with_spaces=True)
        send_keys("{ENTER}")
    except Exception:
        # Dialog not matched by title — fall back to blind keystrokes (operator confirms in spike)
        send_keys("^a")
        send_keys(str(target), with_spaces=True)
        send_keys("{ENTER}")

    # Poll for the file to land
    deadline = time.time() + file_wait
    while time.time() < deadline:
        if target.exists() and target.stat().st_size > 0:
            break
        time.sleep(0.5)
    if not (target.exists() and target.stat().st_size > 0):
        raise RuntimeError(f"export file not found after {file_wait}s: {target}")

    # Room verification (selector-free, fail-fast like the macOS CSV assert)
    if not _verify_room_in_file(target, room):
        raise RuntimeError(f"room assert FAILED — exported file does not mention '{room}': {target}")
    return target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--i-have-verified-on-real-windows", action="store_true",
                    help="use ONLY after a real KakaoTalk-Windows spike confirmed the hotkey + selectors")
    a = ap.parse_args()

    print("=== kakao-wiki Windows provider ===")
    if not a.__dict__["i_have_verified_on_real_windows"]:
        print(SPIKE_CHECKLIST)
        print("\n⚠️ SPIKE-PENDING — not run (no success faking). After the spike, rerun with "
              "--i-have-verified-on-real-windows (set KW_KAKAO_TITLE_RE / KW_ROOM_TITLE_RE if needed).")
        return 4  # collect.py treats non-zero as the SPIKE-PENDING guard

    try:
        path = _export_via_ctrl_s(a.room, Path(a.out))
    except Exception as e:  # noqa: BLE001 — surface the real failure to the spike operator
        print(f"\n❌ export failed: {type(e).__name__}: {e}")
        print("→ adjust KW_KAKAO_TITLE_RE / KW_ROOM_TITLE_RE / KW_SAVE_HOTKEY and retry (see spike doc).")
        return 4
    print(str(path))  # last stdout line = export path (collect.py contract)
    return 0


if __name__ == "__main__":
    sys.exit(main())
