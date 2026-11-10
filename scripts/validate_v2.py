"""B13 semantic validator for the Pair13 finding-report 2.0 candidate.

This is B13's independent implementation of the v2.0 rules proposed by A13 in
commit c4364e96521a8729fe11695c030916e1746eca1b. It intentionally does not
import A13's validator: the cross-group review value comes from a second,
independent reading of the same written rules.

Rules verified here mirror `contracts/paired/a13-v2/schemas/pair13-finding-report-v2.schema.json`
plus the semantic constraints documented in A13's
`docs/E2/B13_REVIEW_RESPONSE_2026-10-10.md`:
  - producer_job_id is required for real detector output (BUILDCHECKER/ECHECKER)
    and must be null/absent for oracle/manual reports;
  - a finding-level commit/configuration_id, when present, must equal the
    top-level values;
  - UNRESOLVED locations carry a reason only (no path/line/declaration);
  - RESOLVED locations carry a safe relative path and a positive line number;
  - core objects are closed; extensions must be namespaced a13./b13./pair13..

findings may be an empty array (a post-repair report with zero MD is valid).
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
JOB_ID = re.compile(r"^job-[A-Za-z0-9-]+$")
EXTENSION_KEY = re.compile(r"^(a13|b13|pair13)\.[A-Za-z0-9_.-]+$")
ARTIFACT_URI = re.compile(r"^artifact://pair13/")

DETECTORS = {"BUILDCHECKER", "ECHECKER", "INSTRUCTOR_ORACLE", "A13_MANUAL_ORACLE", "B13_MANUAL_ORACLE"}
REAL_DETECTORS = {"BUILDCHECKER", "ECHECKER"}

TOP_LEVEL_FIELDS = {
    "schema_version", "report_id", "repository", "configuration_id",
    "environment", "detector", "provenance", "producer_job_id",
    "findings", "artifact_locator", "extensions",
}
REPOSITORY_FIELDS = {"url", "commit"}
ENVIRONMENT_FIELDS = {"os", "arch", "make_version", "cc_version", "image_ref"}
FINDING_FIELDS = {
    "finding_id", "type", "target", "dependency", "commit",
    "configuration_id", "location", "evidence", "extensions",
}
RESOLVED_FIELDS = {"status", "path", "line", "declaration"}
UNRESOLVED_FIELDS = {"status", "reason"}
EVIDENCE_FIELDS = {"kind", "detail", "uri"}
LOCATOR_FIELDS = {"uri", "repository_url", "repository_commit", "repository_path", "sha256"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_safe_path(value: Any) -> bool:
    """Safe project-relative POSIX path: no absolute, no drive, no backslash,
    no ./ prefix, no empty/./.. segments."""
    if (
        not _nonempty(value)
        or "\\" in value
        or value.startswith("/")
        or value.startswith("./")
        or re.match(r"^[A-Za-z]:", value)
    ):
        return False
    parts = PurePosixPath(value).parts
    return all(part not in {"", ".", ".."} for part in parts) and bool(parts)


def _unknown_fields(obj: dict[str, Any], allowed: set[str], where: str, errors: list[str]) -> None:
    extra = sorted(set(obj) - allowed)
    if extra:
        errors.append(f"{where}: unknown core fields {extra}")


def _validate_extensions(value: Any, where: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{where}: object required")
        return
    for key in value:
        if not EXTENSION_KEY.fullmatch(key):
            errors.append(
                f"{where}: keys must be namespaced a13.*/b13.*/pair13.* (got {key!r})"
            )


def _validate_locator(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("artifact_locator: object required")
        return
    _unknown_fields(value, LOCATOR_FIELDS, "artifact_locator", errors)
    for key in ("uri", "repository_url", "repository_commit", "repository_path", "sha256"):
        if key not in value:
            errors.append(f"artifact_locator.{key}: missing required field")
    uri = value.get("uri")
    if _nonempty(uri) and not ARTIFACT_URI.search(uri):
        errors.append("artifact_locator.uri: must start with artifact://pair13/")
    if not _nonempty(value.get("repository_url")):
        errors.append("artifact_locator.repository_url: non-empty string required")
    commit = value.get("repository_commit")
    if not isinstance(commit, str) or not SHA40.fullmatch(commit):
        errors.append("artifact_locator.repository_commit: 40-hex required")
    if not is_safe_path(value.get("repository_path")):
        errors.append("artifact_locator.repository_path: expected safe project-relative POSIX path")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        errors.append("artifact_locator.sha256: 64-hex required")


def validate_report_v2(data: Any) -> list[str]:
    """Return a list of semantic errors; empty list means the report is valid."""
    if not isinstance(data, dict):
        return ["root: expected object"]
    errors: list[str] = []

    _unknown_fields(data, TOP_LEVEL_FIELDS, "root", errors)
    for key in (
        "schema_version", "report_id", "repository", "configuration_id",
        "environment", "detector", "provenance", "findings",
    ):
        if key not in data:
            errors.append(f"{key}: missing required field")

    if data.get("schema_version") != "2.0":
        errors.append("schema_version: expected 2.0")
    if not _nonempty(data.get("report_id")):
        errors.append("report_id: non-empty string required")
    if not _nonempty(data.get("configuration_id")):
        errors.append("configuration_id: non-empty string required")
    if not _nonempty(data.get("provenance")):
        errors.append("provenance: non-empty string required")

    repository = data.get("repository")
    if not isinstance(repository, dict):
        errors.append("repository: object required")
    else:
        _unknown_fields(repository, REPOSITORY_FIELDS, "repository", errors)
        if not _nonempty(repository.get("url")):
            errors.append("repository.url: non-empty string required")
        commit = repository.get("commit")
        if not isinstance(commit, str) or not SHA40.fullmatch(commit):
            errors.append("repository.commit: 40-hex SHA required")

    environment = data.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment: object required")
    else:
        _unknown_fields(environment, ENVIRONMENT_FIELDS, "environment", errors)
        for key in ("os", "arch"):
            if not _nonempty(environment.get(key)):
                errors.append(f"environment.{key}: non-empty string required")
        for key in ("make_version", "cc_version", "image_ref"):
            if key in environment and not _nonempty(environment[key]):
                errors.append(f"environment.{key}: non-empty string required when present")

    detector = data.get("detector")
    if detector not in DETECTORS:
        errors.append("detector: must be one of " + "/".join(sorted(DETECTORS)))

    job_id = data.get("producer_job_id")
    if detector in REAL_DETECTORS:
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            errors.append("producer_job_id: real detector output requires a job-* id")
    elif job_id is not None:
        errors.append("producer_job_id: oracle/manual reports must not carry producer_job_id")

    findings = data.get("findings")
    if not isinstance(findings, list):
        if "findings" in data:
            errors.append("findings: array required")
        return errors + _close_top(data)

    top_commit = repository.get("commit") if isinstance(repository, dict) else None
    for index, finding in enumerate(findings):
        where = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{where}: object required")
            continue
        _unknown_fields(finding, FINDING_FIELDS, where, errors)
        if not _nonempty(finding.get("finding_id")):
            errors.append(f"{where}.finding_id: non-empty string required")
        if finding.get("type") not in {"MISSING", "REDUNDANT"}:
            errors.append(f"{where}.type: must be MISSING or REDUNDANT")
        if not _nonempty(finding.get("target")):
            errors.append(f"{where}.target: non-empty string required")
        if not is_safe_path(finding.get("dependency")):
            errors.append(f"{where}.dependency: expected safe project-relative POSIX path")
        if "commit" in finding and finding["commit"] != top_commit:
            errors.append(f"{where}.commit: must equal repository.commit when present")
        if "configuration_id" in finding and finding["configuration_id"] != data.get("configuration_id"):
            errors.append(f"{where}.configuration_id: must equal top-level configuration_id when present")

        location = finding.get("location")
        if not isinstance(location, dict):
            errors.append(f"{where}.location: object required")
        elif location.get("status") == "RESOLVED":
            _unknown_fields(location, RESOLVED_FIELDS, f"{where}.location", errors)
            if not is_safe_path(location.get("path")):
                errors.append(f"{where}.location.path: expected safe project-relative POSIX path")
            line = location.get("line")
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                errors.append(f"{where}.location.line: positive integer required")
            if "declaration" in location and not _nonempty(location["declaration"]):
                errors.append(f"{where}.location.declaration: non-empty string required when present")
        elif location.get("status") == "UNRESOLVED":
            _unknown_fields(location, UNRESOLVED_FIELDS, f"{where}.location", errors)
            if not _nonempty(location.get("reason")):
                errors.append(f"{where}.location.reason: non-empty string required")
        else:
            errors.append(f"{where}.location.status: must be RESOLVED or UNRESOLVED")

        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{where}.evidence: non-empty array required")
        else:
            for j, item in enumerate(evidence):
                if not isinstance(item, dict):
                    errors.append(f"{where}.evidence[{j}]: object required")
                    continue
                _unknown_fields(item, EVIDENCE_FIELDS, f"{where}.evidence[{j}]", errors)
                if not _nonempty(item.get("kind")):
                    errors.append(f"{where}.evidence[{j}].kind: non-empty string required")
                if not _nonempty(item.get("detail")):
                    errors.append(f"{where}.evidence[{j}].detail: non-empty string required")
                if "uri" in item:
                    uri = item["uri"]
                    if not isinstance(uri, str) or not ARTIFACT_URI.search(uri):
                        errors.append(f"{where}.evidence[{j}].uri: must start with artifact://pair13/")

        _validate_extensions(finding.get("extensions"), f"{where}.extensions", errors)

    return errors + _close_top(data)


def _close_top(data: dict[str, Any]) -> list[str]:
    """Validate the remaining top-level optional containers; returns fresh errors."""
    extra: list[str] = []
    _validate_extensions(data.get("extensions"), "extensions", extra)
    if "artifact_locator" in data:
        _validate_locator(data.get("artifact_locator"), extra)
    return extra


def validate_report_file(path: Path) -> list[str]:
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{path}: unreadable JSON ({exc})"]
    return validate_report_v2(data)


def consume_missing_v2(
    data: Any, default_makefile: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Apply the MDFixer consumption policy to a v2 report.

    MISSING findings are consumed; REDUNDANT findings are skipped. A MISSING
    finding whose location is UNRESOLVED requires an explicit default Makefile
    path from the caller (the report must not fabricate one).
    """
    errors = validate_report_v2(data)
    if errors:
        raise ValueError("invalid v2 report: " + "; ".join(errors[:3]))

    consumed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for finding in data["findings"]:
        entry = {
            "finding_id": finding["finding_id"],
            "type": finding["type"],
            "target": finding["target"],
            "dependency": finding["dependency"],
        }
        if finding["type"] != "MISSING":
            skipped.append(entry)
            continue
        location = finding["location"]
        if location["status"] == "RESOLVED":
            entry["makefile_path"] = location["path"]
            entry["line"] = location["line"]
        else:
            if not default_makefile:
                raise ValueError(
                    "default_makefile: required for MISSING findings with UNRESOLVED location"
                )
            entry["makefile_path"] = default_makefile
            entry["unresolved_reason"] = location["reason"]
        consumed.append(entry)
    return {"consumed_findings": consumed, "skipped_findings": skipped}
