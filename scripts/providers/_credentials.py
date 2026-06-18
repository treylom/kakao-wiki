#!/usr/bin/env python3
"""_credentials.py — kakao-wiki credential loading (ⓐ user-credential model).

재경님 결정(2026-06-19): 코드가 로그인하되 ID/PW 는 *사용자가 로컬에 설정*한다.
  - 공개 레포에 비밀번호 미저장.
  - 비밀번호는 KakaoTalk 입력창에만 들어가고, stdout/stderr/로그/Discord 어디에도 echo 하지 않는다.

자격증명 소스 (먼저 잡히는 것 우선):
  1. 환경변수  KW_KAKAO_ID / KW_KAKAO_PW
  2. ~/.kakao-wiki/credentials.env   (KEY=VALUE, 레포 밖 — 가장 안전)
  3. <repo>/.env                     (gitignored, 로컬 개발 편의)

Secret 래퍼가 repr/str 에서 비밀번호를 **** 로 가려, 실수로 print/log 해도 비밀번호가 새지 않는다.
이 레이어는 Windows UI 셀렉터와 무관(실측 의존 0) — provider spike 전에도 안전하게 완성된다.
"""
from __future__ import annotations
import os
from pathlib import Path

HOME_CRED = Path.home() / ".kakao-wiki" / "credentials.env"
REPO_ENV = Path(__file__).resolve().parents[2] / ".env"


class Secret:
    """repr/str/로그에 절대 값을 드러내지 않는 문자열 래퍼."""
    __slots__ = ("_v",)

    def __init__(self, v: str) -> None:
        self._v = v or ""

    def reveal(self) -> str:
        """실제 값 — KakaoTalk 입력에만 쓰고 절대 print/log 하지 말 것."""
        return self._v

    def __bool__(self) -> bool:
        return bool(self._v)

    def __repr__(self) -> str:
        return "Secret(****)"

    __str__ = __repr__


class Credentials:
    __slots__ = ("kakao_id", "password", "source")

    def __init__(self, kakao_id: str, password: Secret, source: str) -> None:
        self.kakao_id = kakao_id
        self.password = password
        self.source = source

    def is_complete(self) -> bool:
        return bool(self.kakao_id) and bool(self.password)

    def __repr__(self) -> str:
        return f"Credentials(kakao_id={self.kakao_id!r}, password=****, source={self.source!r})"


def _parse_env_file(path: Path) -> dict:
    out: dict = {}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_credentials() -> Credentials:
    """env → ~/.kakao-wiki/credentials.env → <repo>/.env 순으로 ID/PW 를 찾는다."""
    kid = os.environ.get("KW_KAKAO_ID", "").strip()
    kpw = os.environ.get("KW_KAKAO_PW", "")
    if kid and kpw:
        return Credentials(kid, Secret(kpw), "env")
    for path, label in ((HOME_CRED, "~/.kakao-wiki/credentials.env"), (REPO_ENV, "<repo>/.env")):
        if path.exists():
            kv = _parse_env_file(path)
            kid = kid or kv.get("KW_KAKAO_ID", "").strip()
            kpw = kpw or kv.get("KW_KAKAO_PW", "")
            if kid and kpw:
                return Credentials(kid, Secret(kpw), label)
    return Credentials(kid, Secret(kpw), "(incomplete)")


CRED_HELP = """\
KakaoTalk 자격증명을 찾지 못했습니다. 로컬에 설정하세요 (절대 커밋하지 마세요):

  방법 A — 환경변수:
      Windows cmd:   set KW_KAKAO_ID=your_id   &  set KW_KAKAO_PW=your_password
      PowerShell:    $env:KW_KAKAO_ID="your_id";  $env:KW_KAKAO_PW="your_password"

  방법 B — 레포 밖 로컬 파일  ~/.kakao-wiki/credentials.env :
      KW_KAKAO_ID=your_id
      KW_KAKAO_PW=your_password

비밀번호는 KakaoTalk 입력창에만 들어가며 화면/로그/커밋 어디에도 표시되지 않습니다.
"""
