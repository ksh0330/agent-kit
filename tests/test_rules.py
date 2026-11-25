import unittest

from agentkit.guard import config, rules
from agentkit.guard.runner import precheck_command

CFG = config.validate({"allowed_authors": [{"name": "Alice Example", "email": "alice@example.com"}],
                       "denied_emails": ["*@blocked.example.com"]})


class MessageRules(unittest.TestCase):
    def test_clean_message_passes(self):
        self.assertEqual(rules.check_message("feat: add parser\n\nHandles empty input.", CFG), [])

    def test_tool_co_author_trailer_is_denied(self):
        found = rules.check_message("fix: typo\n\nCo-authored-by: Claude <bot@example.com>", CFG)
        self.assertIn("denied-pattern", {v.rule for v in found})
        self.assertIn("denied-user", {v.rule for v in found})

    def test_generated_with_line_is_denied_case_insensitively(self):
        found = rules.check_message("chore: bump\n\nGENERATED WITH some tool", CFG)
        self.assertEqual([v.rule for v in found], ["denied-pattern"])

    def test_comments_and_scissors_are_ignored(self):
        raw = ("docs: note\n# Co-authored-by: Claude <bot@example.com>\n"
               "# ------------------------ >8 ------------------------\nGenerated with diff below\n")
        self.assertEqual(rules.check_message(rules.clean_message(raw), CFG), [])

    def test_denied_name_needs_whole_word(self):
        self.assertEqual(rules.denied_reasons("Claudette Example", "c@example.com", CFG), [])
        self.assertTrue(rules.denied_reasons("claude[bot]", "c@example.com", CFG))


class IdentityRules(unittest.TestCase):
    def test_allowed_author_matches_name_and_email(self):
        self.assertEqual(rules.check_identity("author", "Alice Example", "ALICE@example.com", CFG), [])

    def test_wrong_name_for_allowed_email_is_rejected(self):
        found = rules.check_identity("author", "Mallory", "alice@example.com", CFG)
        self.assertEqual([v.rule for v in found], ["author-not-allowed"])

    def test_empty_allow_list_only_applies_denials(self):
        cfg = config.validate({})
        self.assertEqual(rules.check_identity("author", "Bob Example", "bob@example.com", cfg), [])


class ConfigLoading(unittest.TestCase):
    def test_defaults_are_used_for_missing_keys(self):
        self.assertEqual(CFG["denied_names"], config.DEFAULT_CONFIG["denied_names"])
        self.assertEqual(CFG["denied_emails"], ["*@blocked.example.com"])

    def test_invalid_config_is_reported(self):
        for bad in ([], {"allowed_authors": [{"name": "x"}]}, {"denied_trailer_patterns": ["("]}, {"typo": 1}):
            with self.assertRaises(config.ConfigError):
                config.validate(bad)


class CommandPrecheck(unittest.TestCase):
    def test_inline_message_and_identity_flags(self):
        cmd = ('git -c user.name="Alice Example" -c user.email=alice@example.com commit -m "feat: x" '
               '-m "Generated with a tool"')
        self.assertEqual([v.rule for v in precheck_command(cmd, CFG)], ["denied-pattern"])

    def test_no_verify_and_chained_commands(self):
        cmd = 'git add . && git -c user.name="Alice Example" -c user.email=alice@example.com commit --no-verify -m ok'
        self.assertEqual([v.rule for v in precheck_command(cmd, CFG)], ["no-verify"])

    def test_non_commit_command_is_ignored(self):
        self.assertEqual(precheck_command("git status && ls", CFG), [])


if __name__ == "__main__":
    unittest.main()
