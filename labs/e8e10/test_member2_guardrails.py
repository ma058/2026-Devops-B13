"""Additional repair-parser boundaries; original 18 red tests remain unchanged.

These are explicit contract inputs bound to real Git commits, not claimed scan
outputs for Make syntax beyond the scanner's teaching profile.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from lab import commit, fixture, patch, run


class Member2RepairGuardrails(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="member2-guardrails-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        fixture(self.project, "macro")

    def set_makefile(self, text):
        (self.project / "Makefile").write_text(text)
        sha = commit(self.project, "member2: commit guardrail input")
        return {
            "commit": sha,
            "findings": [
                {"type": "MISSING", "target": "main.o", "dependency": "config.h"}
            ],
        }

    def candidate(self, report):
        before = (self.project / "Makefile").read_bytes()
        try:
            return patch(self.project, report)
        finally:
            self.assertEqual((self.project / "Makefile").read_bytes(), before)

    def reject(self, text, error):
        report = self.set_makefile(text)
        with self.assertRaisesRegex(ValueError, "^" + error + "$"):
            self.candidate(report)

    def test_insertion_precedes_inline_comment(self):
        original = (self.project / "Makefile").read_text().replace(
            "DEPS = main.c unused.h\n",
            "DEPS = main.c unused.h  # preserve this note\n",
        )
        report = self.set_makefile(original)
        diff, plan = self.candidate(report)
        self.assertEqual(plan, [
            {"target": "main.o", "dependency": "config.h", "style": "macro"}
        ])
        target = self.root / "apply-copy"
        shutil.copytree(self.project, target, ignore=shutil.ignore_patterns(".git"))
        patchfile = self.root / "candidate.patch"
        patchfile.write_text(diff)
        run(["git", "init", "-b", "main"], target)
        run(["git", "apply", "--check", str(patchfile.resolve())], target)
        run(["git", "apply", str(patchfile.resolve())], target)
        self.assertEqual((target / "Makefile").read_text(), original.replace(
            "DEPS = main.c unused.h  # preserve this note\n",
            "DEPS = main.c unused.h config.h  # preserve this note\n",
        ))

    def test_private_alias_existing_dependency_is_not_duplicated(self):
        text = (self.project / "Makefile").read_text()
        text = "BASE = main.c unused.h config.h\n" + text.replace(
            "DEPS = main.c unused.h\n", "DEPS = $(BASE)\n"
        )
        report = self.set_makefile(text)
        self.assertEqual(self.candidate(report), ("", []))

    def test_multiple_targets_on_edited_rule_are_rejected(self):
        text = (self.project / "Makefile").read_text().replace(
            "main.o: $(DEPS)\n", "main.o sibling.o: $(DEPS)\n"
        )
        self.reject(text, "UNSUPPORTED_RULE")

    def test_cycle_in_aliases_is_rejected(self):
        text = (self.project / "Makefile").read_text().replace(
            "DEPS = main.c unused.h\n", "DEPS = $(LOOP)\nLOOP = $(DEPS)\n"
        )
        self.reject(text, "UNSUPPORTED_DECLARATION")

    def test_undefined_alias_is_rejected(self):
        text = (self.project / "Makefile").read_text().replace(
            "DEPS = main.c unused.h\n", "DEPS = $(UNKNOWN)\n"
        )
        self.reject(text, "UNSUPPORTED_DECLARATION")

    def test_other_target_recipe_consumer_is_rejected(self):
        text = (self.project / "Makefile").read_text().replace(
            "\tgcc $(CFLAGS) -c helper.c -o helper.o\n",
            "\tgcc $(CFLAGS) -c helper.c -o helper.o\n\t@echo $(DEPS)\n",
        )
        self.reject(text, "UNSUPPORTED_SHARED_MACRO")

    def test_redefined_variable_is_rejected(self):
        text = "DEPS = main.c\n" + (self.project / "Makefile").read_text()
        self.reject(text, "UNSUPPORTED_MACRO")

    def test_conditional_definition_is_not_silently_interpreted(self):
        text = (self.project / "Makefile").read_text().replace(
            "DEPS = main.c unused.h\n",
            "ifeq (1,1)\nDEPS = main.c unused.h\nendif\n",
        )
        self.reject(text, "UNSUPPORTED_MAKEFILE")


if __name__ == "__main__":
    unittest.main()
