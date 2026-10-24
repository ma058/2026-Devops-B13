"""Check saved teaching replay reports against their local artifacts."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re


def verify_input_manifest(project, manifest):
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("input_sha256 must be a non-empty mapping")
    if project.is_symlink() or not project.is_dir():
        raise ValueError("Project must be a real directory")
    for name, expected in manifest.items():
        if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
            raise ValueError("Input path must be a canonical relative POSIX path")
        relative = PurePosixPath(name)
        if (not relative.parts or relative.is_absolute() or ".." in relative.parts
                or relative.as_posix() != name or PureWindowsPath(name).drive):
            raise ValueError(f"Invalid input path: {name}")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            raise ValueError(f"Invalid SHA-256 digest: {name}")
    actual = set()
    for path in project.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not supported in project evidence")
        if path.is_file():
            actual.add(path.relative_to(project).as_posix())
        elif not path.is_dir():
            raise ValueError("Unsupported file type in project evidence")
    recorded = set(manifest)
    if actual != recorded:
        omitted = sorted(actual - recorded)
        absent = sorted(recorded - actual)
        raise ValueError(f"Input manifest does not match project: unlisted={omitted}, absent={absent}")
    for name, expected in manifest.items():
        if hashlib.sha256((project / name).read_bytes()).hexdigest() != expected.lower():
            raise ValueError(f"Input hash mismatch: {name}")


def verify_runtime_command(command, image):
    if not isinstance(image, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("Verification requires an immutable image ID")
    if (not isinstance(command, list) or len(command) < 5
            or any(not isinstance(part, str) or not part or "\x00" in part for part in command)
            or command[:2] != ["docker", "run"] or command[-1] != image):
        raise ValueError("Verification command must be docker run ending with the saved image ID")
    # Accept the producer's saved argv format, not shell text. Unknown or
    # repeated options (including --net aliases) cannot override isolation.
    allowed = {"--rm": 0, "--network": 1, "--cpus": 1, "--memory": 1,
               "--pids-limit": 1, "--cidfile": 1}
    options, seen, index = command[2:-1], {}, 0
    while index < len(options):
        flag = options[index]
        if flag not in allowed or flag in seen:
            raise ValueError(f"Unsupported or duplicate verification option: {flag}")
        width = allowed[flag]
        if width:
            if index + 1 >= len(options) or options[index + 1].startswith("--"):
                raise ValueError(f"Missing verification option value: {flag}")
            seen[flag] = options[index + 1]
        else:
            seen[flag] = True
        index += width + 1
    if seen.get("--network") != "none":
        raise ValueError("Verification must explicitly use --network none")


def verify(directory):
    root = Path(directory).resolve()
    report = json.loads((root / "result.json").read_text(encoding="utf-8"))
    if report["status"] != "SUCCEEDED":
        raise ValueError("Workflow was not successful")
    attempts = report["attempts"]
    if len(attempts) != 2 or [a["iteration"] for a in attempts] != [1, 2]:
        raise ValueError("Expected exactly two ordered attempts")
    if attempts[0]["build_exit_code"] == 0 or attempts[0]["failure_class"] != "MISSING_MAKE":
        raise ValueError("Baseline did not reproduce missing make")
    initial_logs = "\n".join((root / "iter-01" / name).read_text(encoding="utf-8")
                             for name in ("build-stdout.log", "build-stderr.log"))
    if not re.search(r"/bin/sh:.*\bmake: (?:not found|command not found)", initial_logs):
        raise ValueError("Missing-make evidence was not found in saved logs")
    if attempts[1]["build_exit_code"] != 0:
        raise ValueError("Candidate build did not succeed")
    candidate = (root / "iter-02/Dockerfile").read_bytes()
    if hashlib.sha256(candidate).hexdigest() != report["candidate_sha256"]:
        raise ValueError("Candidate hash mismatch")
    image = json.loads((root / "iter-02/image-inspect.json").read_text(encoding="utf-8"))[0]["Id"]
    verification = report["verification"]
    verify_runtime_command(verification["command"], image)
    if image != attempts[1]["image_id"] or verification["command"][-1] != image:
        raise ValueError("Built and verified image IDs differ")
    actual = (root / "verify.log").read_text(encoding="utf-8")
    if verification["exit_code"] != 0 or verification["output_matches"] is not True:
        raise ValueError("Program verification failed")
    if actual != verification["actual_output"] or actual.rstrip("\r\n") != "hello E3" or verification["expected_output"] != "hello E3":
        raise ValueError("Unexpected program output")
    project = root / "project"
    if (project / "Dockerfile.reference").exists():
        raise ValueError("Reference answer leaked into build context")
    verify_input_manifest(project, report["input_sha256"])
    return {"passed": True, "trace_id": report["trace_id"], "baseline_failure": "MISSING_MAKE",
            "fixed_build_exit_code": 0, "verify_exit_code": 0, "verified_output": "hello E3",
            "candidate_sha256": report["candidate_sha256"], "image_id": image,
            "scope": "Saved evidence consistency; does not independently rerun builds"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        result = verify(args.run_dir)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
