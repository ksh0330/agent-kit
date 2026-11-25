"""End-to-end tests: real repositories, real `git commit` / `git push`, real hooks."""

import json
import unittest

from helpers import GOOD, OTHER, GitCase

AI_TRAILER = "Co-authored-by: Claude <bot@example.com>"


class CommitMsgHook(GitCase):
    def setUp(self):
        super().setUp()
        self.write_config(denied_emails=["*@blocked.example.com"], denied_names=["claude", "mallory"])
        self.install_guard()

    def test_allowed_author_with_clean_message_passes(self):
        proc = self.commit("feat: first change\n\nPlain body.")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.head_count(), 1)

    def test_generated_with_phrase_is_rejected(self):
        proc = self.commit("feat: thing\n\nGenerated with SomeTool")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("commit rejected", proc.stderr)
        self.assertIn("denied-pattern", proc.stderr)
        self.assertEqual(self.head_count(), 0)

    def test_tool_co_author_trailer_is_rejected(self):
        proc = self.commit(f"fix: bug\n\n{AI_TRAILER}")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("denied-user", proc.stderr)
        self.assertEqual(self.head_count(), 0)

    def test_session_marker_is_rejected(self):
        proc = self.commit("fix: bug\n\nClaude-Session: abc123")
        self.assertNotEqual(proc.returncode, 0)

    def test_denied_person_as_co_author_is_rejected(self):
        proc = self.commit("feat: pair work\n\nCo-authored-by: Bob Example <bob@blocked.example.com>")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("bob@blocked.example.com", proc.stderr)
        proc = self.commit("feat: pair work\n\nCo-authored-by: Mallory Example <m@example.com>")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("denied name 'mallory'", proc.stderr)

    def test_human_co_author_not_denied_passes(self):
        proc = self.commit(f"feat: pair work\n\nCo-authored-by: {OTHER[0]} <{OTHER[1]}>")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_author_outside_allow_list_is_rejected(self):
        proc = self.commit("feat: x", f"--author={OTHER[0]} <{OTHER[1]}>")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("author-not-allowed", proc.stderr)
        self.assertIn(OTHER[1], proc.stderr)

    def test_committer_outside_allow_list_is_rejected(self):
        proc = self.commit("feat: x", env={"GIT_COMMITTER_NAME": OTHER[0], "GIT_COMMITTER_EMAIL": OTHER[1]})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("committer", proc.stderr)

    def test_dash_c_identity_override_is_checked(self):
        proc = self.commit("feat: x")
        self.assertEqual(proc.returncode, 0)
        msg = self.tmp / "m2.txt"
        msg.write_text("feat: y", encoding="utf-8")
        (self.repo / "y.txt").write_text("y", encoding="utf-8")
        self.git("add", "y.txt")
        proc = self.git("-c", f"user.name={OTHER[0]}", "-c", f"user.email={OTHER[1]}", "commit", "-F", str(msg),
                        check=False)
        self.assertNotEqual(proc.returncode, 0)

    def test_broken_config_fails_closed(self):
        (self.repo / ".commit-guard.json").write_text("{not json", encoding="utf-8")
        proc = self.commit("feat: x")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("config error", proc.stderr)


