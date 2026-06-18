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
import argparse, subprocess, sys
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
PROV = HERE / "providers"

PROVIDER_STATUS = {
    "macos": "GREEN",
    "windows": "SPIKE-PENDING",   # not verified on real Windows KakaoTalk
    "db": "EXPERIMENTAL",
}


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
        "(references/windows-provider-spike.md). 검증 완료 후 이 가드를 해제하라.")


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
    ap.add_argument("--provider", choices=list(PROVIDER_STATUS), default="macos")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--since", default="")
    a = ap.parse_args()

    out_dir = Path(a.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    status = PROVIDER_STATUS[a.provider]
    sys.stderr.write(f"[collect] provider={a.provider} status={status} room={a.room}\n")

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
