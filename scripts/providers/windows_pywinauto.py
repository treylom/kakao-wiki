#!/usr/bin/env python3
"""windows_pywinauto.py — kakao-wiki Windows provider (live replay blocked in Codex sandbox).

Goal: real KakaoTalk-on-Windows chat export, the macOS provider's counterpart.
Path measured by user on 2026-06-25 KST:
  tray restore → login window title "카카오톡" → Edit[1] password →
  main search "나와의 채팅" → room ≡ menu → 대화 내보내기 → 텍스트만 저장.

Design:
  - Measured stable selectors are defaults:
        class_name          EVA_Window
        title/login title   카카오톡
        login password      second Edit control
  - Custom-draw controls fall back to coordinate offsets, exposed as ENV VARS:
        KW_KAKAO_TITLE_RE   window title regex for the KakaoTalk main/app window
                            (default matches both EN/KR: ".*(KakaoTalk|카카오톡).*")
        KW_ROOM_TITLE_RE    chat-room window title regex (default = the room name)
        KW_MORE_X_FROM_RIGHT / KW_MORE_Y_FROM_TOP
        KW_EXPORT_MENU_X / KW_EXPORT_MENU_Y
        KW_TEXT_ONLY_X / KW_TEXT_ONLY_Y
        KW_DIALOG_WAIT_SEC  seconds to wait for the save dialog (default 8)
        KW_FILE_WAIT_SEC    seconds to wait for the file to land (default 30)

🚨 HONESTY GUARD (source-fact §4):
  Codex sandbox could not launch Windows executables (`UtilBindVsockAnyPort`), so this
  file is syntax/unit verified but not scenario-replayed by this session. Do not claim
  live GREEN until step scripts produce screenshots + export path.
"""
from __future__ import annotations
import argparse, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # = providers/ (_credentials 위치)

KAKAO_CLASS = "EVA_Window"
KAKAO_TITLE = "카카오톡"
MEASURED_AT_KST = "2026-06-25"


def default_login_window_re() -> str:
    """Measured on Windows KakaoTalk 2026-06-25 KST: login title is also '카카오톡'."""
    return KAKAO_TITLE


def to_windows_path(path: Path | str) -> str:
    """Convert WSL /mnt/<drive>/... paths for Windows Python dialogs."""
    s = str(path)
    if s.startswith("/mnt/") and len(s) > 6 and s[6] == "/":
        drive = s[5].upper()
        rest = s[7:].replace("/", "\\")
        return f"{drive}:\\{rest}"
    return s.replace("/", "\\") if os.name == "nt" else s


def windows_data_root() -> Path:
    return Path(os.environ.get("KW_DATA_ROOT", str(Path.home() / ".kakao-wiki")))


