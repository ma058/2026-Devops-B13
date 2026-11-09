"""Member2 E8-E10 boundary tests; execute against the real lab.py.

Duplicate/redundant MISSING records are explicitly synthetic robustness inputs.
Shared macro policy: reject with UNSUPPORTED_SHARED_MACRO before producing a
candidate if another target consumes the edited variable, including aliases.
GNU Make/GCC and Linux BuildChecker are exercised without mocks or skips.
"""

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from lab import buildchecker, commit, fixture, patch, run, scan, validate


class Member2Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="member2-e8e10-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def project(self, style="direct"):
        project = self.root / "project"
        fixture(project, style)
        return project

    def replace_makefile(self, project, old, new):
        path = project / "Makefile"
        text = path.read_text()
        self.assertEqual(text.count(old), 1, "Test fixture anchor is ambiguous")
        path.write_text(text.replace(old, new))

    def missing(self, report):
        return [
            (finding["target"], finding["dependency"])
            for finding in report["findings"]
            if finding["type"] == "MISSING"
        ]

    def candidate(self, project, report):
        before = (project / "Makefile").read_bytes()
        report_before = copy.deepcopy(report)
        try:
            return patch(project, report)
        finally:
            self.assertEqual(
                (project / "Makefile").read_bytes(),
                before,
                "Candidate generation/rejection must not write source Makefile",
            )
            self.assertEqual(report, report_before, "patch() must not rewrite its report")

    def apply_to_copy(self, project, diff):
        self.assertTrue(diff, "Expected a nonempty candidate")
        before = (project / "Makefile").read_bytes()
        target = self.root / "apply-copy"
        shutil.copytree(
            project, target, ignore=shutil.ignore_patterns(".git", "*.o", "app")
        )
        patchfile = self.root / "candidate.patch"
        patchfile.write_text(diff)
        run(["git", "init", "-b", "main"], target)
        run(["git", "apply", "--check", str(patchfile.resolve())], target)
        run(["git", "apply", str(patchfile.resolve())], target)
        self.assertEqual((project / "Makefile").read_bytes(), before)
        return target

    def assert_exact_makefile(self, target, expected):
        self.assertEqual(
            (target / "Makefile").read_text(),
            expected,
            "Compare the whole Makefile: keep RD dependencies, variables and recipes",
        )


class E8Member2(Member2Case):
    def test_mixed_md_rd_order_preserves_two_redundant_dependencies(self):
        project = self.project()
        (project / "spare.h").write_text("/* declared but not included */\n")
        self.replace_makefile(
            project, "main.o: main.c unused.h\n",
            "main.o: main.c unused.h spare.h\n",
        )
        commit(project, "member2: add a second real redundant dependency")
        report = scan(project)
        observed = {
            (f["type"], f["target"], f["dependency"]) for f in report["findings"]
        }
        self.assertEqual(observed, {
            ("MISSING", "main.o", "config.h"),
            ("REDUNDANT", "main.o", "unused.h"),
            ("REDUNDANT", "main.o", "spare.h"),
        })
        records = {
            (f["type"], f["dependency"]): f for f in report["findings"]
        }
        # Reorder real findings; add one explicitly synthetic duplicate RD.
        report["findings"] = [
            copy.deepcopy(records[("REDUNDANT", "spare.h")]),
            copy.deepcopy(records[("MISSING", "config.h")]),
            copy.deepcopy(records[("REDUNDANT", "unused.h")]),
            copy.deepcopy(records[("REDUNDANT", "spare.h")]),
        ]
        before = (project / "Makefile").read_text()
        diff, plan = self.candidate(project, report)
        self.assertEqual(plan, [
            {"target": "main.o", "dependency": "config.h", "style": "direct"}
        ])
        applied = self.apply_to_copy(project, diff)
        self.assert_exact_makefile(applied, before.replace(
            "main.o: main.c unused.h spare.h\n",
            "main.o: main.c unused.h spare.h config.h\n",
        ))

    def test_redundant_only_report_keeps_makefile_unchanged(self):
        project = self.project()
        (project / "spare.h").write_text("/* unused second header */\n")
        self.replace_makefile(
            project, "main.o: main.c unused.h\n",
            "main.o: main.c unused.h spare.h config.h\n",
        )
        commit(project, "member2: repair MD while retaining two RD edges")
        report = scan(project)
        self.assertEqual(self.missing(report), [])
        self.assertEqual({
            (f["type"], f["target"], f["dependency"]) for f in report["findings"]
        }, {
            ("REDUNDANT", "main.o", "unused.h"),
            ("REDUNDANT", "main.o", "spare.h"),
        })
        self.assertEqual(self.candidate(project, report), ("", []))

    def test_repeated_candidate_generation_is_deterministic(self):
        project = self.project("mixed")
        report = scan(project)
        first = self.candidate(project, report)
        second = self.candidate(project, report)
        self.assertEqual(first, second)
        self.assertEqual(first[1], [
            {"target": "main.o", "dependency": "config.h", "style": "mixed"}
        ])
        before = (project / "Makefile").read_text()
        applied = self.apply_to_copy(project, second[0])
        self.assert_exact_makefile(applied, before.replace(
            "main.o: main.c $(HEADERS)\n",
            "main.o: main.c $(HEADERS) config.h\n",
        ))


