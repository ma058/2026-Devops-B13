import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_artifact, validate_create, validate_job  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
