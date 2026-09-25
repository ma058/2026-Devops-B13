"""Check the JSON Schema documents and E2 examples with jsonschema.

Requires the optional jsonschema package. The standard-library validator in
validate.py remains the baseline check on systems without this package.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts" / "schemas"
EXAMPLES = ROOT / "contracts" / "examples"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def schema_name_for(path: Path, instance: dict) -> str:
    if path.name.startswith("md-report"):
        return "md-report.schema.json"
    if path.name.endswith(".request.json") or "status" not in instance:
        return "create-job.schema.json"
    return "job.schema.json"


def main() -> None:
    for path in sorted(SCHEMAS.glob("*.json")):
        Draft202012Validator.check_schema(read(path))
        print(f"SCHEMA OK {path.relative_to(ROOT)}")

    for path in sorted(EXAMPLES.glob("*.json")):
        instance = read(path)
        schema_name = schema_name_for(path, instance)
        validator = Draft202012Validator(read(SCHEMAS / schema_name))
        issues = list(validator.iter_errors(instance))
        if issues:
            raise AssertionError(f"{path.name}: {issues[0].message}")
        print(f"INSTANCE OK {path.relative_to(ROOT)}")

    for path in sorted((EXAMPLES / "invalid").glob("*.json")):
        instance = read(path)
        schema_name = schema_name_for(path, instance)
        validator = Draft202012Validator(read(SCHEMAS / schema_name))
        issues = list(validator.iter_errors(instance))
        if not issues:
            raise AssertionError(f"{path.name}: expected schema rejection")
        print(f"EXPECTED REJECTION {path.relative_to(ROOT)}: {issues[0].message}")

    fixture = ROOT / "fixtures" / "mdfixer" / "implicit-style" / "md-report.template.json"
    validator = Draft202012Validator(read(SCHEMAS / "md-report.schema.json"))
    issues = list(validator.iter_errors(read(fixture)))
    if issues:
        raise AssertionError(f"{fixture.name}: {issues[0].message}")
    print(f"INSTANCE OK {fixture.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