class E9Member2(Member2Case):
    def check_duplicate_md(self, style):
        project = self.project(style)
        report = scan(project)
        self.assertEqual(self.missing(report), [("main.o", "config.h")])
        md = next(f for f in report["findings"] if f["type"] == "MISSING")
        rd = next(f for f in report["findings"] if f["type"] == "REDUNDANT")
        # Artificial duplicate input; the detector itself emitted only one MD.
        report["findings"] = [copy.deepcopy(f) for f in [rd, md, md, rd, md]]
        before = (project / "Makefile").read_text()
        diff, plan = self.candidate(project, report)
        self.assertEqual(plan, [
            {"target": "main.o", "dependency": "config.h", "style": style}
        ], "Duplicate (target, dependency) records must produce exactly one edit")
        lines = {
            "direct": "main.o: main.c unused.h",
            "macro": "DEPS = main.c unused.h",
            "mixed": "main.o: main.c $(HEADERS)",
        }
        line = lines[style]
        applied = self.apply_to_copy(project, diff)
        self.assert_exact_makefile(
            applied, before.replace(line + "\n", line + " config.h\n")
        )

    def test_duplicate_md_direct_is_added_once(self):
        self.check_duplicate_md("direct")

    def test_duplicate_md_macro_is_added_once(self):
        self.check_duplicate_md("macro")

    def test_duplicate_md_mixed_is_added_once(self):
        self.check_duplicate_md("mixed")

    def test_same_dependency_on_two_targets_is_not_collapsed(self):
        project = self.project()
        (project / "helper.c").write_text(
            '#include "config.h"\nint helper(void){return 0;}\n'
        )
        commit(project, "member2: both translation units include config.h")
        report = scan(project)
        self.assertEqual(set(self.missing(report)), {
            ("main.o", "config.h"), ("helper.o", "config.h")
        })
        before = (project / "Makefile").read_text()
        diff, plan = self.candidate(project, report)
        self.assertEqual(len(plan), 2)
        self.assertEqual({(e["target"], e["dependency"]) for e in plan}, {
            ("main.o", "config.h"), ("helper.o", "config.h")
        })
        applied = self.apply_to_copy(project, diff)
        expected = before.replace(
            "main.o: main.c unused.h\n", "main.o: main.c unused.h config.h\n"
        ).replace("helper.o: helper.c\n", "helper.o: helper.c config.h\n")
        self.assert_exact_makefile(applied, expected)

    def test_two_dependencies_on_one_target_are_not_collapsed(self):
        project = self.project()
        main = project / "main.c"
        main.write_text('#include "extra.h"\n' + main.read_text())
        commit(project, "member2: main includes two independently missing headers")
        report = scan(project)
        self.assertEqual(set(self.missing(report)), {
            ("main.o", "config.h"), ("main.o", "extra.h")
        })
        before = (project / "Makefile").read_text()
        diff, plan = self.candidate(project, report)
        self.assertEqual(len(plan), 2)
        self.assertEqual({(e["target"], e["dependency"]) for e in plan}, {
            ("main.o", "config.h"), ("main.o", "extra.h")
        })
        applied = self.apply_to_copy(project, diff)
        # scan() emits config.h then extra.h; preserve that stable order.
        self.assert_exact_makefile(applied, before.replace(
            "main.o: main.c unused.h\n",
            "main.o: main.c unused.h config.h extra.h\n",
        ))

    def check_already_declared(self, style):
        project = self.project(style)
        lines = {
            "direct": "main.o: main.c unused.h",
            "macro": "DEPS = main.c unused.h",
            "mixed": "main.o: main.c $(HEADERS)",
        }
        line = lines[style]
        self.replace_makefile(project, line + "\n", line + " config.h\n")
        commit(project, "member2: dependency is already genuinely declared")
        report = scan(project)
        self.assertEqual(self.missing(report), [])
        self.assertEqual(self.candidate(project, report), ("", []))
        # Same real commit, deliberately inconsistent synthetic finding.
        synthetic = copy.deepcopy(report)
        synthetic["findings"].append({
            "type": "MISSING", "target": "main.o", "dependency": "config.h"
        })
        self.assertEqual(
            self.candidate(project, synthetic), ("", []),
            "A synthetic repeated MD must not append an already declared dependency",
        )

    def test_already_declared_direct_is_not_appended_again(self):
        self.check_already_declared("direct")

    def test_already_declared_macro_is_not_appended_again(self):
        self.check_already_declared("macro")

    def test_already_declared_mixed_is_not_appended_again(self):
        self.check_already_declared("mixed")

    def check_shared_macro_rejected(self, kind):
        project = self.project("macro")
        makefile = project / "Makefile"
        text = makefile.read_text()
        if kind == "direct":
            text = text.replace(
                "helper.o: helper.c\n", "helper.o: helper.c $(DEPS)\n"
            )
        elif kind == "alias":
            text = "ALIAS = $(DEPS)\n" + text.replace(
                "helper.o: helper.c\n", "helper.o: helper.c $(ALIAS)\n"
            )
        elif kind == "nested":
            text = "INNER = $(DEPS)\nOUTER = $(INNER)\n" + text.replace(
                "helper.o: helper.c\n", "helper.o: helper.c $(OUTER)\n"
            )
        elif kind == "extra-target":
            text += "\n.PHONY: audit\naudit: $(DEPS)\n"
        else:
            raise AssertionError("Unknown test fixture")
        makefile.write_text(text)
        commit(project, "member2: add another consumer of the DEPS variable")
        report = scan(project)
        self.assertEqual(self.missing(report), [("main.o", "config.h")])
        # ADR choice: reject shared-variable repairs instead of silently widening
        # another target's dependency set. No success fallback or broad exception.
        with self.assertRaisesRegex(ValueError, r"^UNSUPPORTED_SHARED_MACRO(?:$|[ :])"):
            self.candidate(project, report)

    def test_shared_macro_direct_consumer_is_rejected(self):
        self.check_shared_macro_rejected("direct")

    def test_shared_macro_alias_consumer_is_rejected(self):
        self.check_shared_macro_rejected("alias")

    def test_shared_macro_nested_alias_consumer_is_rejected(self):
        self.check_shared_macro_rejected("nested")

    def test_shared_macro_extra_target_consumer_is_rejected(self):
        self.check_shared_macro_rejected("extra-target")

    def test_unused_alias_does_not_block_private_macro_repair(self):
        project = self.project("macro")
        makefile = project / "Makefile"
        makefile.write_text("UNUSED_ALIAS = $(DEPS)\n" + makefile.read_text())
        commit(project, "member2: unused alias has no other target consumer")
        report = scan(project)
        before = makefile.read_text()
        diff, plan = self.candidate(project, report)
        self.assertEqual(plan, [
            {"target": "main.o", "dependency": "config.h", "style": "macro"}
        ])
        applied = self.apply_to_copy(project, diff)
        self.assert_exact_makefile(applied, before.replace(
            "DEPS = main.c unused.h\n", "DEPS = main.c unused.h config.h\n"
        ))


