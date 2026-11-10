# E2 Pair13 finding-report 2.0 候选互读验证（B13 侧）

- 运行时间（UTC）：2026-11-10T06:38:41.316198+00:00
- A13 固定提交：`c4364e96521a8729fe11695c030916e1746eca1b`（v2 候选引入提交，2026-10-10）
- B13 立场：接受该 2.0 候选；冻结待 A13 读取 B13 v2 样例并回写固定提交后完成

| 检查 | 结果 | 说明 |
| --- | --- | --- |
| manifest.source | PASS | pinned c4364e96521a |
| sha256.schemas/pair13-finding-report-v2.schema.json | PASS | 96f7374f484ad55ddab56989eaf9fbffb8d5d2636df7520be648ba9af2303f3e |
| sha256.examples/md-report.valid.json | PASS | 5d4682258615043bc1211ef60a8979daf9f38ebcfca0468728ace279138a83e9 |
| sha256.examples/invalid/empty-evidence.json | PASS | b60dd63eb4872a9728cda7a7ea64070f68b9b42ab1ab697dda647ca1f75e1a2a |
| sha256.examples/invalid/tool-without-producer-job.json | PASS | 20acea313d0a0d682e4f0296791334963b2f8068a8ae57f96835bbcf24eec82c |
| sha256.examples/invalid/unknown-core-field.json | PASS | 59361215180a89e6be001d56e468549c7a1145f514883059fed8d4de95c0972c |
| sha256.examples/invalid/unresolved-with-path.json | PASS | 6abe55dc6a94ca006c3cab27e8fbf84d6291f80395cda94a37152dc61903fe9f |
| sha256.examples/invalid/unsafe-dependency.json | PASS | 0d4e8235ed06f82c71c6731c9e4e1e0fc551f9ab8d5e31eeb3d3a22d576903ab |
| sha256.validator/validate_e2_v2.py | PASS | d3fe4f9da364ce5fa9e4394eb9c45ce9b90d34fb77bdf866050510c2e4941804 |
| a13.valid.accepted | PASS | accepted by B13 validator |
| a13.invalid.empty-evidence.json | PASS | findings[0].evidence: non-empty array required |
| a13.invalid.tool-without-producer-job.json | PASS | producer_job_id: real detector output requires a job-* id |
| a13.invalid.unknown-core-field.json | PASS | root: unknown core fields ['note'] |
| a13.invalid.unresolved-with-path.json | PASS | findings[0].location: unknown core fields ['path'] |
| a13.invalid.unsafe-dependency.json | PASS | findings[0].dependency: expected safe project-relative POSIX path |
| a13.consumption.missing_only | PASS | consumed=['config.h'], skipped=['unused.h'] |
| b13.valid.md-report.valid.json | PASS | valid |
| b13.valid.md-report.e3-target.valid.json | PASS | valid |
| b13.invalid.evidence-item-missing-detail.json | PASS | findings[0].evidence[0].detail: non-empty string required |
| b13.invalid.finding-commit-mismatch.json | PASS | findings[0].commit: must equal repository.commit when present |
| b13.invalid.oracle-with-producer-job.json | PASS | producer_job_id: oracle/manual reports must not carry producer_job_id |
| b13.invalid.unknown-finding-field.json | PASS | findings[0]: unknown core fields ['severity'] |
| b13.invalid.unresolved-with-line.json | PASS | findings[0].location: unknown core fields ['line'] |
| b13.invalid.unsafe-dependency-absolute.json | PASS | findings[0].dependency: expected safe project-relative POSIX path |
| b13.migration.equivalence | PASS | v1=[('MISSING', 'main.o', 'config.h'), ('REDUNDANT', 'main.o', 'unused.h')] v2=[('MISSING', 'main.o', 'config.h'), ('REDUNDANT', 'main.o', 'unused.h')] |

说明：
- A13 固定提交中的样例仍为 synthetic contract fixtures；本验证证明 v2 契约互读、
  语义校验与 MDFixer 消费链路，不表示 BuildChecker/EChecker 已运行。
- B13 的 6 个负例与 A13 的 5 个负例覆盖不同规则面（见脚本头注释），共同确认
  双方对 v2 边界的理解一致。
- v1→v2 语义等价检查确认迁移未改变 finding 集合。
