# B13 ↔ A13 接口对齐记录

## 对齐基线

- 日期：2026-09-29
- B13 仓库：`ma058/2026-Devops-B13`
- B13 基线：`f1fa3a888fa6a4954ac32897ebeeced83c8a6411`
- A13 仓库：`Dufunare/2026-Devops-A13`
- A13 基线：`bc1ed352dc0b8ff9e77a69222a69deb03e49a618`
- A13 合并记录：`https://github.com/Dufunare/2026-Devops-A13/pull/2`
- 原始交付：A13 `docs/E2/B13_DELIVERY.md` 与本组收到的 `A13_to_B13_E2_delivery.md`

## 双方决定

| 主题 | 最终采用规则 | B13 落地位置 |
| --- | --- | --- |
| 公共 Job、状态与错误 | 接受公共字段和状态枚举；MD/RD 是 `SUCCEEDED.output`，系统执行错误进入 `error` | `contracts/schemas/`、`docs/E2/status-and-errors.md` |
| FULL_CHECK | repository、environment、configuration、project_root、clean/build command；输出 actual/declared graph 与 findings | 公共 Job Schema 与 A13 固定快照 |
| INCREMENTAL_CHECK | 先 FULL_CHECK 建 baseline；baseline commit/configuration 必须匹配 base commit/configuration | `ADR-003-baseline-policy.md`、校验器与反例 |
| Finding 路径 | 项目内路径均为相对 `project_root` 的 POSIX 路径；去除 `./`；禁止绝对路径、反斜杠和 `..` 越界；系统依赖不进入报告 | `scripts/verify_a13_interop.py` |
| location | `RESOLVED` 使用 A13 的 `location.path/line`；`UNRESOLVED` 不伪造行号，由调用方显式提供默认 Makefile 路径 | A13 互操作验证器与单测 |
| MDFixer 消费范围 | 只消费 `MISSING`，`REDUNDANT` 记录为 skipped，不拒绝整份混合报告 | REPAIR 契约、A13 归一化结果 |
| Artifact 访问 | 接受 `artifact://pair13/...` 逻辑 URI 加 repository-backed locator；消费方固定完整仓库 commit 和 repository_path | `contracts/artifact-access.md`、A13 manifest |
| Patch 复检 | Patch 绑定 base commit/configuration；A13 在隔离工作区应用、构建并重检后才决定是否形成正式 commit | `docs/E2/repair-contract.md` |
| REPAIR 正常结果 | `PATCH_ACCEPTED`、`NO_VALID_CANDIDATE`、`NOT_APPLICABLE` 均为 `SUCCEEDED`；字段约束按状态分支 | Job Schema、标准校验器、正反样例、单测 |
| 版本策略 | 新增可选字段同步双方样例/校验器；删除、改名、改语义或收紧必填性先讨论并升级版本 | 契约文档与 ADR |

## Artifact 互读结果

B13 已从 A13 `bc1ed352…` 实际读取并固定以下内容：

- FULL_CHECK actual graph、declared graph、MD/RD report
- INCREMENTAL_CHECK actual graph、MD report
- A13 finding report Schema

固定快照、上游原始字节 SHA-256 和来源路径见 `contracts/paired/a13/manifest.json`。执行：

```bash
python scripts/verify_a13_interop.py
```

验收覆盖：

- 来源仓库与完整 commit 固定
- 5 份 Artifact 和 1 份 Schema 可读，记录上游 SHA-256
- FULL_CHECK actual-declared 图差分与报告中的 1 条 MISSING、1 条 REDUNDANT 一致
- MDFixer 只消费 `config.h` 的 MISSING，跳过 `unused.h` 的 REDUNDANT
- INCREMENTAL 报告的 `UNRESOLVED` location 使用显式默认 `Makefile`，不生成虚假行号
- 绝对路径、`..`、Windows 反斜杠和 `./` 前缀均被拒绝

结构化结果见 `evidence/E3/2026-09-29-a13-interop/`。

## 证据边界

A13 固定提交中的报告与图均带有 `Synthetic E2 artifact; not a real ... execution result.` 标记，A13 README 和 Backlog 也把 BuildChecker/EChecker 复现列为后续工作。因此本次结果证明的是契约互读与 MDFixer 消费链路，不把合成样例记作真实检测器输出。B13 的四类 MDFixer 行为验证继续由课程固定 Oracle 和可重复脚本承担。


## finding-report 2.0 候选（2026-11-10 更新）<!-- V2_MARKER_20261110 -->

A13 于 2026-10-10 在提交 `c4364e96521a8729fe11695c030916e1746eca1b` 提出 finding-report 2.0 候选（Schema、正反样例、validator、测试，见 A13 `docs/E2/B13_REVIEW_RESPONSE_2026-10-10.md`）。B13 于 2026-11-10 完成复核并**接受该候选**：

