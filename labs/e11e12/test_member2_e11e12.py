"""Member 2 mixed-style integration and byte-preserving rejection tests.

Uses actual Git/GCC/Make/strace; does not mock successful execution or DRAFT.
The dedicated runner preserves fixtures via M2_E11E12_TEST_OUT. Ordinary
unittest discovery uses temporary fixtures. This suite does not claim image
reuse, real-project integration, or A13 participation.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from lab import commit, fixture, patch, run, scan, validate
from pipeline import full
from consume_report import Failure, consume, verify_received


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def source_bytes(project):
    return {p.relative_to(project).as_posix(): p.read_bytes()
            for p in sorted(project.rglob("*")) if p.is_file()
            and ".git" not in p.relative_to(project).parts}


class Member2MixedIntegration(unittest.TestCase):
    def setUp(self):
        for tool in ("git", "gcc"):
            if shutil.which(tool) is None:
                raise RuntimeError("ENVIRONMENT_ERROR: required tool missing: " + tool)
        evidence = os.environ.get("M2_E11E12_TEST_OUT")
        if evidence:
            self.root = Path(evidence) / self._testMethodName
            self.root.mkdir(parents=True, exist_ok=False)
        else:
            temporary = tempfile.TemporaryDirectory(prefix="member2-e11e12-")
            self.addCleanup(temporary.cleanup)
            self.root = Path(temporary.name)
        self.project = self.root / "original-project"
        fixture(self.project, "mixed")
        self.c0 = run(["git", "rev-parse", "HEAD"], self.project).strip()

    def make_target(self, split_targets=False):
        if split_targets:
            helper = self.project / "helper.c"
            helper.write_text('#include "extra.h"\n' + helper.read_text(), encoding="utf-8")
            makefile = self.project / "Makefile"
            makefile.write_text(makefile.read_text().replace(
                "helper.o: helper.c\n", "helper.o: helper.c $(HEADERS)\n"), encoding="utf-8")
        else:
            main = self.project / "main.c"
            main.write_text('#include "extra.h"\n' + main.read_text(), encoding="utf-8")
        target = commit(self.project, "member2 C1 actual include change")
        report = scan(self.project)
        (self.root / "input-report.json").write_bytes(json_bytes(report))
        return target, report

    def assert_original(self, before, target):
        self.assertEqual(source_bytes(self.project), before, "Original project bytes changed")
        self.assertEqual(run(["git", "rev-parse", "HEAD"], self.project).strip(), target)

    def exercise_repair(self, report, expected, expected_plan, redundant):
        for tool in ("make", "strace"):
            if shutil.which(tool) is None:
                raise RuntimeError("ENVIRONMENT_ERROR: required tool missing: " + tool)
        before = source_bytes(self.project)
        original_report = (self.root / "input-report.json").read_bytes()
        target = report["commit"]
        candidate, plan = patch(self.project, report)
        self.assertEqual(plan, expected_plan)
        self.assert_original(before, target)
        patchfile = self.root / "candidate.patch"
        patchfile.write_text(candidate, encoding="utf-8")
        (self.root / "repair-plan.json").write_bytes(json_bytes({"edits": plan}))
        working = self.root / "repair-working-copy"
        run(["git", "clone", "--no-hardlinks", str(self.project), str(working)], self.root)
        verdict = validate(working, patchfile, self.root / "validation")
        self.assertTrue(verdict["accepted"], verdict)
        self.assertTrue(all(verdict["checks"].get(name) is True for name in
                            ("patch_applies", "build", "test", "header_change", "no_missing")))
        self.assertEqual((working / "Makefile").read_text(), expected)
        for name, raw in before.items():
            if name != "Makefile":
                self.assertEqual((working / name).read_bytes(), raw, name)
        recheck = full(working, self.root / "full-recheck")
        observed = {(item["type"], item["target"], item["dependency"])
                    for item in recheck["findings"]}
        self.assertEqual(observed, redundant)
        self.assert_original(before, target)
        self.assertEqual((self.root / "input-report.json").read_bytes(), original_report)

    def test_mixed_two_headers_keep_macro_recipe_and_redundant(self):
        _, report = self.make_target()
        original = (self.project / "Makefile").read_text()
        self.assertEqual({(f["type"], f["target"], f["dependency"]) for f in report["findings"]}, {
            ("MISSING", "main.o", "config.h"), ("MISSING", "main.o", "extra.h"),
            ("REDUNDANT", "main.o", "unused.h")})
        expected = original.replace("main.o: main.c $(HEADERS)\n",
                                    "main.o: main.c $(HEADERS) config.h extra.h\n")
        self.assertNotEqual(expected, original)
        self.exercise_repair(report, expected, [
            {"target": "main.o", "dependency": "config.h", "style": "mixed"},
            {"target": "main.o", "dependency": "extra.h", "style": "mixed"}],
            {("REDUNDANT", "main.o", "unused.h")})

    def test_shared_headers_macro_changes_only_corresponding_targets(self):
        _, report = self.make_target(split_targets=True)
        original = (self.project / "Makefile").read_text()
        expected = original.replace("main.o: main.c $(HEADERS)\n",
                                    "main.o: main.c $(HEADERS) config.h\n").replace(
                                    "helper.o: helper.c $(HEADERS)\n",
                                    "helper.o: helper.c $(HEADERS) extra.h\n")
        self.exercise_repair(report, expected, [
            {"target": "main.o", "dependency": "config.h", "style": "mixed"},
            {"target": "helper.o", "dependency": "extra.h", "style": "mixed"}],
            {("REDUNDANT", "main.o", "unused.h"), ("REDUNDANT", "helper.o", "unused.h")})

    def test_real_c0_report_rejected_after_c1_without_relabeling(self):
        old = scan(self.project)
        old_file = self.root / "original-c0-report.json"
        original = json_bytes(old)
        old_file.write_bytes(original)
        target, _ = self.make_target()
        self.assertNotEqual(old["commit"], target)
        before = source_bytes(self.project)
        with self.assertRaisesRegex(ValueError, "^STALE_REPORT$"):
            patch(self.project, old)
        self.assert_original(before, target)
        self.assertEqual(json_bytes(old), original)
        self.assertEqual(old_file.read_bytes(), original)
        self.assertFalse((self.root / "candidate.patch").exists())

    def test_later_unsafe_missing_record_cannot_partially_write_source(self):
        target, report = self.make_target()
        before = source_bytes(self.project)
        bad = copy.deepcopy(report)
        bad["findings"] = [
            {"type": "MISSING", "target": "main.o", "dependency": "config.h"},
            {"type": "MISSING", "target": "main.o", "dependency": "../outside.h"}]
        (self.root / "rejected-report.json").write_bytes(json_bytes(bad))
        with self.assertRaisesRegex(ValueError, "^UNSAFE_PATH$"):
            patch(self.project, bad)
        self.assert_original(before, target)
        self.assertFalse((self.root / "candidate.patch").exists())

    def test_duplicate_missing_records_add_each_header_once(self):
        target, report = self.make_target()
        before = source_bytes(self.project)
        duplicate = copy.deepcopy(report)
        duplicate["findings"] += copy.deepcopy(report["findings"])
        diff, plan = patch(self.project, duplicate)
        expected_diff, expected_plan = patch(self.project, report)
        self.assertEqual((diff, plan), (expected_diff, expected_plan))
        self.assertEqual(len(plan), 2)
        (self.root / "candidate.patch").write_text(diff, encoding="utf-8")
        self.assert_original(before, target)

    def delivery(self, folder, payload, target, mutate=None, tamper=None):
        folder.mkdir()
        payload = copy.deepcopy(payload)
        job, trace = "job-member2-mixed", "trace-member2-mixed"
        envelope = {"schema_version": "e11e12-1", "kind": "incremental-check",
                    "status": "SUCCEEDED", "commit": target, "job_id": job,
                    "trace_id": trace, "data": payload}
        if mutate:
            mutate(envelope, payload)
        raw = json_bytes(payload)
        payload_hash = hashlib.sha256(raw).hexdigest()
        envelope["artifacts"] = [{"uri": f"artifact://{job}/incremental-report.json",
                                  "sha256": payload_hash, "bytes": len(raw)}]
        envelope_raw = json_bytes(envelope)
        envelope_hash = hashlib.sha256(envelope_raw).hexdigest()
        env_file, payload_file = folder / "envelope.json", folder / "payload.json"
        env_file.write_bytes(envelope_raw + (b" " if tamper == "envelope" else b""))
        payload_file.write_bytes(raw + (b" " if tamper == "payload" else b""))
        return (env_file, envelope_hash, payload_file, payload_hash, target, job, trace)

    def test_received_mixed_report_keeps_both_original_byte_streams(self):
        target, report = self.make_target()
        args = self.delivery(self.root / "valid-delivery", report, target)
        before = source_bytes(self.project)
        received = verify_received(*args)
        self.assertEqual(received.envelope_bytes, args[0].read_bytes())
        self.assertEqual(received.payload_bytes, args[2].read_bytes())
        self.assertEqual(received.payload, report)
        self.assert_original(before, target)

    def test_independent_consumer_rejects_bad_inputs_without_any_source_write(self):
        target, report = self.make_target()
        before = source_bytes(self.project)
        cases = [
            ("outer-version", "STALE_REPORT", lambda e, p: e.update(commit=self.c0), None),
            ("inner-version", "STALE_REPORT", lambda e, p: p.update(commit=self.c0), None),
            ("outer-schema", "SCHEMA_MISMATCH", lambda e, p: e.update(schema_version="wrong"), None),
            ("inner-schema", "SCHEMA_MISMATCH", lambda e, p: p.update(schema_version="wrong"), None),
            ("kind", "ARTIFACT_TYPE_MISMATCH", lambda e, p: e.update(kind="fixed-md"), None),
            ("job", "JOB_ID_MISMATCH", lambda e, p: e.update(job_id="job-other"), None),
            ("trace", "TRACE_ID_MISMATCH", lambda e, p: e.update(trace_id="trace-other"), None),
            ("payload-hash", "ARTIFACT_HASH_MISMATCH", None, "payload"),
            ("envelope-hash", "ARTIFACT_HASH_MISMATCH", None, "envelope"),
            ("finding-type", "INVALID_REPORT", lambda e, p: p["findings"][0].update(type="UNKNOWN"), None)]
        outcomes = []
        for label, code, mutation, tamper in cases:
            with self.subTest(case=label):
                args = self.delivery(self.root / label, report, target, mutation, tamper)
                output = self.root / (label + "-must-not-exist")
                with self.assertRaises(Failure) as caught:
                    consume(args[0], args[1], args[2], args[3], self.project,
                            args[4], args[5], args[6], output,
                            source_label="course-generated-member2-test")
                self.assertEqual(caught.exception.code, code)
                self.assertFalse(output.exists(), "Rejected input created a repair workspace")
                self.assert_original(before, target)
                outcomes.append({"case": label, "expected": code, "actual": caught.exception.code})
        (self.root / "rejection-outcomes.json").write_bytes(json_bytes({"cases": outcomes}))


if __name__ == "__main__":
    unittest.main()
