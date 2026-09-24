"""Validate the E2 example contracts using only the Python standard library.

This is a focused course-contract validator, not a general JSON Schema engine.
It mirrors the constraints in contracts/schemas/ and adds cross-field checks.
The A13-owned service fields are provisional until pair review.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts" / "schemas"
EXAMPLES = ROOT / "contracts" / "examples"
SHA = re.compile(r"^[0-9a-fA-F]{40}$")
JOB_ID = re.compile(r"^job-[A-Za-z0-9-]+$")


def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


CREATE_SCHEMA = _schema("create-job.schema.json")
JOB_SCHEMA = _schema("job.schema.json")
ARTIFACT_SCHEMA = _schema("artifact.schema.json")
JOB_TYPES = set(CREATE_SCHEMA["properties"]["job_type"]["enum"])
STATUSES = set(JOB_SCHEMA["properties"]["status"]["enum"])


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _field_object(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict) or not value:
        errors.append(f"{path}.{key}: expected non-empty object")
        return {}
    return value


def _required(data: dict[str, Any], names: list[str], path: str, errors: list[str]) -> None:
    for name in names:
        if name not in data:
            errors.append(f"{path}.{name}: missing required field")


def _string(data: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    if not _nonempty(data.get(key)):
        errors.append(f"{path}.{key}: expected non-empty string")


def _sha(data: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not SHA.fullmatch(value):
        errors.append(f"{path}.{key}: expected full 40-hex commit SHA")


def _uri(data: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not value.startswith("artifact://pair13/"):
        errors.append(f"{path}.{key}: expected artifact://pair13/ URI")


def _repository(input_data: dict[str, Any], errors: list[str], *, require_url: bool) -> dict[str, Any]:
    repository = _field_object(input_data, "repository", "input", errors)
    if require_url:
        _string(repository, "url", "input.repository", errors)
    _sha(repository, "commit", "input.repository", errors)
    return repository


def validate_draft_input(data: dict[str, Any], errors: list[str]) -> None:
    files = data.get("context_files")
    if not isinstance(files, list) or len(files) > 2 or any(not _nonempty(item) for item in files):
        errors.append("input.context_files: expected array of at most two non-empty paths")
    build = _field_object(data, "build", "input", errors)
    for key in ("command", "verify_command", "clean_command", "working_directory"):
        _string(build, key, "input.build", errors)
    if not isinstance(build.get("expected_stdout"), str):
        errors.append("input.build.expected_stdout: expected string")
    for parent, key, path in ((build, "timeout_seconds", "input.build"), (data, "max_iterations", "input")):
        if type(parent.get(key)) is not int or parent[key] < 1:
            errors.append(f"{path}.{key}: expected positive integer")
    _string(data, "configuration_id", "input", errors)


def validate_create(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root: expected object"]
    _required(data, CREATE_SCHEMA["required"], "root", errors)
    if data.get("schema_version") != "1.0":
        errors.append("schema_version: expected 1.0")
    _string(data, "trace_id", "root", errors)
    _string(data, "idempotency_key", "root", errors)
    kind = data.get("job_type")
    if kind not in JOB_TYPES:
        errors.append(f"job_type: unsupported value {kind!r}")
    input_data = _field_object(data, "input", "root", errors)
    if not input_data:
        return errors
    _repository(input_data, errors, require_url=True)

    if kind == "DRAFT":
        validate_draft_input(input_data, errors)
    elif kind == "FULL_CHECK":
        environment = _field_object(input_data, "environment", "input", errors)
        for key in ("image_ref", "configuration_id", "project_root"):
            _string(environment, key, "input.environment", errors)
        _string(input_data, "build_command", "input", errors)
    elif kind == "INCREMENTAL_CHECK":
        _sha(input_data, "base_commit", "input", errors)
        baseline = _field_object(input_data, "baseline", "input", errors)
        _uri(baseline, "actual_graph_uri", "input.baseline", errors)
        _sha(baseline, "commit", "input.baseline", errors)
        _string(baseline, "configuration_id", "input.baseline", errors)
        environment = _field_object(input_data, "environment", "input", errors)
        _string(environment, "configuration_id", "input.environment", errors)
        if baseline.get("commit") != input_data.get("base_commit"):
            errors.append("input.baseline.commit: does not match base_commit")
        if baseline.get("configuration_id") != environment.get("configuration_id"):
            errors.append("input.baseline.configuration_id: does not match environment")
    elif kind == "REPAIR":
        _uri(input_data, "md_report_uri", "input", errors)
        _string(input_data, "makefile_path", "input", errors)
        environment = _field_object(input_data, "environment", "input", errors)
        _string(environment, "configuration_id", "input.environment", errors)
        _string(input_data, "build_command", "input", errors)
        _string(input_data, "verify_command", "input", errors)
    return errors


def validate_artifact(data: Any, *, job_id: str | None = None, commit: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["artifact: expected object"]
    _required(data, ARTIFACT_SCHEMA["required"], "artifact", errors)
    for key in ("artifact_id", "type", "media_type", "configuration_id"):
        _string(data, key, "artifact", errors)
    _uri(data, "uri", "artifact", errors)
    if not isinstance(data.get("producer_job_id"), str) or not JOB_ID.fullmatch(data["producer_job_id"]):
        errors.append("artifact.producer_job_id: invalid Job ID")
    _sha(data, "repository_commit", "artifact", errors)
    digest = data.get("sha256")
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)):
        errors.append("artifact.sha256: expected 64-hex digest")
    if job_id is not None and data.get("producer_job_id") != job_id:
        errors.append("artifact.producer_job_id: does not match parent job")
    if commit is not None and data.get("repository_commit") != commit:
        errors.append("artifact.repository_commit: does not match parent job")
    return errors


def validate_job(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root: expected object"]
    _required(data, JOB_SCHEMA["required"], "root", errors)
    if data.get("schema_version") != "1.0":
        errors.append("schema_version: expected 1.0")
    job_id = data.get("job_id")
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        errors.append("job_id: expected job- prefixed identifier")
    _string(data, "trace_id", "root", errors)
    kind = data.get("job_type")
    if kind not in JOB_TYPES:
        errors.append(f"job_type: unsupported value {kind!r}")
    status = data.get("status")
    if status not in STATUSES:
        errors.append(f"status: unsupported value {status!r}")
    input_data = _field_object(data, "input", "root", errors)
    if input_data:
        _repository(input_data, errors, require_url=False)
        if kind == "DRAFT":
            _repository(input_data, errors, require_url=True)
            validate_draft_input(input_data, errors)
    output = data.get("output")
    error = data.get("error")
    if status in {"QUEUED", "RUNNING"}:
        if output is not None or error is not None:
            errors.append("status: non-terminal job must have null output and error")
    elif status == "SUCCEEDED":
        if not isinstance(output, dict):
            errors.append("output: SUCCEEDED requires object")
        if error is not None:
            errors.append("error: SUCCEEDED requires null")
    elif status in {"FAILED", "TIMED_OUT", "CANCELLED"}:
        if output is not None:
            errors.append("output: failed terminal state requires null")
        if not isinstance(error, dict):
            errors.append("error: failed terminal state requires object")
        else:
            _string(error, "code", "error", errors)
            _string(error, "message", "error", errors)

    if status == "SUCCEEDED" and isinstance(output, dict):
        if kind == "DRAFT":
            _string(output, "image_ref", "output", errors)
            if not isinstance(output.get("image_id"), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", output["image_id"]):
                errors.append("output.image_id: expected sha256 image ID")
            if any(type(output.get(key)) is not int or output[key] != 0 for key in ("build_exit_code", "verify_exit_code")):
                errors.append("output: DRAFT success requires zero build and verify exit codes")
            build = input_data.get("build", {})
            if not isinstance(output.get("verify_stdout"), str) or output.get("verify_stdout") != build.get("expected_stdout"):
                errors.append("output.verify_stdout: does not match expected_stdout")
            environment = _field_object(output, "environment", "output", errors)
            for key in ("arch", "project_root", "working_directory", "clean_build_command", "configuration_id"):
                _string(environment, key, "output.environment", errors)
            if environment.get("os") != "linux":
                errors.append("output.environment.os: expected linux")
            if environment.get("repository_commit") != input_data.get("repository", {}).get("commit"):
                errors.append("output.environment.repository_commit: does not match input")
            if environment.get("configuration_id") != input_data.get("configuration_id"):
                errors.append("output.environment.configuration_id: does not match input")
            tracking = _field_object(environment, "tracking", "output.environment", errors)
            if tracking.get("status") not in {"PENDING_A13", "CONFIRMED"}:
                errors.append("output.environment.tracking.status: invalid status")
            for key in ("required_capabilities", "security_options"):
                value = tracking.get(key)
                if key not in tracking or (value is not None and (not isinstance(value, list) or any(not _nonempty(x) for x in value))):
                    errors.append(f"output.environment.tracking.{key}: expected array or null")
                if tracking.get("status") == "CONFIRMED" and value is None:
                    errors.append(f"output.environment.tracking.{key}: CONFIRMED requires explicit array")
            iterations = output.get("iterations")
            if not isinstance(iterations, list) or not iterations:
                errors.append("output.iterations: expected non-empty array")
            else:
                for item in iterations:
                    if not isinstance(item, dict):
                        errors.append("output.iterations: expected object items")
                        continue
                    if type(item.get("iteration")) is not int or item["iteration"] < 1 or type(item.get("build_exit_code")) is not int:
                        errors.append("output.iterations: invalid iteration or exit code")
                    _uri(item, "log_uri", "output.iterations", errors)
                    _string(item, "change_description", "output.iterations", errors)
            artifacts = output.get("artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                errors.append("output.artifacts: DRAFT success requires artifacts")
            else:
                if not any(isinstance(item, dict) and item.get("type") == "DOCKERFILE" for item in artifacts):
                    errors.append("output.artifacts: no DOCKERFILE artifact")
                commit = input_data.get("repository", {}).get("commit") if input_data else None
                for index, artifact in enumerate(artifacts):
                    for issue in validate_artifact(artifact, job_id=job_id, commit=commit):
                        errors.append(f"output.artifacts[{index}].{issue}")
                    if isinstance(artifact, dict) and artifact.get("configuration_id") != input_data.get("configuration_id"):
                        errors.append(f"output.artifacts[{index}].configuration_id: does not match input")
        elif kind in {"FULL_CHECK", "INCREMENTAL_CHECK"}:
            if not isinstance(output.get("findings"), list):
                errors.append("output.findings: expected array")
            graph_key = "actual_graph_uri" if kind == "FULL_CHECK" else "updated_actual_graph_uri"
            _uri(output, graph_key, "output", errors)
        elif kind == "REPAIR":
            _uri(output, "patch_uri", "output", errors)
            if output.get("remaining_md_count") != 0:
                errors.append("output.remaining_md_count: successful repair requires zero")
    return errors


def validate_examples() -> list[str]:
    failures: list[str] = []
    valid_files = sorted(EXAMPLES.glob("*.json"))
    invalid_files = sorted((EXAMPLES / "invalid").glob("*.json"))
    if not valid_files or not invalid_files:
        return ["examples: expected both valid and invalid JSON samples"]
    for path in valid_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name}: invalid JSON: {exc}")
            continue
        issues = validate_create(data) if path.name.endswith(".request.json") else validate_job(data)
        if issues:
            failures.extend(f"{path.name}: {issue}" for issue in issues)
        else:
            print(f"PASS {path.relative_to(ROOT)}")
    for path in invalid_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name}: invalid JSON syntax cannot test contract: {exc}")
            continue
        issues = validate_create(data) if "status" not in data else validate_job(data)
        if not issues:
            failures.append(f"{path.name}: invalid sample was accepted")
        else:
            print(f"EXPECTED REJECTION {path.relative_to(ROOT)}: {issues[0]}")
    return failures


if __name__ == "__main__":
    found = validate_examples()
    if found:
        for issue in found:
            print(f"FAIL {issue}", file=sys.stderr)
        raise SystemExit(1)
    print("All contract examples passed their expected outcome.")