- 固定快照：`contracts/paired/a13-v2/`（8 文件逐字节复制，upstream 与 snapshot SHA-256 一致，见 manifest.json）。
- 独立复核：`scripts/validate_v2.py` 为 B13 独立实现的 v2 语义校验器（不 import A13 validator）；`scripts/verify_a13_v2_interop.py` 36 项检查全过（复审修复后）——manifest 完整性、A13 有效样例接受、A13 五个负例按文档理由拒绝、MDFixer 消费策略（只消费 MISSING）在 v2 输入上不变。
- B13 v2 样例：`contracts/examples/v2/`——v1 合成样例与真实 E3 target 样例（fixture 提交 `84f6e9df…`，B13_MANUAL_ORACLE）各一份的 2.0 迁移，另含 6 个负例（oracle 携带 producer_job_id、UNRESOLVED 携带 line、evidence 项缺 detail、绝对路径依赖、finding 未知字段、finding commit 不匹配——与 A13 五个负例覆盖不同规则面）；迁移等价检查确认 finding 集合不变。
- 测试：`tests/test_e2_v2_contracts.py` 21 项（复审修复后新增 4 项规则用例）；全量回归 54 项通过。
- 证据：`evidence/E2/2026-11-10-a13-v2-interop/`。

**provisional 字段处置**：v1 中 finding 级 `makefile_path` 的基准目录语义自 R3 起标记 provisional、等 A13 确认；v2 删除该字段（RESOLVED 用 `location.path`，为相对 `repository` 项目根的 POSIX 路径），该未决项随 v2 采纳而终结。v1 样例、v1 固定快照与 `evidence/E3/2026-09-29-a13-interop/` 的 16/16 记录不改写。

### 复审修复（2026-11-10，响应成员1对 #27 的 Request Changes）

B13 独立校验器 `scripts/validate_v2.py` 的四处缺陷已修复（8 份 A13 固定原件未动）：

| 缺陷 | 修复 |
|---|---|
| `artifact_locator.uri` 为 null/空串/整数/数组时放行 | 先验 `isinstance(str)` 再匹配 `^artifact://pair13/`；空串同样拒绝 |
| 显式 `extensions: null` 被当作缺省放行（顶层与 finding 同病） | 区分「字段缺省」（允许）与「显式 null」（拒绝）；新增两个负例 |
| `PurePosixPath` 归一化 `a//b`、`a/./b`、`a/` 后被接受（A13 语义校验器拒绝） | `is_safe_path` 改为对原始字符串逐段检查，空段/`.`/`..` 一律拒绝；覆盖 dependency、location.path、artifact_locator.repository_path |
| `detector=[]`、`finding.type={}` 触发 TypeError 崩溃 | 所有 set 成员测试前先验类型，校验器只返回错误列表 |

新增 11 个差异化负例（invalid 目录增至 17 个）与 4 项规则测试；互读验证 36/36、契约测试 21/21、全量回归 54/54 通过；`evidence/E2/2026-11-10-a13-v2-interop/` 已重新生成。结构类型拒绝与 Draft 2020-12 正式校验器一致；原始路径的空段、`.` 和末尾斜线由 A13/B13 语义规则拒绝，不能声称固定 Schema 本身拒绝了全部此类路径。

### 冻结进度（对照 A13 PAIR_REVIEW 冻结条件）

| # | 条件 | 状态 |
|---|---|---|
| 1 | B13 接受 A13 v2 candidate 或提出明确 diff | 完成（无 diff） |
| 2 | B13 用独立 commit 更新 fixtures/validator/tests | 完成（PR #27，合并于 main `1d7f4839…`） |
| 3 | 双方交换完整 commit SHA | 完成：A13 `931563895a40df91a326cac5791e089d767e49a7` / B13 `1d7f4839eff567aa7037d431df86952f24076c4d` |
| 4 | B13 读取 A13 v2 report；A13 读取 B13 v2 REPAIR/report | 完成：A13 互读 B13 19 原件（2 有效接受、17 负例拒绝）；B13 重放 A13 16 项定向测试并读取 A13 6 样例（1 有效接受、5 负例拒绝） |
| 5 | 双方记录文件 SHA-256 | 完成：B13 manifest.json（19 文件全量）；A13 v2-interop.json（19 份记录），A13 validator SHA-256 `20ae9007cd184404ceb07080222d5af91dbb49d35805019e07d91e2ea56a4023` |
| 6 | 两边文档写入同一组固定 commit | **完成：双方共同标记 frozen（2026-11-16）** |

### v2 冻结登记回填（2026-11-16，成员3 依 A13 回执执行）

- 状态：**FROZEN_FIXED_PAIR**（A13 `pair13-finding-report-v2.freeze.json`）
- 固定对：A13 `931563895a40df91a326cac5791e089d767e49a7` / B13 `1d7f4839eff567aa7037d431df86952f24076c4d`（即实际互读执行版本；**不以后续文档 head 替换**）
- A13 冻结登记归档提交：`069ef09263bb08ca3deba541813e722013006fab`（A13 PR #16）；冻结登记脚本实际执行 `196d84ff89cee65afd678b1f5c48d6a28fb078f8`
- B13 公开 ACK：`evidence/coordination/20261116/B13_V2_ACK_20261116.md`（SHA-256 `367ff249…a8d5`，公共归档提交 `e3bc9a91`＝PR #33 head，待其合并）
- 范围：仅 E2 finding-report 2.0；E11 的 e11e12-1/e8e10-1 与运行时/环境验收为独立工作线，不在本冻结内
