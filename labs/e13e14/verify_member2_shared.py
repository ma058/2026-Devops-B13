"""Check one B13 normal run from real shared Compose role logs and worker files."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shlex


def load(path):
    return json.loads(path.read_bytes())


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


PREVIEW = "b13-tomlc99-full-preview-v1"
STAGES = ("draft", "baseline-full", "target-full", "incremental", "repair", "final-full")
WORKERS = {"baseline-full/runtime": "full", "target-full/runtime": "full", "final-full/runtime": "full",
           "incremental/baseline-runtime": "scan", "incremental/target-runtime": "scan", "repair/runtime": "validate"}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_preview_probe(evidence, products):
    probe = load(evidence / "header-probe.json")
    before, after = probe["before_mtime_ns"], probe["after_mtime_ns"]
    require(probe["path"] == "toml.h" and probe["argv"] == ["make", "all"], "wrong header probe or rebuild")
    require(set(before) == set(after) == set(products)
            and all(isinstance(before[n], int) and isinstance(after[n], int) and after[n] > before[n] for n in products),
            "missing six-product mtime advance")
    for label, argv in (("control-clean", ["make", "clean"]), ("control-build", ["make", "all"]),
                        ("clean", ["make", "clean"]), ("build", ["make", "all"]), ("header-rebuild", ["make", "all"]),
                        ("empty-stdin", ["./toml_json"])):
        require(load(evidence / (label + ".command.json")) == {"argv": argv, "stdin_hex": ""}
                and (evidence / (label + ".exit.txt")).read_text().strip() == "0", label + " command or exit differs")
    require((evidence / "empty-stdin.stdout").read_bytes() == b"{}\n"
            and not (evidence / "empty-stdin.stderr").read_bytes(), "standalone toml_json output differs")
    raw = (evidence / "header-rebuild.stdout").read_bytes()
    require(raw == (evidence / "control-build.stdout").read_bytes() == (evidence / "build.stdout").read_bytes(),
            "changed compile/link recipes")
    commands = raw.decode().splitlines()
    require(commands == probe["commands"] and len(commands) == len(products), "header command evidence differs")
    outputs = []
    for command in commands:
        argv = shlex.split(command)
        if argv[:2] == ["ar", "-rcs"] and argv[2:] == ["libtoml.a", "toml.o"]:
            outputs.append(argv[2])
        else:
            require(argv and argv[0] == "cc" and "-o" in argv and argv.index("-o") + 1 < len(argv), "unexpected recipe")
            outputs.append(argv[argv.index("-o") + 1])
    require(set(outputs) == set(products), "six compile/link outputs required")


def check_preview(job, result, image):
    src = Path(__file__).resolve().parents[2] / "course/e13-e14/projects" / PREVIEW
    manifest = load(src / "manifest.json")
    binding = load(job / "draft/binding.json")
    require(load(job / "summary.json") == result, "job/matrix summary mismatch")
    fields = ("project_id", "profile_sha256", "candidate_sha256", "base", "target")
    require(all(result[k] == binding[k] == manifest[k] for k in fields), "registered preview binding differs")
    identity = {k: binding[k] for k in (*fields, "job_id", "trace_id")}
    require(identity["job_id"] == result["job_id"] and identity["trace_id"] == result["trace_id"], "identity mismatch")
    # Recompute every entry, including raw HTTP, full graphs, logs, patches and inspect outputs.
    inventory = load(job / "MANIFEST.json")
    actual = {p.relative_to(job).as_posix(): p for p in job.rglob("*")
              if p.is_file() and ".git" not in p.relative_to(job).parts and p != job / "MANIFEST.json"}
    require(actual.keys() == inventory.keys(), "job manifest coverage mismatch")
    for name, path in actual.items():
        require(not path.is_symlink() and inventory[name] == {"bytes": path.stat().st_size, "sha256": file_hash(path)},
                "job manifest mismatch: " + name)
    original = manifest["target_files"]
    require(load(job / "source-before.json") == original and result["changed_sources"] == ["Makefile"],
            "source binding differs")
    evidence = job / "repair/runtime/output/evidence"
    for name, expected in original.items():
        require(file_hash(job / "source-before-bytes" / name) == expected, "input snapshot: " + name)
        after = file_hash(job / "source-after-good-bytes" / name)
        require((after != expected) == (name == "Makefile") and file_hash(evidence / "repaired-source" / name) == after,
                "unexpected source change: " + name)
        require((file_hash(evidence / "header-sandbox" / name) != after) == (name == "toml.h"),
                "isolated header probe differs: " + name)

    draft = job / "draft"
    pair = manifest["baseline_pair"]
    require(binding["baseline_pair"] == pair and load(draft / "baseline-pair.json") ==
            dict(pair, candidate_sha256=manifest["candidate_sha256"]), "DRAFT pairing registration")
    for path, expected in ((job / "source-before-bytes/Dockerfile.broken", pair["Dockerfile.broken.C1"]),
                           (draft / "project/Dockerfile.broken", pair["Dockerfile.broken.proposed"]),
                           (draft / "iter-01/Dockerfile", pair["Dockerfile.broken.effective"]),
                           (draft / "iter-02/Dockerfile", manifest["candidate_sha256"])):
        require(file_hash(path) == expected, "DRAFT original/pair mismatch: " + str(path))
    build = load(draft / "result.json")
    first, second = build["attempts"]
    require(build["status"] == "SUCCEEDED" and build["candidate_sha256"] == manifest["candidate_sha256"]
            and first["build_exit_code"] != 0 and first["failure_class"] == "MISSING_MAKE"
            and second["build_exit_code"] == 0 and second["image_id"] == image, "incorrect DRAFT attempts")

    require(len(list((job / "http").glob("*-request.json"))) == len(STAGES), "six stage requests required")
    for num, stage in enumerate(STAGES, 1):
        prefix = f"{num:02d}-{stage}"
        req = load(job / "http" / (prefix + "-request.json"))
        require(all(req[k] == v for k, v in identity.items()) and req["profile"] == manifest["profile"]
                and req["protocol"] == "member2-e14-1", "request identity mismatch: " + stage)
        require(req["out"].endswith("/jobs/" + result["job_id"] + "/" + stage)
                and req["project"].endswith("/jobs/" + result["job_id"] + ("/base" if stage == "baseline-full" else "/target")),
                "request paths differ: " + stage)
        resp = load(job / "http" / (prefix + "-response.json"))
        resp_id = resp["binding"] if stage == "draft" else resp
        # Some runner versions carry the incremental image binding in the returned envelope.
        image_ok = (stage == "incremental" and "image_id" not in resp_id) or resp_id.get("image_id") == image
        require(resp_id["job_id"] == result["job_id"] and resp_id["trace_id"] == result["trace_id"]
                and image_ok and resp["status"] == "SUCCEEDED"
                and load(job / "http" / (prefix + "-http.json"))["status"] == 200, "response binding: " + stage)
        if num > 1:
            require(req["image_id"] == image, "request image differs")
        if stage == "incremental":
            for key, file in (("baseline_graph", "baseline-full/actual-graph.json"),
                              ("target_findings", "target-full/findings.json")):
                require(req[key].endswith("/" + result["job_id"] + "/" + file)
                        and req[key + "_sha256"] == file_hash(job / file), "broken source reference: " + key)

    env = load(job / "incremental/incremental-check.json")
    payload = load(job / "incremental/incremental-report.json")
    art, = env["artifacts"]
    payload_file = job / "incremental/incremental-report.json"
    require((env["job_id"], env["trace_id"], env["image_id"], env["commit"], env["profile_sha256"]) ==
            (result["job_id"], result["trace_id"], image, manifest["target"], manifest["profile_sha256"])
            and env["data"] == payload and payload["commit"] == manifest["target"]
            and payload["profile_sha256"] == manifest["profile_sha256"]
            and art == {"uri": "artifact://" + result["job_id"] + "/incremental-report.json",
                        "bytes": payload_file.stat().st_size, "sha256": file_hash(payload_file)}, "incremental source binding")
    expected_missing = {(target, dep) for target, deps in manifest["profile"]["missing_dependencies"].items() for dep in deps}
    require({(f["target"], f["dependency"]) for f in payload["findings"] if f["type"] == "MISSING"} == expected_missing,
            "wrong missing dependency set")
    blobs = manifest["image_git_blobs"]
    seven = {n: manifest["target_files"][n] for n in blobs}
    require(set(seven) == {"toml.c", "toml.h", "toml_extra.h", "toml_json.c", "toml_cat.c", "toml_sample.c", "Makefile"},
            "incorrect image source list")
    for name, expected in blobs.items():
        data = (draft / "project" / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == seven[name] and
                hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == expected,
                "baked source mismatch: " + name)
    ids = set()
    for path, operation in WORKERS.items():
        runtime = job / path
        request = load(runtime / "input/request.json")
        witness = load(runtime / "execution.json")
        response = load(runtime / "output/response.json")
        require(request["operation"] == witness["operation"] == response["operation"] == operation
                and response["status"] == "SUCCEEDED", "wrong worker operation")
        require(request["baked_files"] == witness["baked_source_sha256"] == response["baked_source_sha256"] == seven
                and request["baked_git_blobs"] == witness["baked_source_git_blobs"] == response["baked_source_git_blobs"] == blobs
                and request["profile_sha256"] == response["profile_sha256"] == manifest["profile_sha256"],
                "worker baked files/profile differ")
        cid = witness["container_id"]
        require(cid not in ids and re.fullmatch(r"[a-f0-9]{64}", cid), "reused container identity")
        ids.add(cid)
        observations = []
        for command in sorted(runtime.glob("*-inspect.command.json")):
            if load(command)["argv"] == ["docker", "inspect", cid]:
                raw, = load(command.with_name(command.name.replace(".command.json", ".stdout.log")))
                observations.append((raw["Id"], raw["Image"], raw["State"]["Status"], raw["State"]["ExitCode"]))
        require((cid, image, "exited", 0) in observations, "missing raw downstream container inspect")
    products = manifest["profile"]["products"]
    full = load(job / "final-full/findings.json")
    validation = load(job / "repair/runtime/output/evidence/validation.json")
    require(validation["accepted"] and all(validation["checks"].values()) and set(full["observed_targets"]) == set(products)
            and full["status"] == "SUCCEEDED" and not any(f["type"] == "MISSING" for f in full["findings"]),
            "incomplete whole project result")
    check_preview_probe(evidence, products)
    return {"baked_files": seven, "git_blobs": blobs, "baseline_pair": pair,
            "products": products, "manifest_files_checked": len(inventory)}


def check(root, expected_scope="B13_SHARED_COMPOSE_RUN"):
    matrix_path, = root.glob("matrix-*.json")
    matrix = load(matrix_path)
    require(expected_scope in ("B13_SHARED_COMPOSE_RUN", "B13_LOCAL_PREVIEW") and matrix["scope"] == expected_scope
            and matrix["status"] == "PASS", "requested matrix scope required")
    row, = matrix["records"]
    result = row["result"]
    require(result["status"] == "PASS" and row["scenario"] == "normal", "successful normal chain required")
    if expected_scope == "B13_LOCAL_PREVIEW":
        require(result.get("project_id") == PREVIEW and re.fullmatch(r"job-[0-9a-f]{32}", result["job_id"]),
                "invalid local preview job")
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
    details = {}
    if expected_scope == "B13_LOCAL_PREVIEW" or request["project_id"] == PREVIEW:
        details = check_preview(job, result, image)
        details["scope"] = expected_scope
    return {**details, "status": "PASS", "project_id": request["project_id"], "job_id": result["job_id"],
            "trace_id": result["trace_id"], "implementation_sha": result["implementation_sha"], "image_id": image,
            "operations": dict(operations), "whole_project_findings": findings["whole_project_findings"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--expected-scope", choices=("B13_SHARED_COMPOSE_RUN", "B13_LOCAL_PREVIEW"), default="B13_SHARED_COMPOSE_RUN")
    args = parser.parse_args()
    print(json.dumps(check(args.run, expected_scope=args.expected_scope), indent=2))
