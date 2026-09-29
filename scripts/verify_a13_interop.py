"""Verify the pinned A13 contract artifacts and normalize MDFixer input.

The pinned A13 files are explicitly synthetic E2 examples. This verifier
checks cross-repository readability and consumer semantics; it never reports
that BuildChecker or EChecker executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "contracts" / "paired" / "a13"
SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
JOB_ID = re.compile(r"^job-[A-Za-z0-9-]+$")
A13_REPOSITORY = "https://github.com/Dufunare/2026-Devops-A13"
A13_COMMIT = "bc1ed352dc0b8ff9e77a69222a69deb03e49a618"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_project_path(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or value.startswith(("/", "./"))
        or re.match(r"^[A-Za-z]:", value)
    ):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def validate_native_report(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root: expected object"]
    for key in ("schema_version", "repository", "configuration_id", "producer_job_id", "findings"):
        if key not in data:
            errors.append(f"{key}: missing required field")
    if data.get("schema_version") != "1.0":
        errors.append("schema_version: expected 1.0")
    repository = data.get("repository")
    if not isinstance(repository, dict):
        errors.append("repository: expected object")
        repository = {}
    if not isinstance(repository.get("url"), str) or not repository.get("url"):
        errors.append("repository.url: expected non-empty string")
    commit = repository.get("commit")
    if not isinstance(commit, str) or not SHA40.fullmatch(commit):
        errors.append("repository.commit: expected full 40-hex SHA")
    configuration = data.get("configuration_id")
    if not isinstance(configuration, str) or not configuration:
        errors.append("configuration_id: expected non-empty string")
    producer = data.get("producer_job_id")
    if not isinstance(producer, str) or not JOB_ID.fullmatch(producer):
        errors.append("producer_job_id: expected job- identifier")
    findings = data.get("findings")
    if not isinstance(findings, list):
        errors.append("findings: expected array")
        return errors
    for index, finding in enumerate(findings):
        path = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{path}: expected object")
            continue
        for key in ("finding_id", "type", "target", "dependency", "commit", "configuration_id", "location", "evidence"):
            if key not in finding:
                errors.append(f"{path}.{key}: missing required field")
        if finding.get("type") not in {"MISSING", "REDUNDANT"}:
            errors.append(f"{path}.type: unsupported value")
        for key in ("target", "dependency"):
            if not is_project_path(finding.get(key)):
                errors.append(f"{path}.{key}: expected project-relative POSIX path")
        if finding.get("commit") != commit:
            errors.append(f"{path}.commit: does not match repository.commit")
        if finding.get("configuration_id") != configuration:
            errors.append(f"{path}.configuration_id: does not match report")
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{path}.evidence: expected non-empty array")
        location = finding.get("location")
        if not isinstance(location, dict):
            errors.append(f"{path}.location: expected object")
            continue
        status = location.get("status")
        if status == "RESOLVED":
            if not is_project_path(location.get("path")):
                errors.append(f"{path}.location.path: expected project-relative POSIX path")
            if type(location.get("line")) is not int or location["line"] < 1:
                errors.append(f"{path}.location.line: expected positive integer")
        elif status == "UNRESOLVED":
            if not isinstance(location.get("reason"), str) or not location["reason"].strip():
                errors.append(f"{path}.location.reason: expected non-empty string")
        else:
            errors.append(f"{path}.location.status: unsupported value")
    return errors


def validate_locator(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    locator = data.get("artifact_locator")
    if not isinstance(locator, dict):
        return ["artifact_locator: expected object"]
    if not str(locator.get("uri", "")).startswith("artifact://pair13/"):
        errors.append("artifact_locator.uri: invalid logical URI")
    if locator.get("repository_url") != A13_REPOSITORY:
        errors.append("artifact_locator.repository_url: unexpected repository")
    if not is_project_path(locator.get("repository_path")):
        errors.append("artifact_locator.repository_path: expected repository-relative POSIX path")
    if not isinstance(locator.get("repository_ref"), str) or not locator["repository_ref"]:
        errors.append("artifact_locator.repository_ref: expected non-empty ref")
    return errors


def normalize_missing(data: dict[str, Any], *, default_makefile: str | None = None) -> dict[str, Any]:
    issues = validate_native_report(data) + validate_locator(data)
    if default_makefile is not None and not is_project_path(default_makefile):
        issues.append("default_makefile: expected project-relative POSIX path")
    if issues:
        raise ValueError("; ".join(issues))
    consumed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for finding in data["findings"]:
        if finding["type"] != "MISSING":
            skipped.append(
                {
                    "finding_id": finding["finding_id"],
                    "type": finding["type"],
                    "target": finding["target"],
                    "dependency": finding["dependency"],
                    "reason": "MDFixer consumes MISSING findings only",
                }
            )
            continue
        location = finding["location"]
        if location["status"] == "RESOLVED":
            makefile_path = location["path"]
            line = location["line"]
        else:
            if default_makefile is None:
                raise ValueError(f"{finding['finding_id']}: unresolved location requires default_makefile")
            makefile_path = default_makefile
            line = None
        evidence = "; ".join(
            f"[{item.get('kind', 'UNKNOWN')}] {item.get('detail', '')}" for item in finding["evidence"]
        )
        consumed.append(
            {
                "finding_id": finding["finding_id"],
                "type": "MISSING",
                "target": finding["target"],
                "dependency": finding["dependency"],
                "makefile_path": makefile_path,
                "location_status": location["status"],
                "location_line": line,
                "evidence": evidence,
            }
        )
    manifest = read_json(SNAPSHOT / "manifest.json")
    return {
        "schema_version": "1.0",
        "source": {
            "repository": manifest["source_repository"],
            "commit": manifest["source_commit"],
            "producer_job_id": data["producer_job_id"],
            "artifact_uri": data["artifact_locator"]["uri"],
            "synthetic_contract_sample": True,
        },
        "repository": data["repository"],
        "configuration_id": data["configuration_id"],
        "consumed_findings": consumed,
        "skipped_findings": skipped,
    }


def edge_set(data: dict[str, Any]) -> set[tuple[str, str]]:
    edges = data.get("edges")
    if not isinstance(edges, list):
        raise ValueError("edges: expected array")
    result: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict) or not is_project_path(edge.get("target")) or not is_project_path(edge.get("dependency")):
            raise ValueError("edges: invalid project-relative edge")
        result.add((edge["target"], edge["dependency"]))
    return result


def run_checks() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(check_id: str, condition: bool, detail: Any) -> None:
        checks.append({"id": check_id, "status": "PASS" if condition else "FAIL", "detail": detail})

    manifest = read_json(SNAPSHOT / "manifest.json")
    check("source.repository", manifest.get("source_repository") == A13_REPOSITORY, manifest.get("source_repository"))
    check("source.commit", manifest.get("source_commit") == A13_COMMIT, manifest.get("source_commit"))
    for entry in manifest.get("files", []):
        path = SNAPSHOT / entry["snapshot_path"]
        digest = sha256(path) if path.is_file() else None
        check(
            f"snapshot.{entry['snapshot_path']}",
            path.is_file()
            and bool(SHA256.fullmatch(str(entry.get("upstream_sha256", ""))))
            and digest == entry.get("snapshot_sha256"),
            {
                "snapshot_sha256": digest,
                "expected_snapshot_sha256": entry.get("snapshot_sha256"),
                "upstream_sha256": entry.get("upstream_sha256"),
            },
        )

    full_root = SNAPSHOT / "artifacts" / "job-full-a13-001"
    incremental_root = SNAPSHOT / "artifacts" / "job-incremental-a13-001"
    actual = read_json(full_root / "actual.json")
    declared = read_json(full_root / "declared.json")
    full_report = read_json(full_root / "md-report.json")
    incremental_actual = read_json(incremental_root / "actual.json")
    incremental_report = read_json(incremental_root / "md-report.json")

    for name, report in (("full", full_report), ("incremental", incremental_report)):
        issues = validate_native_report(report) + validate_locator(report)
        check(f"{name}.native-report", not issues, issues or "valid")
        check(
            f"{name}.synthetic-label",
            str(report.get("note", "")).startswith("Synthetic E2 artifact"),
            report.get("note"),
        )

    actual_edges = edge_set(actual)
    declared_edges = edge_set(declared)
    expected = {
        ("MISSING", target, dependency) for target, dependency in actual_edges - declared_edges
    } | {
        ("REDUNDANT", target, dependency) for target, dependency in declared_edges - actual_edges
    }
    reported = {(item["type"], item["target"], item["dependency"]) for item in full_report["findings"]}
    check("full.graph-diff", reported == expected, {"expected": sorted(expected), "reported": sorted(reported)})
    check(
        "incremental.actual-graph",
        ("main.o", "feature.h") in edge_set(incremental_actual),
        sorted(edge_set(incremental_actual)),
    )

    normalized_full = normalize_missing(full_report)
    normalized_incremental = normalize_missing(incremental_report, default_makefile="Makefile")
    check(
        "full.missing-only",
        [item["dependency"] for item in normalized_full["consumed_findings"]] == ["config.h"]
        and [item["dependency"] for item in normalized_full["skipped_findings"]] == ["unused.h"],
        normalized_full,
    )
    check(
        "incremental.unresolved-location",
        normalized_incremental["consumed_findings"][0]["dependency"] == "feature.h"
        and normalized_incremental["consumed_findings"][0]["makefile_path"] == "Makefile"
        and normalized_incremental["consumed_findings"][0]["location_line"] is None,
        normalized_incremental,
    )
    return checks, normalized_full, normalized_incremental


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional evidence output directory")
    args = parser.parse_args()
    checks, normalized_full, normalized_incremental = run_checks()
    result = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    summary = {
        "schema_version": "1.0",
        "suite": "E3",
        "case": "a13-contract-interop",
        "result": result,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {"repository": A13_REPOSITORY, "commit": A13_COMMIT, "kind": "synthetic E2 contract artifacts"},
        "checks": checks,
    }
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "normalized-full.json").write_text(
            json.dumps(normalized_full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (args.output / "normalized-incremental.json").write_text(
            json.dumps(normalized_incremental, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (args.output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    for item in checks:
        print(f"[{item['status']}] {item['id']}")
    print(f"A13 contract interoperability: {result}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
