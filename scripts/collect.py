#!/usr/bin/env python3
"""collect.py — kakao-wiki provider-abstracted collection.

collect(room, provider) -> raw export -> normalized.json

Providers:
  macos   GREEN        — providers/macos_osascript.sh (GUI export -> CSV)
  windows SPIKE-PENDING — providers/windows_pywinauto.py (Ctrl+S local txt; experimental)
  db      EXPERIMENTAL — providers/db_kakaocli.sh (kakaocli DB read -> CSV)

Usage:
  collect.py --room "<ROOM>" --provider macos --out ./out [--since "YYYY-MM-DD HH:MM:SS"]
"""
from __future__ import annotations
import argparse, glob, platform, shutil, subprocess, sys, unicodedata
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
PROV = HERE / "providers"

PROVIDER_STATUS = {
    "macos": "GREEN",
    "manual": "GREEN",            # user-exported txt/csv → normalize (no GUI automation)
    "windows": "SPIKE-PENDING",   # not verified on real Windows KakaoTalk
    "db": "EXPERIMENTAL",
}

# manual provider 기본 탐색 경로 — 우리 컨벤션(~/.kakao-wiki/exports) 우선, 그다음 일반 저장 위치.
# WSL 에서는 Windows 사용자 폴더(/mnt/c/Users/*)까지 자동 포함.
def _is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False


def _manual_search_dirs() -> list[Path]:
    home = Path.home()
    dirs = [home / ".kakao-wiki" / "exports",
            home / "Documents", home / "Downloads", home / "Desktop"]
    if _is_wsl():
        for u in glob.glob("/mnt/c/Users/*"):
            up = Path(u)
            if up.name in ("Public", "Default", "Default User", "All Users"):
                continue
            dirs += [up / ".kakao-wiki" / "exports",
                     up / "Documents", up / "Downloads", up / "Desktop"]
    return [d for d in dirs if d.is_dir()]


CTRL_S_GUIDE = """\
[manual provider] 내보낸 대화 파일을 찾지 못했습니다. 이렇게 만들어 주세요:

  1) Windows 카카오톡(PC버전)에서 대상 대화방을 엽니다.
  2) 대화창에서 Ctrl+S (또는 메뉴 ≡ → 대화 내용 → 대화 내보내기)를 누릅니다.
  3) 저장 위치는 아무 곳이나 되지만, 권장 = 내 문서 또는 C:\\Users\\<이름>\\.kakao-wiki\\exports
     (이 폴더에 저장하면 다음부터 --input 없이 자동으로 찾습니다.)
  4) 저장한 .txt 경로를 --input 으로 넘겨 다시 실행합니다:
       python3 scripts/collect.py --room "<방이름>" --provider manual --input <저장한.txt> --out ./out
     WSL 에서는 C:\\Users\\<이름>\\... 경로가 /mnt/c/Users/<이름>/... 입니다.

  환경 진단·katok-windows 연계 안내는:  python3 scripts/windows_guide.py
"""


def _win_to_wsl_path(raw: str) -> Path:
    """C:\\Users\\x\\file.txt → /mnt/c/Users/x/file.txt (WSL 편의 변환)."""
    if len(raw) >= 3 and raw[1:3] in (":\\", ":/"):
        drive = raw[0].lower()
        rest = raw[3:].replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return Path(raw)


