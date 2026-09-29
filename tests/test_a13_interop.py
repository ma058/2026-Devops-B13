import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_a13_interop import (  # noqa: E402
    SNAPSHOT,
    is_project_path,
    normalize_missing,
    run_checks,
    validate_native_report,
)


def report(relative: str):
    return json.loads((SNAPSHOT / relative).read_text(encoding="utf-8"))


class A13InteropTests(unittest.TestCase):
    def test_snapshot_checks_pass(self):
        checks, _, _ = run_checks()
        self.assertTrue(checks)
        self.assertTrue(all(item["status"] == "PASS" for item in checks), checks)

    def test_full_report_consumes_missing_only(self):
        data = report("artifacts/job-full-a13-001/md-report.json")
        normalized = normalize_missing(data)
        self.assertEqual(["config.h"], [item["dependency"] for item in normalized["consumed_findings"]])
        self.assertEqual(["unused.h"], [item["dependency"] for item in normalized["skipped_findings"]])

    def test_unresolved_location_needs_explicit_default(self):
        data = report("artifacts/job-incremental-a13-001/md-report.json")
        with self.assertRaisesRegex(ValueError, "default_makefile"):
            normalize_missing(data)
        normalized = normalize_missing(data, default_makefile="Makefile")
        self.assertEqual("UNRESOLVED", normalized["consumed_findings"][0]["location_status"])
        self.assertIsNone(normalized["consumed_findings"][0]["location_line"])

    def test_project_paths_reject_absolute_parent_and_windows(self):
        for value in ("/usr/include/stdio.h", "../secret.h", "src\\config.h", "./config.h", ""):
            with self.subTest(value=value):
                self.assertFalse(is_project_path(value))

    def test_report_rejects_commit_and_configuration_mismatch(self):
        data = report("artifacts/job-full-a13-001/md-report.json")
        bad_commit = copy.deepcopy(data)
        bad_commit["findings"][0]["commit"] = "b" * 40
        self.assertTrue(any("commit" in item for item in validate_native_report(bad_commit)))
        bad_configuration = copy.deepcopy(data)
        bad_configuration["findings"][0]["configuration_id"] = "clang-default"
        self.assertTrue(any("configuration_id" in item for item in validate_native_report(bad_configuration)))


if __name__ == "__main__":
    unittest.main()
