"""Offline checks must fail on relabelled runs and incomplete header probes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_member2_shared import check, check_preview_probe


class LocalPreviewEvidenceTests(unittest.TestCase):
    def test_shared_scope_does_not_accept_local_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "matrix-test.json").write_text(json.dumps({"status": "PASS", "scope": "B13_LOCAL_PREVIEW"}))
            with self.assertRaisesRegex(ValueError, "scope"):
                check(root)

    def test_header_probe_requires_each_product_to_advance(self):
        products = ["toml.o", "libtoml.a", "libtoml.so.1.0", "toml_json", "toml_cat", "toml_sample"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            after = dict.fromkeys(products, 2)
            after["libtoml.a"] = 1
            (root / "header-probe.json").write_text(json.dumps({
                "path": "toml.h", "argv": ["make", "all"], "before_mtime_ns": dict.fromkeys(products, 1),
                "after_mtime_ns": after}))
            with self.assertRaisesRegex(ValueError, "mtime"):
                check_preview_probe(root, products)