def run_manual(room: str, out_dir: Path, input_path: str = "") -> Path:
    """이미 내보낸 txt/csv(사용자 수동 Ctrl+S 저장분)를 받아 파이프라인에 연결한다."""
    if input_path:
        src = _win_to_wsl_path(input_path).expanduser()
        if not src.exists():
            raise SystemExit(f"manual provider: --input 파일이 없습니다: {src}")
    else:
        room_n = unicodedata.normalize("NFC", room)
        cands: list[Path] = []
        for d in _manual_search_dirs():
            for p in list(d.glob("*.txt")) + list(d.glob("*.csv")):
                name = unicodedata.normalize("NFC", p.name)
                if (room_n in name) or ("KakaoTalk" in name) or ("카카오톡" in name) or ("Talk_" in name):
                    cands.append(p)
        if not cands:
            sys.stderr.write(CTRL_S_GUIDE)
            raise SystemExit(4)
        # 방이름 매칭 우선, 그 안에서 최신 mtime
        cands.sort(key=lambda p: (unicodedata.normalize("NFC", p.name).find(room_n) < 0,
                                  -p.stat().st_mtime))
        src = cands[0]
        sys.stderr.write(f"[manual] 자동 채택: {src}  (후보 {len(cands)}건 중 최신·방이름 우선)\n")
    # 방 검증: 파일명/앞부분(헤더)에 방이름 NFC substring 확인.
    #  - 자동 탐색 채택분 = fail-fast (엉뚱한 방 오수집 방지 — macos provider CSV 방검증과 동형)
    #  - --input 명시분 = 경고만 (사용자가 고른 파일 존중)
    head = ""
    try:
        head = src.read_text(encoding="utf-8", errors="replace")[:400]
    except OSError:
        pass
    if unicodedata.normalize("NFC", room) not in unicodedata.normalize("NFC", src.name + head):
        if input_path:
            sys.stderr.write(f"[manual] ⚠️ 파일에서 방이름 '{room}' 을 확인하지 못했습니다 — 파일이 맞는지 확인하세요: {src}\n")
        else:
            sys.stderr.write(f"[manual] ❌ 자동 채택 파일에서 방이름 '{room}' 을 확인하지 못했습니다: {src}\n"
                             f"  엉뚱한 방을 수집하지 않도록 중단합니다. 맞는 파일이면 --input 으로 직접 지정하세요:\n"
                             f"    python3 scripts/collect.py --room \"{room}\" --provider manual --input \"{src}\"\n")
            raise SystemExit(4)
    dst = out_dir / f"{room}-{datetime.now().strftime('%Y-%m-%d')}.raw{src.suffix.lower()}"
    shutil.copyfile(src, dst)
    return dst


def run_macos(room: str, out_dir: Path) -> Path:
    r = subprocess.run(["bash", str(PROV / "macos_osascript.sh"), room, str(out_dir)],
                       capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"macos provider failed (exit {r.returncode})")
    csv_path = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if not csv_path or not Path(csv_path).exists():
        raise SystemExit("macos provider produced no CSV")
    return Path(csv_path)


def run_windows(room: str, out_dir: Path) -> Path:
    # scaffold — windows_pywinauto.py 가 spike 전엔 명시적으로 'unverified' 표기하고 비-0 exit.
    r = subprocess.run([sys.executable, str(PROV / "windows_pywinauto.py"),
                        "--room", room, "--out", str(out_dir)],
                       capture_output=True, text=True)
    sys.stderr.write(r.stdout + r.stderr)
    raise SystemExit(
        "windows provider = SPIKE-PENDING (experimental scaffold). "
        "실제 KakaoTalk Windows spike 로 셀렉터/키 검증 전엔 수집 결과를 신뢰하지 말 것 "
        "(references/windows-provider-spike.md). 검증 완료 후 이 가드를 해제하라.\n"
        "👉 지금 바로 되는 길: 카카오톡에서 Ctrl+S 로 대화를 저장한 뒤\n"
        "   python3 scripts/collect.py --room \"<방>\" --provider manual [--input <저장한.txt>]\n"
        "   (환경 진단 = python3 scripts/windows_guide.py)")


def run_db(room: str, out_dir: Path) -> Path:
    r = subprocess.run(["bash", str(PROV / "db_kakaocli.sh"), room, str(out_dir)],
                       capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"db provider failed/unavailable (exit {r.returncode}) — experimental")
    csv_path = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if not csv_path or not Path(csv_path).exists():
        raise SystemExit("db provider produced no CSV")
    return Path(csv_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", required=True)
    ap.add_argument("--provider", choices=list(PROVIDER_STATUS),
                    default=("manual" if platform.system() != "Darwin" else "macos"))
    ap.add_argument("--input", default="",
                    help="manual provider: 이미 내보낸 txt/csv 경로 (미지정 시 기본 저장 경로 자동 탐색)")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--since", default="")
    a = ap.parse_args()

    out_dir = Path(a.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    status = PROVIDER_STATUS[a.provider]
    sys.stderr.write(f"[collect] provider={a.provider} status={status} room={a.room}\n")

    if a.provider == "manual":
        raw = run_manual(a.room, out_dir, a.input)
    else:
        raw = {"macos": run_macos, "windows": run_windows, "db": run_db}[a.provider](a.room, out_dir)

    date = datetime.now().strftime("%Y-%m-%d")
    norm_out = out_dir / f"{a.room}-{date}.normalized.json"
    cmd = [sys.executable, str(HERE / "normalize.py"), "--raw", str(raw), "--out", str(norm_out)]
    if a.since:
        cmd += ["--since", a.since]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("normalize failed")
    print(str(norm_out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
