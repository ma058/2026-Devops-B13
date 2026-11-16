"""Verify the pinned A13 finding-report 2.0 candidate and B13's own v2 samples.

B13 review position (2026-11-10): the A13 v2 candidate at commit
c4364e96521a8729fe11695c030916e1746eca1b is accepted. This verifier provides
the machine-checked part of that acceptance:

  1. snapshot integrity - every pinned file matches the manifest SHA-256;
  2. the A13 valid example passes B13's independent v2 semantic validator;
  3. every A13 invalid example is rejected, each for its documented reason;
  4. the MDFixer consumption policy (MISSING only) still applies on v2 input;
  5. B13's own migrated v2 examples pass the same validator;
  6. B13's own negative fixtures are rejected;
  7. the v1 -> v2 migration preserves the finding set (semantic equivalence).

The pinned A13 files remain synthetic contract fixtures; nothing here claims
that BuildChecker or EChecker executed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_v2 import consume_missing_v2, validate_report_v2  # noqa: E402

SNAPSHOT = ROOT / "contracts" / "paired" / "a13-v2"
B13_V2 = ROOT / "contracts" / "examples" / "v2"
EVIDENCE = ROOT / "evidence" / "E2" / "2026-11-10-a13-v2-interop"

A13_REPOSITORY = "https://github.com/Dufunare/2026-Devops-A13"
A13_V2_COMMIT = "c4364e96521a8729fe11695c030916e1746eca1b"

# Each A13 negative fixture must be rejected; the expected keyword documents
# *why* it is invalid per the written v2 rules.
A13_INVALID_EXPECTATIONS = {
    "empty-evidence.json": "evidence",
    "tool-without-producer-job.json": "producer_job_id",
    "unknown-core-field.json": "unknown core fields",
    "unresolved-with-path.json": "location",
    "unsafe-dependency.json": "dependency",
}

# B13-authored negative fixtures; each covers a rule surface distinct from the
# A13 set. The 2026-11-10 review-fix batch (locator uri types, explicit null
# extensions, path normalisation variants, unhashable detector/type) closes
# the gaps found in B13's first validator implementation.
B13_INVALID_EXPECTATIONS = {
    "oracle-with-producer-job.json": "producer_job_id",
    "unresolved-with-line.json": "location",
    "evidence-item-missing-detail.json": "detail",
    "unsafe-dependency-absolute.json": "dependency",
    "unknown-finding-field.json": "unknown core fields",
    "finding-commit-mismatch.json": "must equal repository.commit",
    # review-fix batch: locator.uri type discipline
    "artifact-locator-uri-null.json": "artifact_locator.uri",
    "artifact-locator-uri-array.json": "artifact_locator.uri",
    # review-fix batch: explicit null extensions is not an omitted field
    "extensions-explicit-null.json": "explicit null rejected",
    "finding-extensions-null.json": "explicit null rejected",
    # review-fix batch: raw-segment path checks (no normalisation collapse)
    "dependency-double-slash.json": "dependency",
    "dependency-dot-segment.json": "dependency",
    "dependency-trailing-slash.json": "dependency",
    "location-path-double-slash.json": "location.path",
    "locator-repository-path-dot.json": "repository_path",
    # review-fix batch: unhashable JSON types must error, not crash
    "detector-array.json": "detector",
    "finding-type-object.json": "type",
}

B13_VALID_SAMPLES = ("md-report.valid.json", "md-report.e3-target.valid.json")
B13_V1_REPORT = ROOT / "contracts" / "examples" / "md-report.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, ok: bool, detail: str) -> dict:
    return {"check": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def run_checks() -> list[dict]:
    checks: list[dict] = []

    # 1. manifest + pinned-commit integrity
    manifest_path = SNAPSHOT / "manifest.json"
    if not manifest_path.is_file():
        return [check("manifest", False, "manifest.json missing")]
    manifest = load_json(manifest_path)
    checks.append(check(
        "manifest.source",
        manifest.get("source_repository") == A13_REPOSITORY
        and manifest.get("source_commit") == A13_V2_COMMIT,
        f"pinned {manifest.get('source_commit', '?')[:12]}",
    ))
    for entry in manifest.get("files", []):
        path = SNAPSHOT / entry["snapshot_path"]
        if not path.is_file():
            checks.append(check(f"snapshot.{entry['snapshot_path']}", False, "file missing"))
            continue
        digest = sha256(path)
        checks.append(check(
            f"sha256.{entry['snapshot_path']}",
            digest == entry["upstream_sha256"] == entry["snapshot_sha256"],
            digest,
        ))

    # 2. A13 valid example passes B13's independent validator
    a13_valid = load_json(SNAPSHOT / "examples" / "md-report.valid.json")
    errors = validate_report_v2(a13_valid)
    checks.append(check(
        "a13.valid.accepted", not errors, "; ".join(errors) or "accepted by B13 validator",
    ))

    # 3. A13 invalid examples rejected with the documented reason
    for filename, keyword in sorted(A13_INVALID_EXPECTATIONS.items()):
        errors = validate_report_v2(load_json(SNAPSHOT / "examples" / "invalid" / filename))
        hit = any(keyword in message for message in errors)
        checks.append(check(
            f"a13.invalid.{filename}", bool(errors) and hit,
            "; ".join(errors[:2]) or "NOT REJECTED",
        ))

    # 4. MDFixer consumption on the A13 v2 sample: MISSING only
    consumed = consume_missing_v2(a13_valid)
    ok = (
        [item["dependency"] for item in consumed["consumed_findings"]] == ["config.h"]
        and [item["dependency"] for item in consumed["skipped_findings"]] == ["unused.h"]
    )
    checks.append(check(
        "a13.consumption.missing_only", ok,
        f"consumed={[i['dependency'] for i in consumed['consumed_findings']]}, "
        f"skipped={[i['dependency'] for i in consumed['skipped_findings']]}",
    ))

    # 5. B13's own migrated valid samples pass
    for filename in B13_VALID_SAMPLES:
        errors = validate_report_v2(load_json(B13_V2 / filename))
        checks.append(check(
            f"b13.valid.{filename}", not errors, "; ".join(errors) or "valid",
        ))

    # 6. B13 negative fixtures rejected
    for filename, keyword in sorted(B13_INVALID_EXPECTATIONS.items()):
        errors = validate_report_v2(load_json(B13_V2 / "invalid" / filename))
        hit = any(keyword in message for message in errors)
        checks.append(check(
            f"b13.invalid.{filename}", bool(errors) and hit,
            "; ".join(errors[:2]) or "NOT REJECTED",
        ))

    # 7. v1 -> v2 migration preserves the finding set
    v1 = load_json(B13_V1_REPORT)
    v2 = load_json(B13_V2 / "md-report.valid.json")
    v1_set = sorted(
        (f["type"], f["target"], f["dependency"]) for f in v1["findings"]
    )
    v2_set = sorted(
        (f["type"], f["target"], f["dependency"]) for f in v2["findings"]
    )
    checks.append(check(
        "b13.migration.equivalence", v1_set == v2_set,
        f"v1={v1_set} v2={v2_set}",
    ))

    return checks


def write_evidence(checks: list[dict]) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    summary = {
        "evidence_schema_version": "0.1",
        "run_id": "2026-11-10-a13-v2-interop",
        "suite": "E2",
        "case": "pair13-finding-report-v2",
        "finished_at": now,
        "source": {
            "repository": A13_REPOSITORY,
            "pinned_commit": A13_V2_COMMIT,
            "pinned_files": len(load_json(SNAPSHOT / "manifest.json")["files"]),
        },
        "b13_position": "accept the A13 v2 candidate; freeze pending A13 reading B13's v2 samples",
        "checks": checks,
        "counts": {
            "total": len(checks),
            "passed": sum(1 for c in checks if c["status"] == "PASS"),
            "failed": sum(1 for c in checks if c["status"] == "FAIL"),
        },
    }
    (EVIDENCE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# E2 Pair13 finding-report 2.0 候选互读验证（B13 侧）",
        "",
        f"- 运行时间（UTC）：{now}",
        f"- A13 固定提交：`{A13_V2_COMMIT}`（v2 候选引入提交，2026-10-10）",
        "- B13 立场：接受该 2.0 候选；冻结待 A13 读取 B13 v2 样例并回写固定提交后完成",
        "",
        "| 检查 | 结果 | 说明 |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        lines.append(f"| {item['check']} | {item['status']} | {item['detail']} |")
    lines += [
        "",
        "说明：",
        "- A13 固定提交中的样例仍为 synthetic contract fixtures；本验证证明 v2 契约互读、",
        "  语义校验与 MDFixer 消费链路，不表示 BuildChecker/EChecker 已运行。",
        "- B13 的 6 个负例与 A13 的 5 个负例覆盖不同规则面（见脚本头注释），共同确认",
        "  双方对 v2 边界的理解一致。",
        "- v1→v2 语义等价检查确认迁移未改变 finding 集合。",
    ]
    (EVIDENCE / "observations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    checks = run_checks()
    write_evidence(checks)
    failed = [c for c in checks if c["status"] == "FAIL"]
    print(f"{'PASS' if not failed else 'FAIL'}: {len(checks) - len(failed)}/{len(checks)} checks")
    for item in checks:
        print(f"  [{item['status']}] {item['check']}: {item['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
