#!/usr/bin/env python3
"""Run member 2's first mixed/rejection test batch and retain all fixtures."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.out.resolve()
    work = (root / "work").resolve()
    if work not in output.parents or output.exists():
        parser.error("Use a new output directory below this repository's work/")
    output.mkdir(parents=True, exist_ok=False)
    code = root / "labs/e11e12/test_member2_e11e12.py"
    summary = {"scope": "Member2 mixed integration and rejection tests; no DRAFT reuse claim",
               "test_file_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
               "status": "RUNNING"}
    try:
        missing = [name for name in ("git", "gcc", "make", "strace") if shutil.which(name) is None]
        if os.name != "posix" or missing:
            raise RuntimeError("ENVIRONMENT_ERROR: use the Linux orchestrator image; missing=" + repr(missing))
        os.environ["M2_E11E12_TEST_OUT"] = str(output / "cases")
        sys.path.insert(0, str(root / "labs/e11e12"))
        spec = importlib.util.spec_from_file_location("member2_e11e12_batch", code)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        summary.update(status="PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
                       tests_run=result.testsRun, skipped=result.skipped,
                       failures=[{"test": str(test), "traceback": trace} for test, trace in result.failures],
                       errors=[{"test": str(test), "traceback": trace} for test, trace in result.errors])
    except Exception as exc:
        summary.update(status="ENVIRONMENT_OR_RUNNER_ERROR", error=repr(exc))
    finally:
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
