import tempfile
import unittest
from pathlib import Path

from scripts.normalize import normalize


class WindowsTxtNormalizeTests(unittest.TestCase):
    def test_parses_kakaotalk_windows_timestamp_sender_and_message(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "self.raw.txt"
            raw.write_text(
                "저장한 날짜 : 2026. 6. 25. 오후 7:00\n"
                "2026. 6. 25. 오후 7:01, 나 : 첫 줄\n"
                "2026. 6. 25. 오후 7:02, 나 : 둘째 줄: 콜론 포함\n",
                encoding="utf-8",
            )

            result = normalize(raw, None)

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["first_time"], "2026-06-25 19:01:00")
        self.assertEqual(result["last_time"], "2026-06-25 19:02:00")
        self.assertEqual(result["messages"][0], {"time": "2026-06-25 19:01:00", "user": "나", "msg": "첫 줄"})
        self.assertEqual(result["messages"][1]["msg"], "둘째 줄: 콜론 포함")


if __name__ == "__main__":
    unittest.main()
