# B13 finding-report 2.0 样例（v2 迁移）

本目录是 B13 对 Pair13 finding-report 2.0 候选（A13 提交
`c4364e96521a8729fe11695c030916e1746eca1b`，2026-10-10 引入）的正式采纳与迁移：
B13 侧 v2 正反样例、B13 独立语义校验器 `scripts/validate_v2.py`、
互读验证 `scripts/verify_a13_v2_interop.py` 与测试
`tests/test_e2_v2_contracts.py`。

## v1 → v2 字段映射

| v1（schema 1.0） | v2（schema 2.0 候选） | 说明 |
| --- | --- | --- |
| `findings[].makefile_path` | 删除；RESOLVED 时用 `location.path` | **provisional 字段就此终结**：v1 中 `makefile_path` 的基准目录语义（相对仓库根还是项目根）从未与 A13 冻结；v2 由 `location.path` 统一为相对 `repository`（项目根）的 POSIX 路径 |
| `findings[].location.line/declaration` | `location.status=RESOLVED` 时保留 | 语义不变 |
| （无） | `location.status=UNRESOLVED` + `reason` | UNRESOLVED 禁止携带 path/line/declaration，不伪造行号；由调用方显式提供默认 Makefile 路径（与 v1 pair-review 决定一致） |
| `findings[].evidence: string` | `evidence: [{kind, detail, uri?}]` | 结构化数组，至少一项 |
| （无） | `findings[].finding_id` | 逐条唯一标识，便于跨组引用 |
| 顶层 `detector: INSTRUCTOR_ORACLE`（单一） | `detector` 五值枚举 | 新增 `A13_MANUAL_ORACLE`/`B13_MANUAL_ORACLE` 区分自建人工样例来源 |
| 顶层 `producer_job_id` 任意 | 仅 BUILDCHECKER/ECHECKER 必填 `job-*`；oracle/manual 必须为 null | 区分真实工具输出与人工 Oracle |
| `findings[].commit/configuration_id` 必填 | 可选；存在时必须等于顶层 | v2 语义规则（A13 文档明示） |
| （无） | `artifact_locator` 正式化为可选结构 | uri + repository_url/commit/path + sha256 |
| （无） | `extensions` 命名空间 `a13.*/b13.*/pair13.*` | 核心对象关闭任意额外字段 |

## 文件清单

- `md-report.valid.json`——v1 合成样例 `contracts/examples/md-report.json` 的 2.0 迁移
  （INSTRUCTOR_ORACLE；验证器 `verify_a13_v2_interop.py` 的等价检查确认 finding 集合不变）
- `md-report.e3-target.valid.json`——真实 E3 target-style fixture
  （`fixtures/mdfixer/target-style`，引入提交 `84f6e9df…`，B13_MANUAL_ORACLE）
  的 2.0 迁移
- `invalid/oracle-with-producer-job.json`——oracle/manual 报告携带 producer_job_id（拒绝）
- `invalid/unresolved-with-line.json`——UNRESOLVED 携带 line（拒绝；A13 负例用的是 path，此为另一变体）
- `invalid/evidence-item-missing-detail.json`——evidence 项缺 detail（拒绝）
- `invalid/unsafe-dependency-absolute.json`——依赖为绝对路径 `/etc/passwd`（拒绝；A13 负例用 `../` 穿越）
- `invalid/unknown-finding-field.json`——finding 内未知核心字段 `severity`（拒绝；A13 负例在顶层）
- `invalid/finding-commit-mismatch.json`——finding 级 commit 与顶层不一致（拒绝；v2 新增语义规则）

B13 十七个负例与 A13 五个负例覆盖不同规则面（含 2026-11-10 复审修复批次：locator uri 类型、显式 null extensions、路径归一化变体、不可哈希类型），共同确认双方对 v2 边界的理解一致。

## 冻结状态

按 A13 `docs/E2/PAIR_REVIEW.md` 的冻结条件：B13 已确认候选并产出 v2 样例
（本目录）；待 A13 读取本目录样例、双方交换固定 commit 与 SHA-256 后，
两侧文档共同标记 frozen。v1 样例与 `evidence/E3/2026-09-29-a13-interop/`
保持不动。

## 运行

```bash
python scripts/verify_a13_v2_interop.py     # 互读验证 + 证据生成
python -m unittest tests.test_e2_v2_contracts -v
```