class E10Member2(Member2Case):
    def accept_and_commit(self):
        project = self.project()
        original_report = scan(project)
        original_commit = original_report["commit"]
        diff, _ = self.candidate(project, original_report)
        patchfile = self.root / "accept.patch"
        patchfile.write_text(diff)
        header_before = (project / "config.h").read_bytes()
        result = validate(project, patchfile, self.root / "accept")
        if result["error"] is not None:
            raise RuntimeError("Validation command/environment error: " + str(result))
        self.assertTrue(result["accepted"], result)
        for key in ["patch_applies", "build", "test", "header_change", "no_missing"]:
            self.assertIs(result["checks"].get(key), True, key)
        self.assertFalse(result["rollback"])
        self.assertFalse(result["source_unchanged"])
        self.assertEqual((project / "config.h").read_bytes(), header_before)
        current_commit = commit(project, "member2: commit genuinely accepted repair")
        self.assertNotEqual(original_commit, current_commit)
        return project, original_report, current_commit

    def test_accepted_repair_real_recheck_returns_no_change(self):
        project, _, current_commit = self.accept_and_commit()
        accepted = (project / "Makefile").read_bytes()
        fresh = scan(project)
        self.assertEqual(fresh["commit"], current_commit)
        self.assertEqual(self.missing(fresh), [])
        # Actual Linux strace/Make collection, never a mock or an old report.
        dynamic = buildchecker(project, self.root / "repeat-buildchecker")
        self.assertEqual(dynamic["status"], "SUCCEEDED")
        self.assertEqual(self.missing(dynamic), [])
        self.assertTrue(any(
            f["type"] == "REDUNDANT" and f["target"] == "main.o"
            and f["dependency"] == "unused.h"
            for f in dynamic["findings"]
        ))
        for _ in range(2):
            self.assertEqual(self.candidate(project, fresh), ("", []))
        self.assertEqual((project / "Makefile").read_bytes(), accepted)
        rule = next(
            line for line in accepted.decode().splitlines()
            if line.startswith("main.o:")
        )
        self.assertEqual(rule.split(":", 1)[1].split().count("config.h"), 1)
        self.assertEqual((project / "config.h").read_text().strip(), "#define VALUE 1")
        self.assertEqual(run(["git", "status", "--porcelain"], project).strip(), "")
        # Empty candidates mean NO_CHANGE; validate() is intentionally not called.

    def test_pre_accept_report_is_rejected_after_real_commit(self):
        project, old_report, current_commit = self.accept_and_commit()
        self.assertNotEqual(old_report["commit"], current_commit)
        with self.assertRaisesRegex(ValueError, r"^STALE_REPORT$"):
            self.candidate(project, old_report)
        fresh = scan(project)
        self.assertEqual(fresh["commit"], current_commit)
        self.assertEqual(self.candidate(project, fresh), ("", []))
        self.assertEqual(run(["git", "status", "--porcelain"], project).strip(), "")


if __name__ == "__main__":
    unittest.main()
