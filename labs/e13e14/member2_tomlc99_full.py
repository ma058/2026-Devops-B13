"""Adapter for staged four-service runs of the frozen full tomlc99 project."""
import difflib
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

from project_profile import FLAGS, canonical, check_environment, run

BASE = "592fc6f3d2463a58fe7f60b8d255ed242740bec0"
TARGET = "b2dda5513fe4a7d250493528800fe425cae459a5"
CLI = ("toml_json", "toml_cat", "toml_sample")
PRODUCTS = ("toml.o", "libtoml.a", "libtoml.so.1.0", *CLI)
SOURCES = ("Makefile", "toml.c", "toml.h", "toml_extra.h", *(n + ".c" for n in CLI))
EDGES = {("toml.o", "toml.h"), ("toml.o", "toml_extra.h"), *((n, "toml.h") for n in CLI)}
MAKE_SHA = "9247cc0f838a47456213d49d4aed2af11c6ba4c17b67dfff81d58aa486fb2c15"
RULES = (
    (b"\ntoml.o: toml.c\n", b"\ntoml.o: toml.c toml.h toml_extra.h\n"),
    (b"\n$(EXEC): $(LIB)\n", b"\n$(EXEC): $(LIB)\n$(EXEC): .EXTRA_PREREQS = toml.h\n"),
)


def require(ok, error):
    if not ok:
        raise ValueError(error)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def repaired(original):
    require(digest(original) == MAKE_SHA, "UNSUPPORTED_MAKEFILE")
    for before, after in RULES:
        original = original.replace(before, after)
    return original


def check(project, profile):
    """Check the exact checkout and the only permitted post-repair Makefile."""
    check_environment()
    require(not any(name in os.environ for name in ("AR", "ARFLAGS", "LDLIBS", "LOADLIBES", "OUTPUT_OPTION",
                                                     "LINK.c", "COMPILE.c", "CPATH", "C_INCLUDE_PATH")),
            "UNSUPPORTED_BUILD_OVERRIDE")
    project = Path(project)
    require(not any((project / n).exists() for n in ("makefile", "GNUmakefile")), "UNSUPPORTED_MAKEFILE")
    require(not any(p.is_symlink() for p in project.rglob("*")), "UNSAFE_PATH")
    commit = run(["git", "rev-parse", "HEAD"], project).decode().strip()
    require(commit in (BASE, TARGET), "COMMIT_MISMATCH")
    names = set(SOURCES)
    if commit == BASE:
        names.remove("toml_extra.h")
    checkout = {p.name for p in project.iterdir() if p.suffix in (".c", ".h") or p.name == "Makefile"}
    require(checkout == names, "UNSUPPORTED_LAYOUT")
    tree = run(["git", "ls-tree", "-z", commit, "--", *sorted(names)], project)
    entries = [row.split(b"\t", 1) for row in tree.split(b"\0") if row]
    require({n.decode() for _, n in entries} == names, "SOURCE_BINDING_MISMATCH")
    for meta, name in entries:
        raw = (project / name.decode()).read_bytes()
        if name == b"Makefile":
            original = run(["git", "show", commit + ":Makefile"], project)
            require(raw == original or (commit == TARGET and raw == repaired(original)), "UNSUPPORTED_MAKEFILE")
            raw = original
        expected = meta.split()[2].decode()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected,
                "SOURCE_BINDING_MISMATCH")
    return commit


def _planned_input(project):
    """Read link inputs from the actual GNU Make recipe plan for this checkout."""
    plan = run(["make", "-Bn", "all"], project).decode().splitlines()
    recipes = {}
    for line in plan:
        words = shlex.split(line)
        if words and words[0] == "ar" and words[1:3] == ["-rcs", "libtoml.a"]:
            target = words[2]
            inputs = words[3:]
        else:
            require(words and words[0] == "cc" and "-o" in words, "UNSUPPORTED_BUILD_COMMAND")
            idx = words.index("-o")
            target = words[idx + 1]
            inputs = [w for w in words[1:idx] + words[idx + 2:] if not w.startswith("-")]
        require(target in PRODUCTS and target not in recipes, "UNSUPPORTED_BUILD_COMMAND")
        # Direct link/archive inputs are the build products passed by the recipe.
        recipes[target] = {"argv": words, "units": [w for w in inputs if w.endswith(".c")],
                           "products": [w for w in inputs if w in PRODUCTS]}
    require(set(recipes) == set(PRODUCTS), "INCOMPLETE_PRODUCT_SCOPE")
    return recipes


