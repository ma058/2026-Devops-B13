#!/usr/bin/env bash
# Usage: bash labs/e13e14/run_shared_member2.sh IMAGE START_PORT [normal|smoke|C4|C5]
set -euo pipefail
umask 077
if [[ $# -lt 2 || $# -gt 4 ]]; then
  echo 'usage: run_shared_member2.sh IMAGE START_PORT [normal|smoke|C4|C5] [PROJECT_ID]' >&2
  exit 2
fi
image=$1
start_port=$2
mode=${3:-normal}
project_id=${4:-b13-level-v1}
scenario=$mode
case "$mode" in
  smoke) scenario=normal ;;
  normal|C4|C5) ;;
  *) echo 'unknown scenario' >&2; exit 2 ;;
esac
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONDONTWRITEBYTECODE=1
setup=$(python3 labs/e13e14/member2_setup.py --shared --image "$image" --port-start "$start_port" --scenario "$scenario" --project "$project_id")
session=$(printf '%s\n' "$setup" | sed -n 's/^M2_E14_SESSION=//p')
[[ -f "$session" && -O "$session" ]]
# shellcheck disable=SC1090
source "$session"
printf 'SESSION=%s\nRUN=%s\n' "$session" "$M2_E14_RUN"
dc=(docker compose -p "$M2_E14_PROJECT" -f "$M2_E14_BASE_COMPOSE" -f "$M2_E14_COMPOSE")
diag="$M2_E14_RUN/diagnostics"
mkdir -m 700 "$diag"
printf '%s\n' "$mode" > "$diag/mode.txt"
id > "$diag/identity.txt"
date -u +%FT%TZ > "$diag/started-utc.txt"
touched=0
finish() {
  local rc=$? capture=0 cleanup=0 verification=0 scan_rc=0
  trap - EXIT INT TERM
  set +e
  printf '%s\n' "$rc" > "$diag/client.exit.txt"
  if ((touched)); then
    "${dc[@]}" ps -a > "$diag/compose-ps.log" 2>&1 || capture=1
    for role in buildchecker echecker draft mdfixer; do
      "${dc[@]}" logs --no-color --no-log-prefix "$role" > "$diag/$role.log" 2>&1 || capture=1
    done
    "${dc[@]}" down > "$diag/compose-down.log" 2>&1 || cleanup=1
  fi
  date -u +%FT%TZ > "$diag/ended-utc.txt"
  printf 'capture=%s\ncleanup=%s\n' "$capture" "$cleanup" > "$diag/capture-exit.txt"
  if ((rc == 0 && capture == 0 && cleanup == 0)) && [[ $mode == normal ]]; then
    python3 labs/e13e14/verify_member2_shared.py "$M2_E14_RUN" > "$diag/verify.log" 2>&1 || verification=1
  fi
  python3 labs/e13e14/member2_evidence.py "$M2_E14_RUN" > "$M2_E14_RUN/diagnostics-scan.log" 2>&1
  scan_rc=$?
  printf 'CLIENT_EXIT=%s CAPTURE_EXIT=%s CLEANUP_EXIT=%s VERIFICATION_EXIT=%s DIAGNOSTIC_SCAN_EXIT=%s\n' \
    "$rc" "$capture" "$cleanup" "$verification" "$scan_rc"
  if ((scan_rc != 0)); then echo 'STOP: inspect diagnostics-scan.log locally before sharing'; exit 1; fi
  if ((rc || capture || cleanup || verification)); then
    echo 'SHARED_RUN=FAILED (retained diagnostics; export as a failed run if needed)'
    exit 1
  fi
  printf 'SHARED_RUN=PASS MODE=%s\n' "$mode"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
"${dc[@]}" config --quiet
touched=1
"${dc[@]}" up -d --wait > "$diag/compose-up.log" 2>&1
if [[ $mode == smoke ]]; then
  PYTHONPATH=labs/e13e14 python3 - "$M2_E14_CONFIG" "$diag/health.json" <<'PY'
from pathlib import Path
import json, sys
from member2_run import health
config = json.loads(Path(sys.argv[1]).read_bytes())
Path(sys.argv[2]).write_text(json.dumps(health(config["ports"]), indent=2) + "\n")
PY
else
  python3 labs/e13e14/member2_run.py --config "$M2_E14_CONFIG" --scenario "$scenario" 2>&1 | tee "$diag/client.log"
fi
