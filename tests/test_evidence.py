import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collect_evidence import Recorder


class EvidenceTests(unittest.TestCase):
    def test_expected_failure_preserves_both_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Recorder(Path(tmp) / "run", "TEST", "expected-failure")
            c, out, err = r.run([sys.executable, "-c", "import sys; print('out'); print('err',file=sys.stderr); sys.exit(7)"])
            r.check("expected_failure", 7, c["exit_code"], c["exit_code"] == 7, c["id"])
            self.assertEqual(r.finish(), "PASS")
            self.assertEqual(out.strip(), "out")
            self.assertEqual(err.strip(), "err")
            self.assertEqual(json.loads((r.output / "summary.json").read_text(encoding="utf-8"))["commands"][0]["exit_code"], 7)
            with self.assertRaises(FileExistsError):
                Recorder(r.output, "TEST", "collision")

    def test_timeout_and_missing_executable_leave_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Recorder(Path(tmp) / "run", "TEST", "timeout")
            c, out, _ = r.run([sys.executable, "-u", "-c", "import time; print('started'); time.sleep(5)"], timeout=0.3)
            self.assertTrue(c["timed_out"])
            self.assertIn("started", out)
            missing, _, _ = r.run([str(Path(tmp) / "does-not-exist")])
            self.assertIsNotNone(missing["execution_error"])
            r.check("timeout", False, True, False)
            self.assertEqual(r.finish(), "FAIL")
            self.assertTrue((r.output / "summary.json").is_file())

    def test_missing_required_check_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Recorder(Path(tmp) / "run", "TEST", "not-run")
            with self.assertRaises(ValueError):
                r.check("invalid", "valid state", "typo", status="PASSED")
            r.check("detector", "executed", "unavailable", status="NOT_RUN")
            self.assertEqual(r.finish(), "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
