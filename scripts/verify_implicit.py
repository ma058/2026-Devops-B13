"""Run the E3 implicit-rule reference and rejection tests in temp copies.

Requires Linux with GNU Make, a C compiler, and Git. This does not execute the
future MDFixer implementation or A13 EChecker; it checks the manual Oracle.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "mdfixer" / "implicit-style"
SOURCE_FILES = ("Makefile", "main.c", "config.h")


def run(directory: Path, *args: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    command = list(args)
    result = subprocess.run(command, cwd=directory, text=True, capture_output=True, check=False)
    print(f"$ {' '.join(command)}\nexit={result.returncode}\n{result.stdout}{result.stderr}")
    if expect_success and result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(command)}")
    if not expect_success and result.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {' '.join(command)}")
    return result


def copy_fixture(destination: Path) -> None:
    destination.mkdir(parents=True)
    for name in SOURCE_FILES:
        shutil.copy2(FIXTURE / name, destination / name)


def change_value(destination: Path, value: int) -> None:
    # Keep the file's modification time later than the compiled object.
    time.sleep(1.1)
    (destination / "config.h").write_text(f"#define VALUE {value}\n", encoding="utf-8")


def program_output(destination: Path) -> str:
    return run(destination, "./app").stdout.strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert '#include "config.h"' in (FIXTURE / "main.c").read_text(encoding="utf-8")
    assert "config.h" not in (FIXTURE / "Makefile").read_text(encoding="utf-8")
    print("ORACLE=B13_MANUAL_ORACLE; detector was not run")

    with tempfile.TemporaryDirectory(prefix="b13-e3-implicit-") as temporary:
        base = Path(temporary)
        before = base / "before"
        after = base / "after"
        rejected = base / "rejected"
        for directory in (before, after, rejected):
            copy_fixture(directory)

        run(before, "make")
        assert program_output(before) == "1"
        original_hash = digest(before / "app")
        change_value(before, 2)
        run(before, "make")
        assert program_output(before) == "1", "unpatched build unexpectedly tracked config.h"
        print("PASS before patch: header-only change leaves stale output 1")

        run(after, "git", "apply", "--check", str(FIXTURE / "reference.patch"))
        run(after, "git", "apply", str(FIXTURE / "reference.patch"))
        run(after, "make")
        assert program_output(after) == "1"
        repaired_hash = digest(after / "app")
        assert repaired_hash == original_hash, "clean build artifact changed after repair"
        print(f"clean_build_sha256_before={original_hash}")
        print(f"clean_build_sha256_after={repaired_hash}")
        dependencies = (after / "main.d").read_text(encoding="utf-8")
        assert "main.o:" in dependencies and "config.h" in dependencies
        change_value(after, 3)
        build = run(after, "make")
        assert "-MMD -MP" in build.stdout, "header change did not trigger compiler"
        assert program_output(after) == "3"
        print("PASS after patch: .d tracks header and rebuild outputs 3")
        print("PASS clean-build artifact SHA-256 unchanged at VALUE=1")

        run(rejected, "git", "apply", "--check", str(FIXTURE / "invalid.patch"))
        run(rejected, "git", "apply", str(FIXTURE / "invalid.patch"))
        run(rejected, "make", expect_success=False)
        shutil.copy2(FIXTURE / "Makefile", rejected / "Makefile")
        run(rejected, "make")
        assert program_output(rejected) == "1"
        print("PASS invalid candidate rejected; original Makefile restored")

    print("All implicit fixture checks passed. A13 EChecker recheck remains pending.")


if __name__ == "__main__":
    main()
