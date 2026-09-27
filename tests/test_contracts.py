import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_artifact, validate_create, validate_job, validate_md_report  # noqa: E402


def example(name: str):
    return json.loads((ROOT / "contracts" / "examples" / name).read_text(encoding="utf-8"))


class ContractTests(unittest.TestCase):
    def test_four_request_types(self):
        for name in ("draft", "full-check", "incremental-check", "repair"):
            with self.subTest(name=name):
                self.assertEqual([], validate_create(example(f"{name}.request.json")))

    def test_four_success_results(self):
        for name in ("draft", "full-check", "incremental-check", "repair"):
            with self.subTest(name=name):
                self.assertEqual([], validate_job(example(f"{name}.succeeded.json")))

    def test_invalid_job_type(self):
        data = example("draft.request.json")
        data["job_type"] = "ABC"
        self.assertTrue(any("job_type" in error for error in validate_create(data)))

    def test_missing_baseline(self):
        data = example("incremental-check.request.json")
        del data["input"]["baseline"]
        self.assertTrue(any("baseline" in error for error in validate_create(data)))

    def test_wrong_baseline_version(self):
        data = example("incremental-check.request.json")
        data["input"]["baseline"]["commit"] = "c" * 40
        self.assertTrue(any("does not match base_commit" in error for error in validate_create(data)))

    def test_failed_job_requires_error(self):
        data = example("draft.succeeded.json")
        data["status"] = "FAILED"
        data["output"] = None
        self.assertTrue(any("requires object" in error for error in validate_job(data)))

    def test_failed_without_error_has_only_intended_rejection(self):
        valid = example("draft.failed.json")
        invalid = example("invalid/failed-without-error.json")
        self.assertEqual([], validate_job(valid))
        expected = copy.deepcopy(valid)
        expected["error"] = None
        self.assertEqual(expected, invalid)
        self.assertEqual(["error: failed terminal state requires object"], validate_job(invalid))

    def test_finding_does_not_fail_job(self):
        data = example("full-check.succeeded.json")
        self.assertEqual("MISSING", data["output"]["findings"][0]["type"])
        self.assertEqual([], validate_job(data))

    def test_artifact_producer_mismatch(self):
        data = example("draft.succeeded.json")
        artifact = copy.deepcopy(data["output"]["artifacts"][0])
        artifact["producer_job_id"] = "job-other"
        self.assertTrue(validate_artifact(artifact, job_id=data["job_id"]))

    def test_context_files_max_two(self):
        data = example("draft.request.json")
        data["input"]["context_files"] = ["README.md", "INSTALL.md", "HOWTO.md"]
        self.assertTrue(any("at most two" in error for error in validate_create(data)))

    def test_draft_status_examples(self):
        for name in ("accepted", "running", "failed"):
            self.assertEqual([], validate_job(example(f"draft.{name}.json")))

    def test_draft_timeout_and_boolean_exit_rejected(self):
        data = example("draft.request.json")
        data["input"]["build"]["timeout_seconds"] = 0
        self.assertTrue(validate_create(data))
        data = example("draft.succeeded.json")
        data["output"]["build_exit_code"] = False
        self.assertTrue(validate_job(data))

    def test_draft_environment_and_output_must_match(self):
        for key, value in (("repository_commit", "c" * 40), ("configuration_id", "other")):
            data = example("draft.succeeded.json")
            data["output"]["environment"][key] = value
            self.assertTrue(validate_job(data))
        data = example("draft.succeeded.json")
        data["output"]["verify_stdout"] = "wrong\n"
        self.assertTrue(validate_job(data))
    def test_valid_md_report_and_implicit_template(self):
        self.assertEqual([], validate_md_report(example("md-report.json")))
        template = json.loads(
            (ROOT / "fixtures" / "mdfixer" / "implicit-style" / "md-report.template.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual([], validate_md_report(template))

    def test_md_report_allows_empty_findings(self):
        data = example("md-report.json")
        data["findings"] = []
        self.assertEqual([], validate_md_report(data))

    def test_md_report_rejects_short_sha(self):
        data = example("invalid/md-report.invalid-short-sha.json")
        self.assertTrue(any("40-hex" in error for error in validate_md_report(data)))

    def test_md_report_rejects_unknown_detector(self):
        data = example("invalid/md-report.invalid-detector.json")
        self.assertTrue(any("detector" in error for error in validate_md_report(data)))

    def test_tool_report_requires_non_null_producer_job(self):
        data = example("md-report.json")
        data["detector"] = "BUILDCHECKER"
        data["producer_job_id"] = None
        self.assertTrue(any("producer_job_id" in error for error in validate_md_report(data)))
        data["producer_job_id"] = "job-full-001"
        self.assertEqual([], validate_md_report(data))

    def test_manual_report_rejects_invented_producer_job(self):
        data = example("md-report.json")
        data["producer_job_id"] = "job-made-up"
        self.assertTrue(any("manual Oracle" in error for error in validate_md_report(data)))

    def test_md_report_location_is_complete(self):
        data = example("md-report.json")
        data["findings"][0]["location"] = {}
        issues = validate_md_report(data)
        self.assertTrue(any("location.line" in error for error in issues))
        self.assertTrue(any("location.declaration" in error for error in issues))


if __name__ == "__main__":
    unittest.main()