def scan(project, old, profile):
    from fullcheck import declaration_graph

    project = Path(project).resolve()
    commit = check(project, profile)
    profile_digest = digest(canonical(profile))
    if old is not None:
        require(old.get("commit") == BASE and old.get("profile_sha256") == profile_digest, "OLD_REPORT_BINDING_MISMATCH")
    recipes = _planned_input(project)
    headers = {p.name: digest(p.read_bytes()) for p in project.glob("*.h")}
    compiler = run(["cc", "--version"], project).decode().splitlines()[0]
    keys, actual, declared, findings = {}, {}, {}, []
    reused, refreshed = [], []
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "make-db.txt"
        db.write_bytes(run(["make", "-Bnp", "all"], project))
        graph = declaration_graph(db, project.as_posix())
    for target, recipe in recipes.items():
        units = recipe["units"]
        key = {"argv": recipe["argv"], "compiler": compiler, "headers": headers if units else {},
               "sources": {u: digest((project / u).read_bytes()) for u in units}}
        keys[target] = digest(canonical(key))
        if old and old.get("keys", {}).get(target) == keys[target]:
            actual[target] = sorted(set(old["actual"][target]))
            reused.append(target)
        else:
            deps = set(recipe["products"])
            for unit in units:
                raw = run(["cc", *FLAGS, "-MM", "-MT", target, unit], project).decode().replace("\\\n", " ")
                name, prerequisites = raw.split(":", 1)
                require(name == target, "INVALID_COMPILER_OUTPUT")
                observed = prerequisites.split()
                require(all(n in SOURCES for n in observed), "UNSUPPORTED_DEPENDENCY")
                deps.update(observed)
            actual[target] = sorted(deps)
            refreshed.append(target)
        declared[target] = sorted(graph[target]["dependencies"])
        observed = set(actual[target])
        specified = set(declared[target])
        for kind, deps in (("MISSING", observed - specified), ("REDUNDANT", specified - observed)):
            findings.extend({"type": kind, "target": target, "dependency": dep} for dep in sorted(deps))
    def identities(items):
        return {(f["type"], f["target"], f["dependency"]) for f in items}
    current, previous = identities(findings), identities(old["findings"] if old else [])
    return {"schema_version": "e8e10-1", "profile": profile["id"], "profile_sha256": profile_digest,
            "commit": commit, "actual": actual, "declared": declared, "findings": findings, "keys": keys,
            "reused": reused, "refreshed": refreshed, "added": sorted(current - previous),
            "resolved": sorted(previous - current)}


def patch(project, report, profile):
    commit = check(project, profile)
    require(commit == TARGET and report.get("commit") == TARGET, "STALE_REPORT")
    require(report.get("schema_version") == "e8e10-1", "SCHEMA_MISMATCH")
    require(report.get("profile_sha256") == digest(canonical(profile)), "PROFILE_HASH_MISMATCH")
    findings = report.get("findings")
    require(isinstance(findings, list), "INVALID_REPORT")
    missing = set()
    for f in findings:
        require(isinstance(f, dict) and f.get("type") in ("MISSING", "REDUNDANT")
                and f.get("target") in PRODUCTS and isinstance(f.get("dependency"), str), "INVALID_REPORT")
        if f["type"] == "MISSING":
            missing.add((f["target"], f["dependency"]))
    project = Path(project)
    before = (project / "Makefile").read_bytes()
    if digest(before) != MAKE_SHA:
        require(not missing, "STALE_REPORT")
        return "", []
    require(missing == EDGES, "UNEXPECTED_MISSING_DEPENDENCIES")
    after = repaired(before)
    delta = "".join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                         "a/Makefile", "b/Makefile"))
    return delta, [{"target": t, "dependency": dep} for t, dep in sorted(missing)]


