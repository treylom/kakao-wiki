import os
import sys
import unittest
from pathlib import Path

PROVIDERS = Path(__file__).resolve().parents[1] / "scripts" / "providers"
sys.path.insert(0, str(PROVIDERS))

import windows_pywinauto as provider  # noqa: E402
from _credentials import Secret  # noqa: E402


class WindowsProviderContractTests(unittest.TestCase):
    def test_real_kakao_title_is_default_login_window_pattern(self):
        self.assertEqual(provider.default_login_window_re(), "카카오톡")

    def test_wsl_c_path_converts_to_windows_c_path(self):
        self.assertEqual(
            provider.to_windows_path(Path("/mnt/c/Users/alice/.kakao-wiki/exports")),
            r"C:\Users\alice\.kakao-wiki\exports",
        )

    def test_secret_does_not_render_password(self):
        secret = Secret("do-not-print-this")

        self.assertNotIn("do-not-print-this", str(secret))
        self.assertNotIn("do-not-print-this", repr(secret))


if __name__ == "__main__":
    unittest.main()
