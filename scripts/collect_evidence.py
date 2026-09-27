"""B13 evidence format 0.1: reusable recorder and command-line wrapper."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def probe(argv, cwd=ROOT):
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        return {"value": (p.stdout or p.stderr).strip() if p.returncode == 0 else None,
                "reason": None if p.returncode == 0 else (p.stderr or p.stdout).strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"value": None, "reason": str(exc)}


class Recorder:
    def __init__(self, output, suite, case, root=ROOT):
        self.root = Path(root).resolve()
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        status = probe(["git", "status", "--porcelain"], self.root)
        files = probe(["git", "ls-files", "--cached", "--others", "--exclude-standard"], self.root)
        hashes = {}
        for name in (files["value"] or "").splitlines():
            p = self.root / name
            if p.is_file() and not name.startswith("evidence/"):
                hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.data = {
            "evidence_schema_version": "0.1", "format_status": "B13_DRAFT",
            "run_id": self.output.name, "suite": suite, "case": case,
            "started_at": now(), "finished_at": None,
            "source": {"repository": probe(["git", "remote", "get-url", "origin"], self.root),
                       "commit_sha": probe(["git", "rev-parse", "HEAD"], self.root)["value"],
                       "dirty": bool(status["value"]) if status["value"] is not None else None,
                       "git_status": status, "file_sha256": hashes},
            "environment": {"os": platform.platform(), "arch": platform.machine(),
                            "cwd": str(self.root), "container": None},
            "tools": {name: probe(args) for name, args in {
                "python": [sys.executable, "--version"], "git": ["git", "--version"],
                "make": ["make", "--version"], "gcc": ["gcc", "--version"],
                "docker": ["docker", "version"]}.items()},
            "commands": [], "checks": [], "artifacts": [],
            "provenance": {"kind": "B13_MANUAL_ORACLE", "detector_executed": False},
            "result": "NOT_RUN"}

    def run(self, argv, cwd=None, timeout=600):
        index = len(self.data["commands"]) + 1
        entry = {"id": f"cmd-{index}", "argv": list(map(str, argv)),
                 "cwd": str(Path(cwd or self.root).resolve()), "started_at": now(),
                 "exit_code": None, "timed_out": False, "execution_error": None}
        try:
            p = subprocess.run(entry["argv"], cwd=entry["cwd"], capture_output=True,
                               timeout=timeout)
            stdout, stderr = p.stdout, p.stderr
            entry["exit_code"] = p.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
            entry["timed_out"] = True
        except OSError as exc:
            stdout, stderr = b"", str(exc).encode("utf-8")
            entry["execution_error"] = str(exc)
        entry["finished_at"] = now()
        for channel, payload in (("stdout", stdout), ("stderr", stderr)):
            name = f"{index:03d}.{channel}.log"
            (self.output / name).write_bytes(payload)
            entry[channel + "_path"] = name
        with (self.output / "verify.log").open("a", encoding="utf-8") as log:
            log.write(json.dumps(entry, ensure_ascii=False) + "\n[stdout]\n")
            log.write(stdout.decode("utf-8", "replace") + "\n[stderr]\n")
            log.write(stderr.decode("utf-8", "replace") + "\n")
        self.data["commands"].append(entry)
        return entry, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")

    def check(self, name, expected, actual, passed=None, command=None, status=None):
        if status is not None and status not in {"PASS", "FAIL", "SKIPPED", "NOT_RUN"}:
            raise ValueError(f"unsupported check status: {status}")
        self.data["checks"].append({"id": name, "expected": expected, "actual": actual,
            "status": status or ("PASS" if passed else "FAIL"), "command_id": command})

    def finish(self, notes=""):
        states = [x["status"] for x in self.data["checks"]]
        self.data["result"] = ("FAIL" if "FAIL" in states else
                               "INCOMPLETE" if any(s in states for s in ("NOT_RUN", "SKIPPED")) else
                               "PASS" if states else "NOT_RUN")
        self.data["finished_at"] = now()
        for p in sorted(self.output.iterdir()):
            if p.is_file() and p.name not in ("summary.json", "observations.md"):
                self.data["artifacts"].append({"path": p.name,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        (self.output / "summary.json").write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = ["# 运行证据", "", f"- 格式：B13 草案 0.1", f"- 结果：{self.data['result']}",
                 f"- 开始：{self.data['started_at']}", f"- 结束：{self.data['finished_at']}",
                 f"- HEAD：{self.data['source']['commit_sha']}", f"- dirty：{self.data['source']['dirty']}",
                 "- 未提交文件以 summary.json 的 file_sha256 绑定，HEAD 不代表全部运行源码。",
                 "- 环境、命令、退出码与原始输出见 summary.json、verify.log 和分流日志。", "", notes, ""]
        lines += [f"- {c['status']} {c['id']}: {c['actual']}" for c in self.data["checks"]]
        (self.output / "observations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.data["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--suite", default="E3")
    parser.add_argument("--case", required=True)
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--expect-exit", type=int, default=0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command after -- is required")
    recorder = Recorder(args.output, args.suite, args.case)
    entry, _, _ = recorder.run(command, args.cwd, args.timeout)
    recorder.check("command_exit", args.expect_exit, entry["exit_code"],
                   entry["exit_code"] == args.expect_exit and not entry["timed_out"] and not entry["execution_error"], entry["id"])
    result = recorder.finish("本通用包装只判断命令退出码，不推断子脚本内部检查或检测器结果。")
    print(f"{result}: {recorder.output}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
