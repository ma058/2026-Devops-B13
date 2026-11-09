"""Member 1 evidence driver for the B-track manual E8/E9/E10 route.

Calls the distributed lab implementation without copying its algorithms.
Run in the teaching Linux container with a new --out directory. The caller
records the outer student-source commit and environment image ID separately.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import traceback

from lab import buildchecker, commit, fixture, patch, run, save, scan, validate


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_bytes(project):
    names = run(["git", "ls-files"], project).splitlines()
    return {name: (project / name).read_bytes() for name in names}


def snapshot(project, destination):
    data = source_bytes(project)
    for name, content in data.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    save(destination / "sha256.json", {
        name: hashlib.sha256(content).hexdigest() for name, content in data.items()
    })
    return data


def fixed_input(project, path):
    report = scan(project)
    save(path, report)
    expected = {("MISSING", "main.o", "config.h"),
                ("REDUNDANT", "main.o", "unused.h")}
    actual = {(item["type"], item["target"], item["dependency"])
              for item in report["findings"]}
    require(actual == expected and len(report["findings"]) == 2,
            "Fixed input must contain exactly the independently expected MD and RD")
    require(report["commit"] == run(["git", "rev-parse", "HEAD"], project).strip(),
            "Fixed input version mismatch")
    return report


def candidate(project, report, diff_path, plan_path, style):
    before = source_bytes(project)
    diff, plan = patch(project, report)
    diff_path.write_text(diff, encoding="utf-8")
    save(plan_path, plan)
    require(plan == [{"target": "main.o", "dependency": "config.h", "style": style}],
            "Unexpected candidate plan")
    require(source_bytes(project) == before, "Candidate generation changed source")
    output = run(["git", "apply", "--check", str(diff_path.resolve())], project)
    diff_path.with_suffix(".apply-check.log").write_text(output, encoding="utf-8")
    require(not run(["git", "status", "--porcelain"], project).strip(),
            "Candidate input is not clean")
    return diff, plan


def e8(out):
    project = out / "project"
    fixture(project)
    before = snapshot(project, out / "source-before")
    report = fixed_input(project, out / "fixed-md-report.json")
    diff, plan = candidate(project, report, out / "candidate.patch",
                           out / "patch-plan.json", "direct")
    require("+main.o: main.c unused.h config.h\n" in diff, "Wrong direct patch")
    require(source_bytes(project) == before, "E8 source changed")
    snapshot(project, out / "source-after")
    # A second isolated fixture supplies a real historical commit, not a fake SHA.
    stale_project = out / "stale-project"
    fixture(stale_project)
    stale_report = fixed_input(stale_project, out / "stale-input-report.json")
    (stale_project / "version-marker.txt").write_text("New version for stale-report rejection\n")
    current = commit(stale_project, "C1 real version change for stale input test")
    require(current != stale_report["commit"], "Stale case must use two real commits")
    stale_before = snapshot(stale_project, out / "stale-source-before")
    try:
        patch(stale_project, stale_report)
    except ValueError as error:
        require(str(error) == "STALE_REPORT", "Wrong stale-report rejection reason")
        rejected = {"error": str(error), "report_commit": stale_report["commit"],
                    "current_commit": current}
    else:
        raise AssertionError("Historical report was accepted against a later commit")
    require(source_bytes(stale_project) == stale_before, "Stale rejection changed source")
    save(out / "expected-failure.json", rejected)
    snapshot(stale_project, out / "stale-source-after")
    (out / "conclusion.txt").write_text(
        "Candidate adds config.h only; RD and recipes are preserved. Original input is clean.\n"
        "Historical report from a real earlier commit is rejected without source changes.\n"
        "Patch applicability is not build/test acceptance; see E10.\n", encoding="utf-8")
    return {"fixture_commit": report["commit"], "style": plan[0]["style"],
            "stale_report_rejection": rejected, "source_unchanged": source_bytes(project) == before}


def e9(out):
    rows = []
    for style in ("direct", "macro", "mixed"):
        project = out / style
        fixture(project, style)
        before = snapshot(project, out / (style + "-source-before"))
        report = fixed_input(project, out / (style + "-input.json"))
        diff, plan = candidate(project, report, out / (style + ".patch"),
                               out / (style + "-plan.json"), style)
        expected = {"direct": "+main.o: main.c unused.h config.h\n",
                    "macro": "+DEPS = main.c unused.h config.h\n",
                    "mixed": "+main.o: main.c $(HEADERS) config.h\n"}[style]
        require(expected in diff, "Wrong repair placement for " + style)
        require(source_bytes(project) == before, "E9 source changed")
        snapshot(project, out / (style + "-source-after"))
        rows.append({"style": style, "fixture_commit": report["commit"],
                     "source_unchanged": source_bytes(project) == before})
    source, copy = out / "macro", out / "apply-demo"
    shutil.copytree(source, copy, ignore=shutil.ignore_patterns(".git"))
    run(["git", "init", "-b", "main"], copy)
    candidate_path = str((out / "macro.patch").resolve())
    run(["git", "apply", "--check", candidate_path], copy)
    run(["git", "apply", candidate_path], copy)
    applied = (copy / "Makefile").read_text()
    require("DEPS = main.c unused.h config.h\n" in applied and "main.o: $(DEPS)\n" in applied,
            "Applied macro candidate lost its declaration structure")
    require("config.h" not in (source / "Makefile").read_text(), "Apply-demo changed source")
    (out / "conclusion.txt").write_text(
        "direct changes the target line; macro changes DEPS; mixed retains HEADERS and changes the target line.\n"
        "All source inputs remain clean. apply-demo is a separate copy.\n"
        "Shared variables may affect other targets; complex/implicit Make syntax is outside this profile.\n",
        encoding="utf-8")
    save(out / "styles.json", rows)
    return {"styles": rows, "apply_demo": "macro.patch applied to an isolated copy"}


def e10(out):
    project = out / "project"
    fixture(project)
    original = snapshot(project, out / "before-test-rejection")
    (out / "source-before.Makefile").write_bytes(original["Makefile"])
    report = fixed_input(project, out / "fixed-md-report.json")
    candidate(project, report, out / "candidate.patch", out / "patch-plan.json", "direct")
    rejected = validate(project, out / "candidate.patch", out / "reject-test", fail_test=True)
    require(not rejected["accepted"] and rejected["checks"].get("test") is False,
            "Wrong test expectation was not rejected")
    require(rejected["checks"].get("build") is True and rejected["error"] is None,
            "Test-rejection case failed for an unrelated reason")
    require(rejected["rollback"] and rejected["source_unchanged"] and source_bytes(project) == original,
            "Test rejection changed source")
    snapshot(project, out / "after-test-rejection")
    snapshot(project, out / "before-accept")
    accepted = validate(project, out / "candidate.patch", out / "accept")
    expected_checks = {"patch_applies", "build", "test", "header_change", "no_missing"}
    require(accepted["accepted"] and set(accepted["checks"]) == expected_checks
            and all(accepted["checks"].values()) and accepted["error"] is None,
            "Valid repair failed full acceptance")
    require(not accepted["rollback"] and not accepted["source_unchanged"], "Wrong accepted state")
    repaired = snapshot(project, out / "after-accept")
    require({name for name in original if original[name] != repaired[name]} == {"Makefile"},
            "Acceptance changed files other than Makefile")
    require("main.o: main.c unused.h config.h\n" in (project / "Makefile").read_text(),
            "Accepted Makefile does not contain repair")
    require((project / "config.h").read_text() == "#define VALUE 1\n"
            and (out / "accept/sandbox/config.h").read_text() == "#define VALUE 2\n",
            "Header mutation escaped sandbox or did not run")
    (out / "source-after-accept.Makefile").write_bytes(repaired["Makefile"])
    snapshot(project, out / "before-patch-rejection")
    (out / "broken.patch").write_text("invalid patch\n")
    rejected_patch = validate(project, out / "broken.patch", out / "reject-patch")
    require(not rejected_patch["accepted"] and rejected_patch["rollback"]
            and rejected_patch["source_unchanged"] and rejected_patch["error"]
            and source_bytes(project) == repaired, "Bad patch damaged accepted source")
    snapshot(project, out / "after-patch-rejection")
    dynamic = buildchecker(project, out / "recheck-buildchecker")
    require(not any(f["type"] == "MISSING" for f in dynamic["findings"]),
            "Real BuildChecker recheck still contains MD")
    trace_files = [p for p in (out / "recheck-buildchecker").rglob("t.*") if p.is_file()]
    require(trace_files, "Real dynamic recheck did not save strace files")
    require(source_bytes(project) == repaired, "Dynamic recheck changed tracked source")
    rows = [{"case": "test-rejection", "passed": bool(rejected["rollback"]
             and rejected["source_unchanged"] and not rejected["accepted"])},
            {"case": "accepted", "passed": bool(accepted["accepted"])},
            {"case": "patch-rejection", "passed": bool(rejected_patch["rollback"]
             and rejected_patch["source_unchanged"] and not rejected_patch["accepted"])}]
    with (out / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case", "passed"])
        writer.writeheader()
        writer.writerows(rows)
    save(out / "gate.json", {"track": "B", "passed": all(row["passed"] for row in rows), "rows": len(rows)})
    (out / "conclusion.txt").write_text(
        "Wrong test expectation rejected; correct candidate accepted; invalid patch rejected.\n"
        "Only accepted Makefile is written back. Header mutation remains in sandbox.\n"
        "Real BuildChecker/strace recheck confirms no missing dependencies. RD is not removed.\n",
        encoding="utf-8")
    return {"fixture_commit": report["commit"], "rows": rows, "strace_file_count": len(trace_files),
            "dynamic_findings": dynamic["findings"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("--out must not already exist; preserve previous evidence")
    out.mkdir(parents=True)
    summary = {"track": "B", "passed": False, "stages": {},
               "scope": "Member1 orchestration of the distributed teaching implementation"}
    current = None
    try:
        for current, operation in (("e8", e8), ("e9", e9), ("e10", e10)):
            print("RUNNING " + current, flush=True)
            stage = out / current
            stage.mkdir()
            summary["stages"][current] = operation(stage)
            print("PASS " + current, flush=True)
        summary["passed"] = len(summary["stages"]) == 3
        return 0 if summary["passed"] else 1
    except Exception as error:
        summary["failed_stage"] = current
        summary["error"] = str(error)
        (out / "failure.log").write_text(traceback.format_exc(), encoding="utf-8")
        print("FAILED " + str(current) + ": " + str(error), flush=True)
        return 1
    finally:
        save(out / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
