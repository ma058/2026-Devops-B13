"""Run the manual DRAFT Docker baseline; no LLM or A13 service is invoked."""
from __future__ import annotations

import argparse
import difflib
import json
from datetime import datetime
from pathlib import Path

from collect_evidence import ROOT, Recorder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    parser.add_argument("--build-arg", action="append", default=[], help="Optional Docker build argument, e.g. HTTP_PROXY for a local environment")
    args = parser.parse_args()
    fixture = ROOT / "fixtures" / "draft"
    output = args.output or str(ROOT / "evidence" / "E3" / (datetime.now().strftime("%Y-%m-%d-%H%M%S") + "-draft"))
    record = Recorder(output, "E3", "draft")
    expected = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
    tag = "b13-draft-reference:" + datetime.now().strftime("%Y%m%d%H%M%S")
    build_args = [item for value in args.build_arg for item in ("--build-arg", value)]
    diff = difflib.unified_diff((fixture / "Dockerfile.broken").read_text().splitlines(True),
                                (fixture / "Dockerfile.reference").read_text().splitlines(True),
                                fromfile="Dockerfile.broken", tofile="Dockerfile.reference")
    (record.output / "Dockerfile.diff").write_text("".join(diff), encoding="utf-8")
    try:
        cmd, out, err = record.run(["docker", "build", "--no-cache", "--progress=plain", "-f", "Dockerfile.broken", "."], fixture)
        good_failure = (cmd["exit_code"] is not None and cmd["exit_code"] != 0 and
                        not cmd["timed_out"] and not cmd["execution_error"] and expected["broken"]["diagnostic"] in (out + err))
        record.check("broken_missing_make", expected["broken"], {"exit_code": cmd["exit_code"], "diagnostic_found": expected["broken"]["diagnostic"] in out + err}, good_failure, cmd["id"])
        cmd, _, _ = record.run(["docker", "build", "--no-cache", "--progress=plain", *build_args, "-t", tag, "-f", "Dockerfile.reference", "."], fixture, 1200)
        record.check("reference_build", 0, cmd["exit_code"], cmd["exit_code"] == 0, cmd["id"])
        if cmd["exit_code"] == 0:
            cmd, out, _ = record.run(["docker", "image", "inspect", tag])
            metadata = json.loads(out)[0] if cmd["exit_code"] == 0 else {}
            record.data["image"] = {"ref": tag, "id": metadata.get("Id"), "repo_digests": metadata.get("RepoDigests", [])}
            record.data["environment"]["container"] = {"os": metadata.get("Os"), "arch": metadata.get("Architecture"), "project_root": "/workspace/project"}
            record.check("image_identity", "sha256 image ID", metadata.get("Id"), bool(metadata.get("Id")), cmd["id"])
            cmd, base, _ = record.run(["docker", "image", "inspect", "public.ecr.aws/ubuntu/ubuntu:20.04"])
            record.data["base_image"] = json.loads(base)[0] if cmd["exit_code"] == 0 else None
            for i in range(expected["repeat_count"]):
                cmd, out, _ = record.run(["docker", "run", "--rm", tag])
                record.check(f"hello_run_{i + 1}", expected["reference"], {"exit_code": cmd["exit_code"], "stdout": out}, cmd["exit_code"] == 0 and out == expected["reference"]["stdout"], cmd["id"])
            cmd, out, _ = record.run(["docker", "run", "--rm", tag, "sh", "-c", "make clean && make && ./hello"])
            record.check("clean_build", "exit 0; last line hello E3", {"exit_code": cmd["exit_code"], "stdout": out}, cmd["exit_code"] == 0 and out.splitlines()[-1:] == ["hello E3"], cmd["id"])
            cmd, out, _ = record.run(["docker", "run", "--rm", tag, "sh", "-c", "cat /etc/os-release; uname -m; make --version; gcc --version; git --version; python3 --version; sha256sum hello"])
            record.data["environment"]["container"]["tool_versions_and_binary_hash"] = out
            record.check("container_metadata", 0, cmd["exit_code"], cmd["exit_code"] == 0, cmd["id"])
        else:
            record.check("container_checks", "successful reference image", "reference build unavailable", status="NOT_RUN")
    except Exception as exc:
        record.check("runner_error", "no exception", repr(exc), False)
    finally:
        result = record.finish("人工 DRAFT 基线；未调用 LLM 或 A13。预期 broken 构建失败按错误原因判定。镜像保留用于复验。")
    print(f"{result}: {record.output}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
