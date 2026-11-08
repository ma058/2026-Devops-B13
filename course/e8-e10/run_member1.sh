#!/usr/bin/env bash
# Member 1 host-side evidence capture; run from the personal repository root.
set -euo pipefail
test "$(git config --local user.name)" = 241880054
test -z "$(git status --porcelain)"
IMAGE=course-e8e10:241880054
OUT="work/member1-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
git rev-parse HEAD > "$OUT/student-source-commit.txt"
docker image inspect "$IMAGE" --format '{{.Id}}' > "$OUT/environment-image-id.txt"
git status --porcelain > "$OUT/source-status.txt"
uname -a > "$OUT/host-system.txt"
free -m > "$OUT/host-memory.txt"
df -h . > "$OUT/host-disk.txt"
docker version > "$OUT/docker-version.txt"
docker run --rm --network none "$IMAGE" cat /opt/toolchain.lock > "$OUT/toolchain.lock"
# Source is mounted read-only; only this run's OUT is mounted writable.
# The helper uses the already authorized host account for Docker administration.
if [ "$(id -u)" = 0 ]; then
  chown 10001:10001 "$OUT"
  RUN_USER=10001:10001
else
  RUN_USER="$(id -u):$(id -g)"
fi
printf '%s\n' "$RUN_USER" > "$OUT/container-user.txt"
execute() {
  local label="$1"; shift
  printf '%q ' "$@" > "$OUT/$label.command.txt"
  printf '\n' >> "$OUT/$label.command.txt"
  set +e
  "$@" 2>&1 | tee "$OUT/$label.log"
  local result=${PIPESTATUS[0]}
  set -e
  printf '%s\n' "$result" > "$OUT/$label.exit-code.txt"
  return "$result"
}
execute tests docker run --rm --network none --cap-add SYS_PTRACE \
  --user "$RUN_USER" -e HOME=/tmp -v "$PWD:/course:ro" -v "$PWD/$OUT:/course/$OUT:rw" -w /course "$IMAGE" \
  python3 -m unittest discover -s labs/e8e10 -p 'test_*.py' -v
execute experiments docker run --rm --network none --cap-add SYS_PTRACE \
  --user "$RUN_USER" -e HOME=/tmp -v "$PWD:/course:ro" -v "$PWD/$OUT:/course/$OUT:rw" -w /course "$IMAGE" \
  python3 labs/e8e10/member1_run.py --out "/course/$OUT/experiments"
printf '%s\n' "$OUT" > work/member1-latest.path
printf 'EVIDENCE=%s\n' "$OUT"
