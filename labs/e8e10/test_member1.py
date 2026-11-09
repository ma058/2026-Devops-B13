"""Member 1 independent B-track checks for the E8-E10 teaching profile.

These are additional tests, not the seven distributed reference tests. E8/E9
reports are deliberately constructed inputs with explicit expectations. E10
runs the actual GCC/Make validation path on Linux; no fake success is used.
"""

import difflib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from lab import fixture, patch, run, validate


class Member1RepairContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="b13-member1-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        fixture(self.project)

    def report(self, findings, project=None):
        project = project or self.project
        return {
            "commit": run(["git", "rev-parse", "HEAD"], project).strip(),
            "findings": findings,
        }

    @staticmethod
    def missing(target, dependency):
        return {"type": "MISSING", "target": target, "dependency": dependency}

    @staticmethod
    def snapshot(project):
        return {p.name: p.read_bytes() for p in project.iterdir() if p.is_file()}

    def apply_to_copy(self, project, diff, label):
        """Observe a real applied patch without changing its source fixture."""
        copy = self.root / (label + "-applied")
        shutil.copytree(project, copy, ignore=shutil.ignore_patterns(".git"))
        candidate = self.root / (label + ".patch")
        candidate.write_text(diff, encoding="utf-8")
        run(["git", "init", "-b", "main"], copy)
        run(["git", "apply", "--check", str(candidate)], copy)
        run(["git", "apply", str(candidate)], copy)
        return (copy / "Makefile").read_text()

    def test_e8_redundant_only_is_noop_for_all_source_files(self):
        before = self.snapshot(self.project)
        report = self.report([
            {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"}
        ])
        diff, plan = patch(self.project, report)
        self.assertEqual(diff, "")
        self.assertEqual(plan, [])
        self.assertEqual(self.snapshot(self.project), before)
        self.assertIn("main.o: main.c unused.h", (self.project / "Makefile").read_text())

    def test_e8_unknown_target_is_rejected_without_source_changes(self):
        before = self.snapshot(self.project)
        with self.assertRaisesRegex(ValueError, "^UNSUPPORTED_TARGET$"):
            patch(self.project, self.report([self.missing("unknown.o", "config.h")]))
        self.assertEqual(self.snapshot(self.project), before)

    def test_e8_later_invalid_finding_cannot_partially_write_first_edit(self):
        before = self.snapshot(self.project)
        report = self.report([
            self.missing("main.o", "config.h"),
            self.missing("unknown.o", "extra.h"),
        ])
        with self.assertRaisesRegex(ValueError, "^UNSUPPORTED_TARGET$"):
            patch(self.project, report)
        self.assertEqual(self.snapshot(self.project), before)

    def test_e9_distinct_missing_entries_keep_order_and_recipes(self):
        before = self.snapshot(self.project)
        report = self.report([
            self.missing("main.o", "extra.h"),
            self.missing("main.o", "config.h"),
        ])
        diff, plan = patch(self.project, report)
        applied = self.apply_to_copy(self.project, diff, "direct")
        self.assertIn("main.o: main.c unused.h extra.h config.h\n", applied)
        self.assertEqual(plan, [
            {"target": "main.o", "dependency": "extra.h", "style": "direct"},
            {"target": "main.o", "dependency": "config.h", "style": "direct"},
        ])
        original = before["Makefile"].decode()
        self.assertEqual([l for l in applied.splitlines() if l.startswith("\t")],
                         [l for l in original.splitlines() if l.startswith("\t")])
        self.assertEqual(self.snapshot(self.project), before)

    def test_e9_macro_and_mixed_retain_original_reference(self):
        for style, unchanged_line, expected_line in [
            ("macro", "main.o: $(DEPS)", "DEPS = main.c unused.h config.h extra.h"),
            ("mixed", "HEADERS = unused.h", "main.o: main.c $(HEADERS) config.h extra.h"),
        ]:
            with self.subTest(style=style):
                project = self.root / style
                fixture(project, style)
                before = self.snapshot(project)
                report = self.report([
                    self.missing("main.o", "config.h"),
                    self.missing("main.o", "extra.h"),
                ], project)
                diff, plan = patch(project, report)
                applied = self.apply_to_copy(project, diff, style)
                self.assertIn(unchanged_line, applied.splitlines())
                self.assertIn(expected_line, applied.splitlines())
                self.assertEqual([edit["style"] for edit in plan], [style, style])
                self.assertEqual(self.snapshot(project), before)

    @unittest.skipUnless(os.name == "posix" and shutil.which("make") and shutil.which("gcc"),
                         "E10 requires the Linux GCC/Make teaching environment")
    def test_e10_compile_failure_rejected_and_source_bytes_retained(self):
        before = self.snapshot(self.project)
        original = (self.project / "Makefile").read_text()
        # This candidate adds the missing edge but intentionally breaks the
        # compiler invocation, so patch application alone must not accept it.
        changed = original.replace("main.o: main.c unused.h\n",
                                   "main.o: main.c unused.h config.h\n")
        changed = changed.replace("gcc $(CFLAGS) -c main.c -o main.o",
                                  "gcc -fmember1-invalid-option -c main.c -o main.o")
        candidate = self.root / "compile-failure.patch"
        candidate.write_text("".join(difflib.unified_diff(
            original.splitlines(True), changed.splitlines(True),
            fromfile="a/Makefile", tofile="b/Makefile")), encoding="utf-8")
        evidence = self.root / "compile-failure-evidence"
        result = validate(self.project, candidate, evidence)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["checks"]["patch_applies"])
        self.assertNotIn("build", result["checks"])
        self.assertNotIn("test", result["checks"])
        self.assertIn("fmember1-invalid-option", result["error"])
        self.assertTrue(result["rollback"])
        self.assertTrue(result["source_unchanged"])
        self.assertEqual(self.snapshot(self.project), before)
        self.assertEqual(json.loads((evidence / "validation.json").read_text()), result)


if __name__ == "__main__":
    unittest.main()
