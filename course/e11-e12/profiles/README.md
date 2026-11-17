# Restricted tomlc99 release integration

This profile is specific to the received A13 tomlc99 source, C0
`592fc6f3d2463a58fe7f60b8d255ed242740bec0` and C1
`b2dda5513fe4a7d250493528800fe425cae459a5`.
The upstream project is https://github.com/cktan/tomlc99; retain its license and
received Git history. The Makefile fixture is copied byte-for-byte from that
audited C1; its SHA-256 is in the profile.

Both `pipeline.execute` and `consume_report.consume` accept an explicit profile
object and the SHA-256 of sorted, compact UTF-8 JSON (`project_profile.canonical`).
The independent consumer CLI uses `--profile FILE --profile-sha256 HASH`.
Only this exact version is accepted. Non-target Makefile bytes must remain
identical to the audited template. Only missing root-level C/header prerequisites
of `toml.o` can be added. The teaching parser and mixed rules remain unchanged.

Release flags are ordered: `-std=c99 -Wall -Wextra -fpic -O2 -DNDEBUG`.
Make's effective flags and compiler are checked inside the selected image.
Environment overrides, unknown profile fields, wrong hashes and stale reports
fail explicitly. The incremental cache key includes compiler identity/version,
effective flags, profile hash, target mapping, Makefile and root source bytes.

The new candidate installs git and strace in addition to build-essential. It is
a new immutable DRAFT image, not the old A13 image. Downstream full/scan/validate
operations use actual containers, copy transport, inspected image IDs, worker
code hashes and tool versions. No missing-tool fallback exists. Header validation
requires an observed successful compiler exec with exact flags and a newer
object timestamp; object hash changes are not required for a comment-only edit.

Success is scoped to `toml.o`. Full findings, including the known
`MISSING(toml_json, toml.h)`, are retained. This is not whole-project zero MD and
does not certify a new A13 HTTP exchange. Received A13 reports are preserved;
the E11-B fixed oracle and new E12 incremental report are labeled as member2
outputs. A separate consumer verifies and preserves the new report's original
bytes and both transfer hashes.

`run_member2_real_project.py formal` performs actual server acceptance; `http`
uses a dedicated store and own loopback port 8082. Neither mode has been marked
passed merely by the portable contract tests. All run directories must be new.
