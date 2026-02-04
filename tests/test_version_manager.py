import unittest
from unittest.mock import patch, mock_open
import datetime
import importlib.util
import os

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
        mock_git.return_value = b"2026.1.2\n2026.1.1\n2025.12.5\n"
        version = vm.get_current_version()
        self.assertEqual(version, "2026.1.2")

    @patch("subprocess.check_output")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"version": "2026.1.5"}')
    def test_get_current_version_fallback(self, mock_file, mock_exists, mock_git):
        import subprocess

        mock_git.side_effect = subprocess.CalledProcessError(1, "git")
        mock_exists.side_effect = lambda p: p == vm.MANIFEST_FILE
        version = vm.get_current_version()
        self.assertEqual(version, "2026.1.5")

    @patch("subprocess.check_output")
    def test_rollover_new_month_stable(self, mock_git):
        # Current release 2026.1.2, it's now Feb 2026
        mock_git.return_value = b"2026.1.2\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("stable", now=now)
        # Should be 2026.2.0 (new cycle, patch starts at 0, no extra increment)
        self.assertEqual(new_v, "2026.2.0")

    @patch("subprocess.check_output")
    def test_rollover_new_month_beta(self, mock_git):
        # Current release 2026.1.2, it's now Feb 2026, user wants beta
        mock_git.return_value = b"2026.1.2\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("beta", now=now)
        # Should be 2026.2.0b0
        self.assertEqual(new_v, "2026.2.0b0")

    @patch("subprocess.check_output")
    def test_increment_same_month_beta(self, mock_git):
        # Current version is 2026.2.0b0, user wants next beta in same month
        mock_git.return_value = b"2026.2.0b0\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("beta", now=now)
        self.assertEqual(new_v, "2026.2.0b1")

    @patch("subprocess.check_output")
    def test_increment_same_month_stable_after_beta(self, mock_git):
        # Current version is 2026.2.0b1, user wants stable in same month
        mock_git.return_value = b"2026.2.0b1\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("stable", now=now)
        # Should be 2026.2.0 (suffix removed)
        self.assertEqual(new_v, "2026.2.0")

    @patch("subprocess.check_output")
    def test_increment_same_month_stable_after_stable(self, mock_git):
        # Current version is 2026.2.0, user wants stable in same month
        mock_git.return_value = b"2026.2.0\n"
        now = datetime.datetime(2026, 2, 4)
        new_v = vm.calculate_version("stable", now=now)
        # Should be 2026.2.1
        self.assertEqual(new_v, "2026.2.1")


if __name__ == "__main__":
    unittest.main()