def screenshot_path(name: str) -> Path:
    path = windows_data_root() / "screenshots" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_dir() -> Path:
    path = Path(os.environ.get("KW_EXPORT_DIR", str(windows_data_root() / "exports")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_kakao_hwnd() -> int:
    import ctypes

    user32 = ctypes.windll.user32
    return int(user32.FindWindowW(KAKAO_CLASS, KAKAO_TITLE))


def restore_kakao_window() -> int:
    """Restore tray-minimized KakaoTalk window and bring it forward."""
    import ctypes

    hwnd = find_kakao_hwnd()
    if not hwnd:
        raise RuntimeError(f'KakaoTalk window not found: class={KAKAO_CLASS!r}, title={KAKAO_TITLE!r}')
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE, measured path for tray-hidden KakaoTalk.
    time.sleep(0.3)
    try:
        user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    return hwnd


def kakao_app_from_hwnd(hwnd: int):
    from pywinauto import Application  # type: ignore

    return Application(backend="uia").connect(handle=hwnd, timeout=10)


def window_from_hwnd(hwnd: int):
    app = kakao_app_from_hwnd(hwnd)
    return app.window(handle=hwnd)


def capture_window(hwnd: int, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        win = window_from_hwnd(hwnd)
        win.capture_as_image().save(str(path))
        return
    except Exception:
        pass
    try:
        from PIL import ImageGrab  # type: ignore

        ImageGrab.grab().save(str(path))
        return
    except Exception as exc:
        raise RuntimeError(f"screenshot failed: {exc}") from exc

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
    login_re = os.environ.get("KW_LOGIN_WINDOW_RE", default_login_window_re())
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
    try:
        edits = dlg.descendants(control_type="Edit")
        if len(edits) >= 2:
            # 2026-06-25 KST 실측: login window is custom-draw, Edit[0]=ID combo, Edit[1]=PW.
            edits[1].click_input()
            edits[1].set_focus()
        else:
            send_keys("{TAB}")
    except Exception:
        send_keys("{TAB}")
    send_keys(creds.password.reveal(), with_spaces=True, vk_packet=True)  # PW: masked 입력, 로그 echo 0
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
    restore_kakao_window()
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


def _wait_for_new_txt(out_dir: Path, started_at: float, file_wait: int) -> Path:
    deadline = time.time() + file_wait
    while time.time() < deadline:
        candidates = sorted(
            (p for p in out_dir.glob("*.txt") if p.stat().st_mtime >= started_at and p.stat().st_size > 0),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
        time.sleep(0.5)
    raise RuntimeError(f"export file not found after {file_wait}s in {out_dir}")


def _click_room_more_menu(win) -> None:
    from pywinauto import mouse  # type: ignore

    rect = win.rectangle()
    x = rect.right - int(os.environ.get("KW_MORE_X_FROM_RIGHT", "34"))
    y = rect.top + int(os.environ.get("KW_MORE_Y_FROM_TOP", "46"))
    mouse.click(coords=(x, y))
    time.sleep(0.8)


def _click_menu_text_or_coord(app, win, text_re: str, x_env: str, y_env: str, default_x: int, default_y: int) -> None:
    from pywinauto import mouse  # type: ignore

    try:
        item = app.window(title_re=text_re)
        if item.exists(timeout=1):
            item.click_input()
            time.sleep(0.8)
            return
    except Exception:
        pass
    rect = win.rectangle()
    x = rect.left + int(os.environ.get(x_env, str(default_x)))
    y = rect.top + int(os.environ.get(y_env, str(default_y)))
    mouse.click(coords=(x, y))
    time.sleep(0.8)


def _save_dialog_to_dir(app, out_dir: Path, file_wait: int, started_at: float) -> Path:
    from pywinauto import Application          # type: ignore
    from pywinauto.keyboard import send_keys   # type: ignore

    del Application
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir_win = to_windows_path(out_dir)
    dlg_wait = int(os.environ.get("KW_DIALOG_WAIT_SEC", "8"))
    try:
        dlg = app.window(title_re=".*(저장|Save).*")
        dlg.wait("exists ready", timeout=dlg_wait)
        dlg.set_focus()
    except Exception:
        pass
    # Keep KakaoTalk's suggested filename, only move the save dialog to the export directory.
    send_keys("%d")
    time.sleep(0.2)
    send_keys(out_dir_win, with_spaces=True, vk_packet=True)
    send_keys("{ENTER}")
    time.sleep(0.8)
    send_keys("{ENTER}")
    return _wait_for_new_txt(out_dir, started_at, file_wait)


def _export_via_menu(room: str, out_dir: Path) -> Path:
    """Real export flow: room window ≡ → 대화 내보내기 → 텍스트만 저장."""
    from pywinauto import Application          # type: ignore

    kakao_re = os.environ.get("KW_KAKAO_TITLE_RE", ".*(KakaoTalk|카카오톡).*")  # EN+KR locale
    room_re  = os.environ.get("KW_ROOM_TITLE_RE", f".*{room}.*")
    file_wait = int(os.environ.get("KW_FILE_WAIT_SEC", "30"))

    out_dir.mkdir(parents=True, exist_ok=True)
    app = Application(backend="uia").connect(title_re=kakao_re, timeout=10)
    win = app.window(title_re=room_re)
    win.set_focus()
    time.sleep(0.5)
    started_at = time.time()
    _click_room_more_menu(win)
    _click_menu_text_or_coord(app, win, ".*대화.*내보내기.*", "KW_EXPORT_MENU_X", "KW_EXPORT_MENU_Y", 260, 180)
    _click_menu_text_or_coord(app, win, ".*텍스트.*저장.*", "KW_TEXT_ONLY_X", "KW_TEXT_ONLY_Y", 210, 240)
    target = _save_dialog_to_dir(app, out_dir, file_wait, started_at)

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
        path = _export_via_menu(a.room, Path(a.out))
    except Exception as e:  # noqa: BLE001 — surface the real failure to the spike operator
        print(f"\n❌ export failed: {type(e).__name__}: {e}")
        print("→ adjust KW_KAKAO_TITLE_RE / KW_ROOM_TITLE_RE / KW_SAVE_HOTKEY and retry (see spike doc).")
        return 4
    print(str(path))  # last stdout line = export path (collect.py contract)
    return 0


if __name__ == "__main__":
    sys.exit(main())