class PrePushHook(GitCase):
    def setUp(self):
        super().setUp()
        self.write_config()
        self.remote = self.tmp / "remote.git"
        self.git("init", "-q", "--bare", str(self.remote), cwd=self.tmp)
        self.git("remote", "add", "origin", str(self.remote))

    def test_push_with_bad_commit_is_rejected_with_hash(self):
        self.commit("feat: ok one")
        self.commit(f"feat: sneaky\n\n{AI_TRAILER}", "--no-verify")
        bad = self.git("rev-parse", "HEAD").stdout.strip()
        self.install_guard()
        proc = self.git("push", "-q", "origin", "main", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("push rejected", proc.stderr)
        self.assertIn(bad[:12], proc.stderr)
        self.assertNotIn("feat: ok one", proc.stderr)
        self.assertEqual(self.git("branch", "--list", cwd=self.remote).stdout.strip(), "")

    def test_only_new_range_is_scanned(self):
        self.commit(f"feat: old\n\n{AI_TRAILER}", "--no-verify")
        self.git("push", "-q", "origin", "main")  # no guard yet: history already published
        self.install_guard()
        self.commit("feat: clean follow-up")
        proc = self.git("push", "-q", "origin", "main", check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_new_branch_push_checks_unpublished_commits(self):
        self.commit("feat: base")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "-b", "topic")
        self.commit("feat: topic", f"--author={OTHER[0]} <{OTHER[1]}>", "--no-verify")
        self.install_guard()
        proc = self.git("push", "-q", "origin", "topic", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("author-not-allowed", proc.stderr)
        self.assertEqual(proc.stderr.count("author-not-allowed"), 1)

    def test_scan_command_reports_range(self):
        self.commit("feat: a")
        base = self.git("rev-parse", "HEAD").stdout.strip()
        self.commit("feat: b\n\nGenerated with ToolX", "--no-verify")
        proc = self.kit("guard", "scan", f"{base}..HEAD")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("1 commit(s)", proc.stdout)
        self.assertIn("feat: b", proc.stdout)
        clean = self.kit("guard", "scan", base)
        self.assertEqual(clean.returncode, 0, clean.stdout)


class InstallUninstall(GitCase):
    def hooks(self):
        return self.repo / ".git" / "hooks"

    def test_install_creates_config_from_identity(self):
        proc = self.install_guard()
        self.assertIn("created .commit-guard.json", proc.stdout)
        data = json.loads((self.repo / ".commit-guard.json").read_text(encoding="utf-8"))
        self.assertEqual(data["allowed_authors"], [{"name": GOOD[0], "email": GOOD[1]}])

    def test_existing_hook_is_backed_up_and_chained(self):
        self.write_hook("commit-msg", 'echo "legacy ran" >> legacy.log\n')
        self.write_config()
        proc = self.install_guard()
        self.assertIn("backed up existing commit-msg", proc.stdout)
        self.assertTrue((self.hooks() / "commit-msg.agentkit-backup").exists())
        self.assertEqual(self.commit("feat: ok").returncode, 0)
        self.assertIn("legacy ran", (self.repo / "legacy.log").read_text(encoding="utf-8"))
        self.assertNotEqual(self.commit("feat: no\n\nGenerated with X").returncode, 0)

    def test_failing_original_hook_still_blocks(self):
        self.write_hook("commit-msg", 'echo "legacy says no" >&2\nexit 3\n')
        self.write_config()
        self.install_guard()
        proc = self.commit("feat: ok")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("legacy says no", proc.stderr)

    def test_original_pre_push_receives_stdin(self):
        remote = self.tmp / "r.git"
        self.git("init", "-q", "--bare", str(remote), cwd=self.tmp)
        self.git("remote", "add", "origin", str(remote))
        self.write_hook("pre-push", "cat > pushed-refs.log\n")
        self.write_config()
        self.install_guard()
        self.commit("feat: ok")
        self.git("push", "-q", "origin", "main")
        self.assertIn("refs/heads/main", (self.repo / "pushed-refs.log").read_text(encoding="utf-8"))

    def test_reinstall_is_idempotent(self):
        self.write_config()
        self.install_guard()
        proc = self.install_guard()
        self.assertIn("updated", proc.stdout)
        self.assertFalse((self.hooks() / "commit-msg.agentkit-backup").exists())

    def test_uninstall_restores_original_hook(self):
        original = self.write_hook("commit-msg", "exit 0\n").read_text(encoding="utf-8")
        self.write_config()
        self.install_guard()
        proc = self.kit("guard", "uninstall")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("restored original commit-msg", proc.stdout)
        self.assertEqual((self.hooks() / "commit-msg").read_text(encoding="utf-8"), original)
        self.assertFalse((self.hooks() / "pre-push").exists())
        self.assertFalse((self.hooks() / "commit-msg.agentkit-backup").exists())
        self.assertEqual(self.commit("feat: free\n\nGenerated with X").returncode, 0)

    def test_hooks_path_is_respected(self):
        self.git("config", "core.hooksPath", ".githooks")
        proc = self.kit("guard", "install")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("core.hooksPath", proc.stdout)
        self.assertFalse((self.hooks() / "commit-msg").exists())

    def test_check_reports_status_and_message(self):
        self.write_config()
        self.install_guard()
        msg = self.tmp / "candidate.txt"
        msg.write_text(f"fix: x\n\n{AI_TRAILER}\n", encoding="utf-8")
        proc = self.kit("guard", "check", "--message", str(msg))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("hook commit-msg: installed", proc.stdout)
        self.assertIn("denied-pattern", proc.stdout)

    def test_tool_json_blocks_bad_commit_command(self):
        self.write_config()
        payload = json.dumps({"tool_name": "Bash", "cwd": str(self.repo),
                              "tool_input": {"command": 'git commit -m "x" -m "Claude-Session: 1"'}})
        proc = self.kit("guard", "check", "--tool-json", stdin=payload)
        self.assertEqual(proc.returncode, 2)
        ok = json.dumps({"tool_name": "Bash", "cwd": str(self.repo), "tool_input": {"command": "git status"}})
        self.assertEqual(self.kit("guard", "check", "--tool-json", stdin=ok).returncode, 0)


if __name__ == "__main__":
    unittest.main()
