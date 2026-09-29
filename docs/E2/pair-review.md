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