def validate(project, patchfile, out, profile):
    from fullcheck import full_check

    project, out = Path(project), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    before = (project / "Makefile").read_bytes()
    checks, error = {}, None
    try:
        report = scan(project, None, profile)
        expected, _ = patch(project, report, profile)
        require(expected and Path(patchfile).read_bytes() == expected.encode(), "UNSAFE_PATCH")
        # The probe and strace collector work on separate copies. Only the Makefile
        # can be published and only after all assertions on both copies succeed.
        sandbox = out / "header-sandbox"
        shutil.copytree(project, sandbox, ignore=shutil.ignore_patterns(".git", *PRODUCTS))
        run(["git", "init", "--quiet"], sandbox)
        run(["make", "clean"], sandbox, out, "control-clean")
        original_commands = run(["make", "all"], sandbox, out, "control-build")
        run(["git", "apply", "--check", str(Path(patchfile).resolve())], sandbox, out, "apply-check")
        run(["git", "apply", str(Path(patchfile).resolve())], sandbox, out, "apply")
        updated = (sandbox / "Makefile").read_bytes()
        checks["patch_applies"] = updated == repaired(before)
        require(checks["patch_applies"], "EXACT_PATCH_REQUIRED")
        run(["make", "clean"], sandbox, out, "clean")
        commands = run(["make", "all"], sandbox, out, "build")
        checks["build"] = original_commands == commands
        result = run(["./toml_json"], sandbox, out, "empty-stdin")
        checks["test"] = result == b"{}\n" and (out / "empty-stdin.stderr").read_bytes() == b""

        # Run the real full collector on the repaired bytes before the header probe.
        # Its input is clean so cached binaries do not enter the reported source set.
        clean_copy = out / "repaired-source"
        shutil.copytree(sandbox, clean_copy, ignore=shutil.ignore_patterns(".git", *PRODUCTS))
        final = full_check(clean_copy, out / "full-recheck", clean_command="make clean", build_command="make all")
        checks["no_missing"] = (final["status"] == "SUCCEEDED" and set(final["observed_targets"]) == set(PRODUCTS)
                                and not any(f["type"] == "MISSING" for f in final["findings"]))
        (out / "recheck.json").write_bytes(canonical(final) + b"\n")

        def product_times():
            require(all((sandbox / n).stat().st_size > 0 for n in PRODUCTS), "MISSING_PRODUCT")
            return {n: (sandbox / n).stat().st_mtime_ns for n in PRODUCTS}

        times = product_times()
        time.sleep(1.1)
        header = sandbox / "toml.h"
        with header.open("ab") as f:
            f.write(b"\n/* full-project header rebuild probe */\n")
        rebuilt = run(["make", "all"], sandbox, out, "header-rebuild")
        after = product_times()
        checks["header_change"] = (rebuilt == original_commands and all(after[n] > times[n] for n in PRODUCTS))
        (out / "header-probe.json").write_bytes(canonical({"path": "toml.h", "argv": ["make", "all"],
            "before_mtime_ns": times, "after_mtime_ns": after, "commands": rebuilt.decode().splitlines()}) + b"\n")
        require(check(project, profile) == TARGET and (project / "Makefile").read_bytes() == before, "SOURCE_CHANGED")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        error = str(exc)
    accepted = len(checks) == 5 and all(checks.values()) and error is None
    if accepted:
        with tempfile.NamedTemporaryFile(dir=project, delete=False) as tmp:
            staged = Path(tmp.name)
            tmp.write(updated)
        try:
            shutil.copymode(project / "Makefile", staged)
            os.replace(staged, project / "Makefile")
        finally:
            staged.unlink(missing_ok=True)
    unchanged = (project / "Makefile").read_bytes() == before
    verdict = {"accepted": accepted, "checks": checks, "error": error, "rollback": not accepted and unchanged,
               "source_unchanged": unchanged, "profile_sha256": digest(canonical(profile)), "success_scope": list(PRODUCTS)}
    (out / "validation.json").write_bytes(canonical(verdict) + b"\n")
    return verdict
