"""Frozen checkout, repair-boundary and source-preservation tests."""
from pathlib import Path
import sys
import tempfile
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from member2_run import project_inputs, restore_sources
import member2_tomlc99_full as adapter


class FullProjectRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        directory, manifest = project_inputs({"project_id": "b13-tomlc99-full-preview-v1"})
        restore_sources(directory, manifest, folder)
        cls.base = folder / "base"
        cls.target = folder / "target"
        cls.profile = manifest["profile"]
        cls.profile_sha = manifest["profile_sha256"]

    def report(self, edges):
        return {"schema_version": "e8e10-1", "commit": adapter.TARGET, "profile_sha256": self.profile_sha,
                "findings": [{"type": "MISSING", "target": t, "dependency": d} for t, d in edges]}

    def test_original_source_checks_include_every_cli(self):
        self.assertEqual(adapter.check(self.base, self.profile), adapter.BASE)
        sample = self.target / "toml_sample.c"
        original = sample.read_bytes()
        try:
            sample.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_BINDING_MISMATCH"):
                adapter.check(self.target, self.profile)
        finally:
            sample.write_bytes(original)

    def test_patch_for_current_target_preserves_recipes_and_covers_five_edges(self):
        makefile = self.target / "Makefile"
        original = makefile.read_bytes()
        delta, edits = adapter.patch(self.target, self.report(adapter.EDGES), self.profile)
        self.assertEqual({(e["target"], e["dependency"]) for e in edits}, adapter.EDGES)
        self.assertEqual(original, makefile.read_bytes())
        self.assertIn("+$(EXEC): .EXTRA_PREREQS = toml.h", delta)
        self.assertFalse(any(line.startswith(("+\t", "-\t")) for line in delta.splitlines()))

    def test_incomplete_or_unrelated_missing_findings_fail_before_write(self):
        original = (self.target / "Makefile").read_bytes()
        for edges in (adapter.EDGES - {("toml_json", "toml.h")}, adapter.EDGES | {("libtoml.a", "toml.h")}):
            with self.subTest(edges=sorted(edges)), self.assertRaisesRegex(ValueError, "UNEXPECTED_MISSING"):
                adapter.patch(self.target, self.report(edges), self.profile)
        self.assertEqual((self.target / "Makefile").read_bytes(), original)

    def test_failed_source_or_profile_binding_rejects_report(self):
        for key, value, code in (("commit", adapter.BASE, "STALE_REPORT"), ("schema_version", "old", "SCHEMA"),
                                 ("profile_sha256", "0" * 64, "PROFILE_HASH")):
            report = self.report(adapter.EDGES)
            report[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, code):
                adapter.patch(self.target, report, self.profile)


if __name__ == "__main__":
    unittest.main()
