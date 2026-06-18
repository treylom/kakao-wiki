#!/usr/bin/env python3
"""windows_pywinauto.py — kakao-wiki Windows provider (⚠️ SPIKE-PENDING / EXPERIMENTAL).

현실성 등급(연구 §2.2): 🟢 Ctrl+S 로컬 txt 저장 = Windows 카톡 최우선 경로
(Mac 다단 메뉴보다 단순). 본 스캐폴드는 그 경로를 pywinauto(UIA)로 코드화한다.

🚨 HONESTY GUARD (source-fact §4):
  - 본 코드는 **실제 KakaoTalk Windows 에서 검증되지 않았다**. UI 요소 셀렉터·키 동작·
    저장 다이얼로그 흐름은 Mac 과 달라 **반드시 spike 로 재유도**해야 한다.
  - 따라서 기본 동작은 **검증 안내 + 비-0 exit** (성공을 가장하지 않음).
  - spike 로 셀렉터를 확정한 뒤 `--i-have-verified-on-real-windows` 플래그로만 실행 허용.
  - 체크리스트: references/windows-provider-spike.md

대안: pywinauto 대신 AutoHotkey(빠른 UIA 클릭) 또는 PowerShell UIAutomation 도 가능
(연구 §2.1). Ctrl+S 키 입력만으로 로컬 txt 가 떨어지면 도구 무관 단순.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

SPIKE_CHECKLIST = """\
[Windows spike 체크리스트 — 검증 전 'completed' 금지]
 1. KakaoTalk Windows 설치·로그인 상태.
 2. 대상 방을 더블클릭으로 *대화창* 오픈(검색-리스트 상태 ❌).
 3. 대화창 포커스 후 Ctrl+S → '내 컴퓨터에 txt 저장' 다이얼로그가 뜨는지 확인.
 4. 저장 경로/파일명 패턴 확정(예: KakaoTalk_<방>_<ts>.txt) → normalize.py txt 파서와 정합 확인.
 5. pywinauto backend='uia' 로 대화창 윈도우 타이틀/컨트롤 식별자 재유도(Mac 셀렉터 무효).
 6. UIA 노출이 약한 컨트롤은 send_keys('^s') 키 입력 + 다이얼로그 Enter 로 폴백.
 7. 위 전부 1회 실 export 성공 후에만 HONESTY GUARD 해제.
"""

# --- 검증 후 활성화할 실제 흐름 (현재 비활성 — 참조용 스캐폴드) ---
def _export_via_ctrl_s(room: str, out_dir: Path) -> Path:  # pragma: no cover (spike-pending)
    from pywinauto import Application  # type: ignore
    # NOTE: 아래 타이틀/셀렉터는 *추정값* — spike 에서 실측 교체 필요.
    app = Application(backend="uia").connect(title_re=".*KakaoTalk.*")
    win = app.window(title_re=f".*{room}.*")
    win.set_focus()
    win.type_keys("^s")            # Ctrl+S → 로컬 txt 저장
    # 저장 다이얼로그: 경로 입력/Enter (spike 에서 다이얼로그 구조 확정)
    from pywinauto.keyboard import send_keys
    send_keys("{ENTER}")
    # TODO(spike): 저장 완료 폴링 + 파일 경로 회수 + 방 검증(파일명 substring)
    raise NotImplementedError("spike 에서 저장경로 회수·검증 로직 확정 후 구현")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--i-have-verified-on-real-windows", action="store_true",
                    help="spike 로 셀렉터/키를 실검증한 경우에만 사용")
    a = ap.parse_args()

    print("=== kakao-wiki Windows provider (SPIKE-PENDING) ===")
    print(SPIKE_CHECKLIST)
    if not a.__dict__["i_have_verified_on_real_windows"]:
        print("\n⚠️ 미검증 — 수집 미수행(성공 가장 ❌). spike 완료 후 --i-have-verified-on-real-windows 로 재실행.")
        return 4  # collect.py 가 이 비-0 을 보고 SPIKE-PENDING 가드 발동
    # 검증 플래그가 있어도, 실제 구현은 spike 산출 셀렉터로 _export_via_ctrl_s 를 완성한 뒤 활성화.
    try:
        path = _export_via_ctrl_s(a.room, Path(a.out))
    except NotImplementedError as e:
        print(f"\n⚠️ 구현 미완(spike 산출 필요): {e}")
        return 4
    print(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
