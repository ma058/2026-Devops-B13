"""B13 E5 manual-equivalent build/run recorder; does not generate candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import uuid

from lab_cloud import ROOT, execute

sys.path.insert(0, str(ROOT / "services/draft"))
from draft.autobuild import prepare_candidate


def validate_result(build_code, image, command, run_code, stdout):
    return (build_code == 0 and bool(re.fullmatch(r"sha256:[0-9a-f]{64}", image))
            and command[-1] == image and "--network" in command
            and command[command.index("--network") + 1] == "none"
            and run_code == 0 and stdout.rstrip("\r\n") == "hello E3")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if sys.platform != "linux" or args.timeout <= 0:
        parser.error("Linux and a positive timeout are required")
    candidate = (ROOT / args.candidate).resolve()
    output = (ROOT / args.out).resolve()
    if ROOT / "work" not in output.parents or output.exists():
        parser.error("Use a new directory strictly below work/")
    text = candidate.read_text(encoding="utf-8")
    prepare_candidate((ROOT / "fixtures/draft/Dockerfile.broken").read_text(), text)
    output.mkdir(parents=True)
    project = output / "project"
    shutil.copytree(ROOT / "fixtures/draft", project,
                    ignore=shutil.ignore_patterns("Dockerfile.reference"))
    saved = output / "Dockerfile"
    saved.write_bytes(candidate.read_bytes())
    report = {"passed": False, "candidate_sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
              "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in project.iterdir() if p.is_file()},
              "scope": "B13 E5 explicit candidate build and image-ID run"}
    cidfile = output / "container-id.txt"
    try:
        tag = "b13-e5-manual:" + uuid.uuid4().hex
        code = execute(["docker", "build", "--progress=plain", "-f", str(saved),
                        "-t", tag, str(project)], output / "build", args.timeout)
        report["build_exit_code"] = code
        if code != 0:
            return 1
        if execute(["docker", "image", "inspect", tag], output / "image", 30):
            return 1
        image = json.loads((output / "image/stdout.log").read_text())[0]["Id"]
        report["image_id"] = image
        command = ["docker", "run", "--rm", "--network", "none", "--cpus", "1",
                   "--memory", "128m", "--pids-limit", "64",
                   "--cidfile", str(cidfile), image]
        run_code = execute(command, output / "verify", 30)
        stdout = (output / "verify/stdout.log").read_text()
        report.update(run_exit_code=run_code, actual_output=stdout, command=command)
        report["passed"] = validate_result(code, image, command, run_code, stdout)
        return 0 if report["passed"] else 1
    finally:
        if cidfile.exists():
            cid = cidfile.read_text().strip()
            if re.fullmatch(r"[0-9a-f]{64}", cid):
                execute(["docker", "rm", "-f", cid], output / "cleanup", 30)
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
