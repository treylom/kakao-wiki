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
                            (default matches both EN/KR: ".*(KakaoTalk|카카오톡).*")
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

sys.path.insert(0, str(Path(__file__).resolve().parent))  # = providers/ (_credentials 위치)

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


def _require_creds():
    """ⓐ user-credential 모델: 로컬 설정에서 ID/PW 로드. 없으면 안내 후 exit 4.
    PW 는 Secret 래퍼로 감싸 화면/로그에 절대 노출되지 않는다(_credentials.py)."""
    from _credentials import load_credentials, CRED_HELP
    creds = load_credentials()
    if not creds.is_complete():
        sys.stderr.write(CRED_HELP)
        raise SystemExit(4)
    sys.stderr.write(f"[login] credentials loaded (source={creds.source}; id 노출 OK / pw 비노출)\n")
    return creds


def _login_if_needed(app) -> bool:
    """ⓐ 자동 로그인: 로그인 화면이 떠 있을 때만 키보드로 ID→Tab→PW→Enter (좌표 클릭 ❌).
    이미 로그인(세션 유지)이면 creds 없이 즉시 skip → 방오픈/export 만 단독 실측 가능.
    자격증명은 로그인이 실제 필요할 때만 lazy 로드(_require_creds). PW 는 KakaoTalk 입력창에만
    들어가고 stdout/로그 echo 0. 🔬 실측 TODO(spike): 로그인 창 타이틀·필드 탭 순서·2FA 유무."""
    from pywinauto.keyboard import send_keys  # type: ignore
    login_re = os.environ.get("KW_LOGIN_WINDOW_RE", ".*(로그인|Login).*")
    try:
        dlg = app.window(title_re=login_re)
        if not dlg.exists(timeout=int(os.environ.get("KW_LOGIN_WAIT_SEC", "3"))):
            sys.stderr.write("[login] 로그인 창 없음 — 세션 유지로 간주(creds 불요)\n")
            return False
    except Exception:
        return False
    creds = _require_creds()   # 로그인이 실제 필요할 때만 자격증명 요구
    dlg.set_focus()
    time.sleep(0.5)
    send_keys(creds.kakao_id, with_spaces=True)          # ID 화면 노출 OK (재경님 결정)
    send_keys("{TAB}")
    send_keys(creds.password.reveal(), with_spaces=True)  # PW: masked 입력, 로그 echo 0
    send_keys("{ENTER}")
    time.sleep(int(os.environ.get("KW_LOGIN_WAIT_SEC", "8")))
    return True


def _open_room_via_search(app, room: str) -> None:
    """ⓐ 방 자동오픈: 키보드 검색→Enter (좌표 클릭 ❌ = 오클릭 방지).
    🔬 실측 TODO(spike): 검색 포커스 단축키(KW_SEARCH_HOTKEY)·결과 선택키·단일창 패널 구조 확정."""
    from pywinauto.keyboard import send_keys  # type: ignore
    kakao_re = os.environ.get("KW_KAKAO_TITLE_RE", ".*(KakaoTalk|카카오톡).*")
    search_hotkey = os.environ.get("KW_SEARCH_HOTKEY", "^f")  # 🔬 실측 대상(기본 추정)
    main = app.window(title_re=kakao_re)
    main.set_focus()
    time.sleep(0.5)
    send_keys(search_hotkey)
    time.sleep(0.8)
    send_keys(room, with_spaces=True)
    time.sleep(1.2)
    send_keys("{ENTER}")  # 첫 결과(self-chat) 열기
    time.sleep(1.2)


def _unattended_prelude(room: str) -> None:
    """무인 모드 prelude: 로그인(ⓐ creds) + 방 자동오픈 (export 직전).
    ponytail: prelude 가 app 을 connect 하고 _export_via_ctrl_s 가 재-connect = 무해(idempotent).
    실측 후 단일 connect 로 합치고 싶으면 그때 리팩토링(현재는 명확성 우선)."""
    from pywinauto import Application  # type: ignore
    kakao_re = os.environ.get("KW_KAKAO_TITLE_RE", ".*(KakaoTalk|카카오톡).*")
    app = Application(backend="uia").connect(title_re=kakao_re, timeout=15)
    _login_if_needed(app)   # 세션 유지면 creds 없이 skip → 방오픈+export 만 실측 가능
    _open_room_via_search(app, room)


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

    kakao_re = os.environ.get("KW_KAKAO_TITLE_RE", ".*(KakaoTalk|카카오톡).*")  # EN+KR locale
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
    ap.add_argument("--unattended", action="store_true",
                    help="full unattended (ⓐ): auto-login (local user creds) + auto-open room + export. "
                         "Set KW_KAKAO_ID/KW_KAKAO_PW locally (see _credentials.py). Still gated by "
                         "--i-have-verified-on-real-windows until the login/search selectors are spiked.")
    a = ap.parse_args()

    print("=== kakao-wiki Windows provider ===")
    if not a.__dict__["i_have_verified_on_real_windows"]:
        print(SPIKE_CHECKLIST)
        print("\n⚠️ SPIKE-PENDING — not run (no success faking). After the spike, rerun with "
              "--i-have-verified-on-real-windows (set KW_KAKAO_TITLE_RE / KW_ROOM_TITLE_RE if needed).")
        return 4  # collect.py treats non-zero as the SPIKE-PENDING guard

    try:
        if a.unattended:
            _unattended_prelude(a.room)   # ⓐ auto-login + auto-open room (spike-gated)
        path = _export_via_ctrl_s(a.room, Path(a.out))
    except Exception as e:  # noqa: BLE001 — surface the real failure to the spike operator
        print(f"\n❌ export failed: {type(e).__name__}: {e}")
        print("→ adjust KW_KAKAO_TITLE_RE / KW_ROOM_TITLE_RE / KW_SAVE_HOTKEY and retry (see spike doc).")
        return 4
    print(str(path))  # last stdout line = export path (collect.py contract)
    return 0


if __name__ == "__main__":
    sys.exit(main())
