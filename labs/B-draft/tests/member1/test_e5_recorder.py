"""B13-owned evidence acceptance tests; no Docker invocation."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_e5_manual import validate_result


class EvidenceAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.image = "sha256:" + "a" * 64
        self.command = ["docker", "run", "--network", "none", self.image]

    def test_correct_output_from_same_image(self):
        self.assertTrue(validate_result(0, self.image, self.command, 0, "hello E3\n"))

    def test_nonzero_exit_rejected_even_with_expected_stdout(self):
        self.assertFalse(validate_result(0, self.image, self.command, 7, "hello E3\n"))

    def test_different_image_rejected(self):
        self.command[-1] = "sha256:" + "b" * 64
        self.assertFalse(validate_result(0, self.image, self.command, 0, "hello E3\n"))

    def test_wrong_stdout_rejected_even_with_zero_exit(self):
        self.assertFalse(validate_result(0, self.image, self.command, 0, "wrong\n"))
