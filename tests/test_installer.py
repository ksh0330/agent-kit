"""Installer: preview by default, --apply writes, never overwrites."""

import unittest

from helpers import GitCase


class KitInstaller(GitCase):
    def test_preview_writes_nothing_and_apply_never_overwrites(self):
        preview = self.kit("install", "--target", str(self.repo))
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("PREVIEW", preview.stdout)
        self.assertFalse((self.repo / ".claude").exists())
        self.assertFalse((self.repo / ".git" / "hooks" / "commit-msg").exists())
        board = self.repo / "agent" / "BOARD.md"
        board.parent.mkdir()
        board.write_text("mine", encoding="utf-8")
        applied = self.kit("install", "--target", str(self.repo), "--apply")
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual(board.read_text(encoding="utf-8"), "mine")
        self.assertTrue((self.repo / ".claude" / "skills" / "plan" / "SKILL.md").exists())
        self.assertTrue((self.repo / "agent" / "LEARNING.md").exists())
        self.assertTrue((self.repo / ".git" / "hooks" / "commit-msg").exists())


if __name__ == "__main__":
    unittest.main()
