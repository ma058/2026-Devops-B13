"""Portable checks of the shared runner inputs, independent of the Linux Docker run."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "labs/e13e14"))
from member2_faults import fault_environment, permits_fault
from member2_profiles import canonical, digest
from member2_run import main, scenario_config


class SharedProtocolTests(unittest.TestCase):
    def test_faults_require_both_role_and_explicit_scenario(self):
        for scenario in ("normal", "C4", "C5"):
            for role in ("buildchecker", "echecker", "draft", "mdfixer"):
                env = fault_environment(role, scenario)
                self.assertEqual(permits_fault("C4", env), scenario == "C4" and role == "draft")
                self.assertEqual(permits_fault("C5", env), scenario == "C5" and role in ("mdfixer", "draft"))
        self.assertFalse(permits_fault("C4", {"E14_ENABLE_FAULTS": "1"}))

    def test_runner_rejects_different_or_unrecorded_scenario(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            for body in ({"scenario": "C5"}, {"scenario": "normal"}, {}):
                path.write_text(json.dumps(body))
                with self.assertRaisesRegex(ValueError, "CONFIG_SCENARIO_MISMATCH"):
                    scenario_config(path, "C4")

    def test_default_runner_does_not_execute_faults(self):
        marker = RuntimeError("END_TEST")
        with patch.object(sys, "argv", ["runner", "--config", "dummy"]), \
             patch("member2_run.scenario_config", side_effect=marker) as check:
            with self.assertRaisesRegex(RuntimeError, "END_TEST"):
                main()
        check.assert_called_once_with("dummy", "normal")

    def test_example_request_is_bound_to_registered_b13_inputs(self):
        project = ROOT / "course/e13-e14/projects/b13-level-v1"
        manifest = json.loads((project / "manifest.json").read_bytes())
        sample = json.loads((ROOT / "course/e13-e14/member2-draft-request.example.json").read_bytes())
        for field in ("project_id", "base", "target", "profile", "profile_sha256", "candidate_sha256"):
            self.assertEqual(sample[field], manifest[field])
        self.assertEqual(digest(canonical(sample["profile"])), sample["profile_sha256"])
        self.assertEqual(digest((project / "candidate.Dockerfile").read_bytes()), sample["candidate_sha256"])
        self.assertEqual(set(sample), {"protocol", "project_id", "job_id", "trace_id", "base", "target", "profile",
                                      "profile_sha256", "candidate_sha256", "project", "candidate", "out", "build_timeout"})


if __name__ == "__main__":
    unittest.main()
