"""Check one B13 normal run from real shared Compose role logs and worker files."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def load(path):
    return json.loads(path.read_bytes())


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def check(root):
    matrix_path, = root.glob("matrix-*.json")
    matrix = load(matrix_path)
    require(matrix["scope"] == "B13_SHARED_COMPOSE_RUN" and matrix["status"] == "PASS", "shared matrix required")
    row, = matrix["records"]
    result = row["result"]
    require(result["status"] == "PASS" and row["scenario"] == "normal", "successful normal chain required")
    job = root / "jobs" / result["job_id"]
    image = load(job / "draft" / "binding.json")["image_id"]
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image) and image == result["image_id"], "DRAFT image differs")
    seen = Counter()
    for role in ("draft", "buildchecker", "echecker", "mdfixer"):
        for line in (root / "diagnostics" / (role + ".log")).read_text().splitlines():
            if not line.startswith("{"):
                continue
            record = json.loads(line)
            if record.get("job_id") != result["job_id"]:
                continue
            require(record["trace_id"] == result["trace_id"] and record["role"] == role, "log identity differs")
            require(record["protocol"] == "member2-e14-1" and record["status"] == "SUCCEEDED"
                    and record["http_status"] == 200 and record["error_code"] is None, "role operation failed")
            require(isinstance(record["elapsed_ms"], int) and record["elapsed_ms"] >= 0, "missing elapsed time")
            seen[role, record["endpoint"], record["stage"]] += 1
    expected = {
        ("draft", "/v1/run", "draft"): 1, ("buildchecker", "/v1/run", "full"): 3,
        ("echecker", "/v1/run", "scan"): 1, ("mdfixer", "/v1/run", "validate"): 1,
        ("draft", "/v1/worker", "full"): 3, ("draft", "/v1/worker", "scan"): 2,
        ("draft", "/v1/worker", "validate"): 1,
    }
    require(dict(seen) == expected, f"incomplete four-role or delegated chain: {dict(seen)}")
    operations = Counter()
    for witness_file in job.rglob("execution.json"):
        runtime = witness_file.parent
        witness = load(witness_file)
        cleanup = load(runtime / "cleanup.json")
        require(witness["image_id"] == witness["actual_container_image"] == image
                and witness["container_exit_code"] == 0 and witness["input_source_sha256"], "worker witness mismatch")
        require(cleanup["verified_no_owned_containers"] and witness["container_id"] in cleanup["removed"],
                "worker cleanup not proven")
        response = load(runtime / "output" / "response.json")
        require(all(response["tools"].get(k) for k in ("python3", "git", "gcc", "make", "strace")), "missing tool version")
        operations[witness["operation"]] += 1
    require(dict(operations) == {"full": 3, "scan": 2, "validate": 1}, "missing worker execution")
    increment = job / "incremental"
    request_file, = (job / "http").glob("*-repair-request.json")
    request = load(request_file)
    for field, name in (("report", "incremental-check.json"), ("payload", "incremental-report.json")):
        require(request[field + "_sha256"] == hashlib.sha256((increment / name).read_bytes()).hexdigest(),
                "MDFixer did not receive the original " + field)
    findings = load(job / "final-full" / "findings.json")
    require(findings["findings"] == findings["whole_project_findings"] and findings["findings_by_scope"]["in_scope_missing"] == 0
            and findings["findings_by_scope"]["out_of_scope_missing"] == 0, "unexpected B13 final findings")
    return {"status": "PASS", "project_id": "b13-level-v1", "job_id": result["job_id"],
            "trace_id": result["trace_id"], "implementation_sha": result["implementation_sha"], "image_id": image,
            "operations": dict(operations), "whole_project_findings": findings["whole_project_findings"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    print(json.dumps(check(parser.parse_args().run), indent=2))
