# B13 E13–E14 incremental integration

Course origin and boundaries: [`course/e13-e14/MATERIALS.md`](../../course/e13-e14/MATERIALS.md).

This directory is additive. Keep the E7, E8–E10, and E11–E12 workflows and regression tests. The four-role course scaffold is a fixture rehearsal; the current branch does not claim production deployment or general-project E14 acceptance.

When using Compose, set `E14_UID` and `E14_GID` to the identity creating the shared snapshots, and `E14_DOCKER_GID` to the host Docker socket group for DRAFT. CI derives these values from its Runner. This preserves Git ownership checks; do not add a global `safe.directory=*` exception. Defaults remain the teaching template's root identity until explicitly configured.

## Member 1 checks

On the Linux personal environment with the existing compiler/strace/vendor dependencies:

```bash
python3 -m unittest discover -s labs/e13e14/tests -p 'test_*.py' -v
python3 -m unittest discover -s labs/e11e12 -p 'test_*.py' -v
```

The member1 evidence driver runs inside the established non-root personal teaching container with the Docker socket group, SYS_PTRACE, read-only `/course`, and writable `/course/data` and `/course/work`:

```bash
python3 labs/e13e14/member1_run.py \
  --request data/integration-sample/e12.json \
  --out work/member1-e13-new-run
```

Prepare a fresh course fixture first using the existing host entry `python3 run_e11e12.py prepare`, or the in-container `prepare.py --name` option for a different unused dataset. Do not overwrite previous outputs. Docker access is privileged host capability even with a non-root container user; use the already authorized isolated lab environment.

The driver labels its detector `LOCAL_SIMULATED_A`, runs C1 report handoff/repair, C2 stale target, C3 byte tampering, and C8 on a temporary loopback instance of the existing asynchronous API. It is not an A13 cross-group acceptance record.

## Integrity and compatibility

The original A bytes and the B derived fixed-md bytes are distinct artifacts. Register their hashes and the converter source commit. Formal delivery must include an independently exchanged original result/archive digest and expected job/trace, not only hashes supplied inside an untrusted result file.

E11-B accepts the optional `fixed_report_sha256` field; when supplied, it must match the received bytes before constructing snapshots, invoking DRAFT or applying a patch. Old requests without the field remain supported, but cannot count as transport-hash verification.

Do not infer E14 schema compatibility or idempotency from E12. The course synchronous role API and existing durable asynchronous API are separate interfaces. Real project/profile and immutable DRAFT execution across role containers require the member2/member3 integration described in the assignment.
