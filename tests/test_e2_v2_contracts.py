"""Tests for the Pair13 finding-report 2.0 candidate (B13 side).

Covers: B13's independent v2 semantic validator, the pinned A13 v2 snapshot
integrity, acceptance/rejection of both groups' fixtures, the MDFixer
consumption policy on v2 input, and v1 -> v2 migration equivalence.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_v2 import consume_missing_v2, validate_report_v2  # noqa: E402
from verify_a13_v2_interop import (  # noqa: E402
    A13_INVALID_EXPECTATIONS,
    A13_V2_COMMIT,
    B13_INVALID_EXPECTATIONS,
    SNAPSHOT,
    B13_V2,
    run_checks,
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class A13V2SnapshotTests(unittest.TestCase):
    def test_all_interop_checks_pass(self):
        checks = run_checks()
        self.assertTrue(checks)
        failures = [c for c in checks if c["status"] != "PASS"]
        self.assertEqual([], failures, failures)

    def test_snapshot_pin_is_the_v2_candidate_commit(self):
        manifest = load(SNAPSHOT / "manifest.json")
        self.assertEqual(A13_V2_COMMIT, manifest["source_commit"])

    def test_a13_valid_example_is_accepted(self):
        errors = validate_report_v2(load(SNAPSHOT / "examples" / "md-report.valid.json"))
        self.assertEqual([], errors)

    def test_a13_invalid_examples_are_rejected(self):
        for filename, keyword in sorted(A13_INVALID_EXPECTATIONS.items()):
            with self.subTest(fixture=filename):
                errors = validate_report_v2(load(SNAPSHOT / "examples" / "invalid" / filename))
                self.assertTrue(errors, f"{filename} must be rejected")
                self.assertTrue(
                    any(keyword in message for message in errors),
                    f"{filename}: expected {keyword!r} in {errors}",
                )


class B13V2SampleTests(unittest.TestCase):
    def test_synthetic_migration_is_valid(self):
        errors = validate_report_v2(load(B13_V2 / "md-report.valid.json"))
        self.assertEqual([], errors)

    def test_real_e3_target_report_is_valid(self):
        errors = validate_report_v2(load(B13_V2 / "md-report.e3-target.valid.json"))
        self.assertEqual([], errors)

    def test_b13_invalid_examples_are_rejected(self):
        for filename, keyword in sorted(B13_INVALID_EXPECTATIONS.items()):
            with self.subTest(fixture=filename):
                errors = validate_report_v2(load(B13_V2 / "invalid" / filename))
                self.assertTrue(errors, f"{filename} must be rejected")
                self.assertTrue(
                    any(keyword in message for message in errors),
                    f"{filename}: expected {keyword!r} in {errors}",
                )

    def test_v1_to_v2_migration_preserves_findings(self):
        v1 = load(ROOT / "contracts" / "examples" / "md-report.json")
        v2 = load(B13_V2 / "md-report.valid.json")
        v1_set = sorted((f["type"], f["target"], f["dependency"]) for f in v1["findings"])
        v2_set = sorted((f["type"], f["target"], f["dependency"]) for f in v2["findings"])
        self.assertEqual(v1_set, v2_set)


class MDFixerConsumptionV2Tests(unittest.TestCase):
    def test_a13_sample_consumes_missing_only(self):
        result = consume_missing_v2(load(SNAPSHOT / "examples" / "md-report.valid.json"))
        self.assertEqual(
            ["config.h"], [item["dependency"] for item in result["consumed_findings"]]
        )
        self.assertEqual(
            ["unused.h"], [item["dependency"] for item in result["skipped_findings"]]
        )

    def test_resolved_location_supplies_makefile_path(self):
        result = consume_missing_v2(load(B13_V2 / "md-report.e3-target.valid.json"))
        self.assertEqual(1, len(result["consumed_findings"]))
        entry = result["consumed_findings"][0]
        self.assertEqual("config.h", entry["dependency"])
        self.assertEqual("Makefile", entry["makefile_path"])
        self.assertEqual(9, entry["line"])

    def test_unresolved_missing_requires_explicit_default(self):
        report = load(B13_V2 / "md-report.valid.json")
        report["findings"][0]["location"] = {
            "status": "UNRESOLVED",
            "reason": "declaration not located in this synthetic sample",
        }
        with self.assertRaisesRegex(ValueError, "default_makefile"):
            consume_missing_v2(report)
        result = consume_missing_v2(report, default_makefile="Makefile")
        self.assertEqual("Makefile", result["consumed_findings"][0]["makefile_path"])


class ValidatorRuleTests(unittest.TestCase):
    def base_report(self):
        return load(B13_V2 / "md-report.valid.json")

    def test_findings_array_may_be_empty(self):
        report = self.base_report()
        report["findings"] = []
        self.assertEqual([], validate_report_v2(report))

    def test_oracle_with_producer_job_rejected(self):
        report = self.base_report()
        report["producer_job_id"] = "job-e2-001"
        errors = validate_report_v2(report)
        self.assertTrue(any("producer_job_id" in message for message in errors))

    def test_real_detector_requires_producer_job(self):
        report = self.base_report()
        report["detector"] = "BUILDCHECKER"
        errors = validate_report_v2(report)
        self.assertTrue(any("producer_job_id" in message for message in errors))
        report["producer_job_id"] = "job-full-001"
        self.assertEqual([], validate_report_v2(report))

    def test_finding_configuration_mismatch_rejected(self):
        report = self.base_report()
        report["findings"][0]["configuration_id"] = "gcc-O2"
        errors = validate_report_v2(report)
        self.assertTrue(any("configuration_id" in message for message in errors))

    def test_unknown_extension_namespace_rejected(self):
        report = self.base_report()
        report["extensions"] = {"m13.custom": True}
        errors = validate_report_v2(report)
        self.assertTrue(any("namespaced" in message for message in errors))

    def test_namespaced_extension_accepted(self):
        report = self.base_report()
        report["extensions"] = {"b13.note": "anything", "a13.note": 1, "pair13.note": None}
        self.assertEqual([], validate_report_v2(report))

    def test_explicit_null_extensions_rejected_top_level_and_finding(self):
        report = self.base_report()
        report["extensions"] = None
        errors = validate_report_v2(report)
        self.assertTrue(any("explicit null rejected" in message for message in errors))
        report = self.base_report()
        report["findings"][0]["extensions"] = None
        errors = validate_report_v2(report)
        self.assertTrue(any("explicit null rejected" in message for message in errors))

    def test_artifact_locator_uri_type_discipline(self):
        locator = {
            "uri": "artifact://pair13/job-1/report.json",
            "repository_url": "https://github.com/example/x.git",
            "repository_commit": "a" * 40,
            "repository_path": "contracts/examples",
            "sha256": "a" * 64,
        }
        report = self.base_report()
        report["artifact_locator"] = dict(locator)
        self.assertEqual([], validate_report_v2(report))
        for bad in (None, [], 123, "", "pair13://x"):
            with self.subTest(uri=bad):
                report = self.base_report()
                report["artifact_locator"] = {**locator, "uri": bad}
                errors = validate_report_v2(report)
                self.assertTrue(any("artifact_locator.uri" in message for message in errors))

    def test_path_normalisation_variants_rejected(self):
        # These collapse to valid paths under PurePosixPath; the raw segments
        # must be checked before any normalisation.
        report = self.base_report()
        report["findings"][0]["dependency"] = "a//config.h"
        self.assertTrue(validate_report_v2(report))
        for bad in ("a//config.h", "a/./config.h", "config.h/", "./config.h", "a/../config.h"):
            with self.subTest(dependency=bad):
                report = self.base_report()
                report["findings"][0]["dependency"] = bad
                errors = validate_report_v2(report)
                self.assertTrue(any("dependency" in message for message in errors))
        for bad in ("a//Makefile", "Makefile/", "./Makefile"):
            with self.subTest(path=bad):
                report = self.base_report()
                report["findings"][0]["location"] = {
                    "status": "RESOLVED", "path": bad, "line": 1}
                errors = validate_report_v2(report)
                self.assertTrue(any("location.path" in message for message in errors))

    def test_unhashable_detector_and_type_error_not_crash(self):
        report = self.base_report()
        report["detector"] = []
        errors = validate_report_v2(report)  # must return errors, not TypeError
        self.assertTrue(any("detector" in message for message in errors))
        report = self.base_report()
        report["findings"][0]["type"] = {}
        errors = validate_report_v2(report)
        self.assertTrue(any("type" in message for message in errors))
        report = self.base_report()
        report["findings"] = [["not", "a", "dict"]]
        errors = validate_report_v2(report)
        self.assertTrue(any("object required" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
