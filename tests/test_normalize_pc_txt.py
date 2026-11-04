#!/usr/bin/env python3
"""PC(Ctrl+S) txt export 파서 테스트 — [이름] [오전/오후 H:MM] + 날짜 구분선 + 멀티라인."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
NORMALIZE = HERE / "scripts" / "normalize.py"

FIXTURE = """테스트방 님과 카카오톡 대화
저장한 날짜 : 2026-07-29 07:30:00

--------------- 2026년 7월 28일 월요일 ---------------
[홍길동] [오후 2:30] 첫 메시지입니다
[이영희] [오전 11:05] 답장이요
여러 줄
메시지 계속
[홍길동] [오후 12:10] 정오 케이스
--------------- 2026년 7월 29일 화요일 ---------------
[이영희] [오전 12:01] 자정 케이스
"""


class TestNormalizePcTxt(unittest.TestCase):
    def _run(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "export.txt"
            out = Path(td) / "norm.json"
            raw.write_text(text, encoding="utf-8")
            r = subprocess.run([sys.executable, str(NORMALIZE), "--raw", str(raw), "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(out.read_text(encoding="utf-8"))

    def test_pc_format_full(self):
        d = self._run(FIXTURE)
        self.assertEqual(d["count"], 4)
        msgs = d["messages"]
        # 날짜 구분선 → 날짜 공급 + 오전/오후 변환
        self.assertEqual(msgs[0]["time"], "2026-07-28 14:30:00")
        self.assertEqual(msgs[0]["user"], "홍길동")
        # 멀티라인 병합
        self.assertEqual(msgs[1]["msg"], "답장이요\n여러 줄\n메시지 계속")
        # 정오(오후 12시) = 12시 유지
        self.assertEqual(msgs[2]["time"], "2026-07-28 12:10:00")
        # 날짜 전환 + 자정(오전 12시) = 00시
        self.assertEqual(msgs[3]["time"], "2026-07-29 00:01:00")

    def test_header_lines_skipped(self):
        d = self._run(FIXTURE)
        for m in d["messages"]:
            self.assertNotIn("카카오톡 대화", m["msg"])
            self.assertNotIn("저장한 날짜", m["msg"])

    def test_windows_format_no_regression(self):
        d = self._run("2026. 6. 18. 오후 8:19, 홍길동 : 기존 포맷 메시지\n")
        self.assertEqual(d["count"], 1)
        self.assertEqual(d["messages"][0]["time"], "2026-06-18 20:19:00")


if __name__ == "__main__":
    unittest.main()
