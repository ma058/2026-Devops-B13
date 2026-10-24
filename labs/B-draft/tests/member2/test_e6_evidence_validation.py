"""Saved-evidence consistency tests; no Docker commands or original work mutation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/verify_e6_b_evidence.py"
SPEC = importlib.util.spec_from_file_location("member2_e6_verifier", SCRIPT)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)
IMAGE = "sha256:" + "a" * 64


def digest(data):
    return hashlib.sha256(data).hexdigest()


class EvidenceValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="member2-e6-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        (self.project / "src").mkdir(parents=True)
        inputs = {"main.c": b"int main(void) { return 0; }\n",
                  "src/config.h": b"#define VALUE 1\n"}
        for name, content in inputs.items():
            (self.project / name).write_bytes(content)
        (self.root / "iter-01").mkdir()
        (self.root / "iter-01/build-stdout.log").write_bytes(b"")
        (self.root / "iter-01/build-stderr.log").write_bytes(b"/bin/sh: 1: make: not found\n")
        (self.root / "iter-02").mkdir()
        candidate = b"FROM synthetic-test-fixture\nRUN make\n"
        (self.root / "iter-02/Dockerfile").write_bytes(candidate)
        self.write_inspect(IMAGE)
        (self.root / "verify.log").write_bytes(b"hello E3\n")
        self.report = {
            "status": "SUCCEEDED", "trace_id": "member2-synthetic-test",
            "attempts": [
                {"iteration": 1, "build_exit_code": 1, "failure_class": "MISSING_MAKE"},
                {"iteration": 2, "build_exit_code": 0, "image_id": IMAGE},
            ],
            "candidate_sha256": digest(candidate),
            "input_sha256": {name: digest(content) for name, content in inputs.items()},
            "verification": {
                "command": ["docker", "run", "--rm", "--network", "none", "--cpus", "1",
                            "--memory", "128m", "--pids-limit", "64", "--cidfile",
                            "/evidence/verify-container-id.txt", IMAGE],
                "exit_code": 0, "output_matches": True,
                "actual_output": "hello E3\n", "expected_output": "hello E3",
            },
        }

    def write_inspect(self, image):
        (self.root / "iter-02/image-inspect.json").write_text(
            json.dumps([{"Id": image}]), encoding="utf-8")

    def verify(self):
        (self.root / "result.json").write_text(json.dumps(self.report), encoding="utf-8")
        return VERIFIER.verify(self.root)

    def test_valid_nested_input_evidence_passes(self):
        self.assertTrue(self.verify()["passed"])

    def test_valid_uppercase_digest_passes(self):
        self.report["input_sha256"] = {
            name: value.upper() for name, value in self.report["input_sha256"].items()}
        self.assertTrue(self.verify()["passed"])

    def test_deleted_manifest_entry_is_rejected(self):
        del self.report["input_sha256"]["main.c"]
        with self.assertRaises(ValueError):
            self.verify()

    def test_extra_project_file_is_rejected(self):
        (self.project / "extra.txt").write_bytes(b"not in manifest\n")
        with self.assertRaises(ValueError):
            self.verify()

    def test_empty_manifest_is_rejected(self):
        self.report["input_sha256"] = {}
        with self.assertRaises(ValueError):
            self.verify()

    def test_manifest_must_be_mapping(self):
        for invalid in (None, [], "main.c"):
            with self.subTest(value=invalid):
                self.report["input_sha256"] = invalid
                with self.assertRaises(ValueError):
                    self.verify()

    def test_invalid_digest_is_rejected(self):
        for invalid in (None, 123, "a" * 63, "z" * 64):
            with self.subTest(value=invalid):
                self.report["input_sha256"]["main.c"] = invalid
                with self.assertRaises(ValueError):
                    self.verify()

    def test_noncanonical_or_escaping_paths_are_rejected(self):
        for invalid in ("", "../main.c", "/main.c", "./main.c", "src/../main.c",
                        "src//config.h", "C:/main.c", "src\\config.h"):
            with self.subTest(path=invalid):
                self.report["input_sha256"] = {invalid: "a" * 64}
                with self.assertRaises(ValueError):
                    self.verify()

    def test_symlink_inside_project_is_rejected(self):
        path = self.project / "main.c"
        path.unlink()
        try:
            path.symlink_to("src/config.h")
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Host cannot create test symlink: " + str(exc))
        self.report["input_sha256"]["main.c"] = digest((self.project / "src/config.h").read_bytes())
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_file_content_is_rejected(self):
        (self.project / "main.c").write_bytes(b"changed\n")
        with self.assertRaises(ValueError):
            self.verify()

    def test_network_changed_to_bridge_is_rejected(self):
        command = self.report["verification"]["command"]
        command[command.index("--network") + 1] = "bridge"
        with self.assertRaises(ValueError):
            self.verify()

    def test_removed_network_option_is_rejected(self):
        command = self.report["verification"]["command"]
        index = command.index("--network")
        del command[index:index + 2]
        with self.assertRaises(ValueError):
            self.verify()

    def test_duplicate_network_override_is_rejected(self):
        self.report["verification"]["command"][-1:-1] = ["--network", "host"]
        with self.assertRaises(ValueError):
            self.verify()

    def test_network_alias_override_is_rejected(self):
        self.report["verification"]["command"][-1:-1] = ["--net", "host"]
        with self.assertRaises(ValueError):
            self.verify()

    def test_command_must_be_docker_run(self):
        self.report["verification"]["command"][1] = "exec"
        with self.assertRaises(ValueError):
            self.verify()

    def test_command_must_be_string_array(self):
        self.report["verification"]["command"][0] = None
        with self.assertRaises(ValueError):
            self.verify()

    def test_different_runtime_image_is_rejected(self):
        self.report["verification"]["command"][-1] = "sha256:" + "b" * 64
        with self.assertRaises(ValueError):
            self.verify()

    def test_mutable_image_tag_is_rejected(self):
        image = "synthetic:mutable"
        self.write_inspect(image)
        self.report["attempts"][1]["image_id"] = image
        self.report["verification"]["command"][-1] = image
        with self.assertRaises(ValueError):
            self.verify()

    def test_network_option_after_image_is_rejected(self):
        self.report["verification"]["command"][-1:-1] = [IMAGE, "--network", "none"]
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == "__main__":
    unittest.main()
