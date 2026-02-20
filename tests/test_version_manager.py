import unittest
from unittest.mock import patch, mock_open
import datetime
import importlib.util
import os
import subprocess

# Dynamic import of version_manager
script_path = os.path.abspath(".github/scripts/version_manager.py")
spec = importlib.util.spec_from_file_location("version_manager", script_path)
vm = importlib.util.module_from_spec(spec)
# Patch subprocess.check_output BEFORE loading to avoid initial calls
with patch("subprocess.check_output") as mock_git:
    mock_git.return_value = b""
    spec.loader.exec_module(vm)


class TestVersionManager(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_get_current_version_git(self, mock_git):
        # Case with normal and beta tags
        mock_git.return_value = b"2026.2.0b0\n2026.2.0\n2026.1.2\n"
        version = vm.get_current_version()
        self.assertEqual(version, "2026.2.0b0")

    @patch("subprocess.check_output")
    def test_get_current_version_git_invalid_ignored(self, mock_git):
        # Invalid format tags should be ignored
        mock_git.return_value = b"v1.0.0\n2026.1.2\n"
        version = vm.get_current_version()
        self.assertEqual(version, "2026.1.2")

    @patch("subprocess.check_output")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"version": "2026.1.5"}')
    def test_get_current_version_fallback(self, mock_file, mock_exists, mock_git):
        mock_git.side_effect = subprocess.CalledProcessError(1, "git")
        mock_exists.side_effect = lambda p: p == vm.MANIFEST_FILE
        version = vm.get_current_version()
        self.assertEqual(version, "2026.1.5")

    @patch("subprocess.check_output")
    def test_stable_to_stable(self, mock_git):
        # 2026.2.0 -> bump stable -> 2026.2.1
        mock_git.return_value = b"2026.2.0\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("stable", now=now)
        self.assertEqual(new_v, "2026.2.1")

    @patch("subprocess.check_output")
    def test_stable_to_beta(self, mock_git):
        # 2026.2.0 -> bump beta -> 2026.2.1b0
        mock_git.return_value = b"2026.2.0\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("beta", now=now)
        self.assertEqual(new_v, "2026.2.1b0")

    @patch("subprocess.check_output")
    def test_beta_to_beta(self, mock_git):
        # 2026.2.1b0 -> bump beta -> 2026.2.1b1
        mock_git.return_value = b"2026.2.1b0\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("beta", now=now)
        self.assertEqual(new_v, "2026.2.1b1")

    @patch("subprocess.check_output")
    def test_beta_to_stable(self, mock_git):
        # 2026.2.1b1 -> bump stable -> 2026.2.1
        mock_git.return_value = b"2026.2.1b1\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("stable", now=now)
        self.assertEqual(new_v, "2026.2.1")

    @patch("subprocess.check_output")
    def test_stable_to_dev(self, mock_git):
        # 2026.2.1 -> bump dev -> 2026.2.2-dev0
        mock_git.return_value = b"2026.2.1\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("dev", now=now)
        self.assertEqual(new_v, "2026.2.2-dev0")

    @patch("subprocess.check_output")
    def test_dev_to_beta(self, mock_git):
        # 2026.2.2-dev0 -> bump beta -> 2026.2.2b0
        mock_git.return_value = b"2026.2.2-dev0\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("beta", now=now)
        self.assertEqual(new_v, "2026.2.2b0")

    @patch("subprocess.check_output")
    def test_rollover_new_month(self, mock_git):
        # 2026.1.2 -> bump stable in Feb -> 2026.2.0
        mock_git.return_value = b"2026.1.2\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("stable", now=now)
        self.assertEqual(new_v, "2026.2.0")

    @patch("subprocess.check_output")
    def test_rollover_new_month_beta(self, mock_git):
        # 2026.1.2 -> bump beta in Feb -> 2026.2.0b0
        mock_git.return_value = b"2026.1.2\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("beta", now=now)
        self.assertEqual(new_v, "2026.2.0b0")

if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
