#!/usr/bin/env python3
"""windows_guide.py — Windows/WSL 환경 진단 + 사용 경로 자동 안내.

kakao-wiki 를 Windows(또는 WSL)에서 쓰려는 사용자를 위한 원샷 가이드:
  1) 환경 감지 (Windows 네이티브 / WSL / macOS)
  2) 지금 바로 되는 길(Ctrl+S 수동 내보내기 → manual provider) 단계 안내
  3) katok-windows(대화 검색 CLI) 설치 여부 감지 → 미설치면 설치 명령 안내
  4) 내보내기 파일 자동 탐색 결과 미리보기 (찾으면 다음 명령까지 출력)

읽기 전용 — 아무것도 설치·수정하지 않고 진단·안내만 출력한다.
Usage:  python3 scripts/windows_guide.py [--room "<방이름>"]
"""
from __future__ import annotations
import argparse, glob, os, platform, shutil, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from collect import _is_wsl, _manual_search_dirs  # noqa: E402


def detect_env() -> str:
    if platform.system() == "Windows":
        return "windows"
    if _is_wsl():
        return "wsl"
    if platform.system() == "Darwin":
        return "macos"
    return "linux"


def find_katok() -> str:
    """katok-windows 설치 흔적 탐지 — PATH, cargo 빌드 산출물, %APPDATA% 데이터 폴더."""
    exe = shutil.which("katok") or shutil.which("katok.exe")
    if exe:
        return exe
    home = Path.home()
    candidates = [home / "katok-windows" / "target" / "release" / "katok",
                  home / "katok-windows" / "target" / "release" / "katok.exe"]
    if _is_wsl():
        for u in glob.glob("/mnt/c/Users/*"):
            up = Path(u)
            candidates += [up / "katok-windows" / "target" / "release" / "katok.exe",
                           up / "AppData" / "Roaming" / "katok"]
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        candidates.append(Path(appdata) / "katok")
    for c in candidates:
        if c.exists():
            return str(c)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", default="", help="찾을 대화방 이름 (내보내기 파일 자동 탐색에 사용)")
    a = ap.parse_args()

    env = detect_env()
    env_label = {"windows": "Windows 네이티브", "wsl": "WSL(리눅스, Windows 파일 접근 가능)",
                 "macos": "macOS", "linux": "일반 Linux"}[env]
    print(f"◼ 환경: {env_label}")

    if env == "macos":
        print("→ macOS 는 자동 수집이 됩니다 (검증된 기본 경로):")
        print('    python3 scripts/collect.py --room "<방이름>" --provider macos --out ./out')
        return 0

    # ── 1) 수집: 지금 바로 되는 길 = 공식 내보내기(Ctrl+S) + manual provider ──
    print("""
◼ 수집 — 지금 바로 되는 길 (공식 내보내기 + manual provider)
  Windows 카카오톡의 자동 내보내기(windows provider)는 아직 검증 대기(spike-pending)입니다.
  대신 카카오톡 공식 기능으로 파일을 만들고, 그 파일을 이 스킬이 이어받습니다:

  1) Windows 카카오톡(PC버전)에서 대상 대화방을 엽니다.
  2) 대화창에서 Ctrl+S (또는 메뉴 ≡ → 대화 내용 → 대화 내보내기) → .txt 저장.
  3) 권장 저장 위치 = C:\\Users\\<이름>\\.kakao-wiki\\exports  (한 번 만들어 두면 자동 탐색됨)
  4) 처리 실행:""")
    where = "WSL 쪽에서" if env == "wsl" else "같은 PC의 Python 에서"
    print(f"     # {where}:")
    print('     python3 scripts/collect.py --room "<방이름>" --provider manual --out ./out')
    if env == "wsl":
        print("     (경로 직접 지정 시: C:\\Users\\<이름>\\... = /mnt/c/Users/<이름>/... — --input 은 둘 다 인식)")
    print('     python3 scripts/store_to_wiki.py --normalized out/<방>-<날짜>.normalized.json \\')
    print('       --vault "<옵시디언 vault 절대경로>" --subdir "Research/<방이름>"')

    # 자동 탐색 미리보기
    dirs = _manual_search_dirs()
    found = []
    room_n = unicodedata.normalize("NFC", a.room) if a.room else ""
    for d in dirs:
        for p in list(d.glob("*.txt")):
            name = unicodedata.normalize("NFC", p.name)
            if (room_n and room_n in name) or ("KakaoTalk" in name) or ("카카오톡" in name):
                found.append(p)
    if found:
        found.sort(key=lambda p: -p.stat().st_mtime)
        print(f"\n  ✅ 내보내기 파일 후보 {len(found)}건 발견 — 최신: {found[0]}")
        print("     위 collect 명령을 그대로 실행하면 이 파일이 자동 채택됩니다.")
    else:
        print(f"\n  (아직 내보내기 파일을 못 찾았습니다 — 탐색 위치: {', '.join(str(d) for d in dirs[:4])} …)")

    # ── 2) 검색: katok-windows 연계 ──
    katok = find_katok()
    print("\n◼ 대화 검색 — katok-windows (선택, 권장)")
    if katok:
        print(f"  ✅ 설치 확인: {katok}")
        print('  사용:  katok sync --source txt "<내보낸.txt>"   →   katok search bm25 "<질의>"')
    else:
        print("  ❌ 설치 안 됨 — 내보낸 txt 를 색인해 keyword/BM25/semantic 검색을 해주는 CLI 입니다.")
        print("  설치 (Rust 필요 — https://rustup.rs 에서 rustup 먼저):")
        print("     git clone https://github.com/Hostingglobal-Tech/katok-windows.git")
        print("     cd katok-windows && cargo build --release")
        print("     → 실행 파일: target/release/katok(.exe)")
        if env == "wsl":
            print("  (WSL 팁: 검색 대상 txt 가 Windows 쪽에 있으면 Windows 에서 빌드·실행하는 쪽이 간단합니다.)")

    print("\n◼ 요약: 공식 내보내기(Ctrl+S) → kakao-wiki(위키 적재) + katok-windows(검색) 이 Windows 의 현재 정답 조합입니다.")
    print("  자동 수집(windows provider)은 실기 검증 1회가 남아 있습니다 — references/windows-provider-spike.md 참고.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
