# B13 E4 最终交付报告

## 1. 交付信息

- 小组：B13（3 人）
- 服务：DRAFT
- 仓库：<https://github.com/ma058/2026-Devops-B13>
- E4 环境与运行基线：`519ca0fce2a5417e3f855a101bc5c938252a03d5`
- 总集成 PR：[#13](https://github.com/ma058/2026-Devops-B13/pull/13)
- 最终交付标签：[`e4-complete-2026-10-12`](https://github.com/ma058/2026-Devops-B13/tree/e4-complete-2026-10-12)
- 结论：三名成员均在独立学号目录检出同一运行基线，完整执行 E4 流程并得到一致结论。

运行基线固定为已完成服务器完整运行的环境代码提交。其后的提交只增加脱敏报告、互查记录和交付说明，不改变 DRAFT 镜像、依赖锁、测试或扫描逻辑。

## 2. 三人独立运行结果

| 成员 | 学号 | 个人目录 | 成功证据目录 | 测试 | 冒烟 | 最终扫描 |
| --- | --- | --- | --- | --- | --- | --- |
| 成员1 ma058 | `241880054` | `/root/241880054/draft` | `work/20261009-224916/` | `4 passed` | 正确识别 `make: not found`，`passed: true` | 通过 |
| 成员2 Lacrym1ra | `241880091` | `/root/241880091/draft` | `work/20261011-150116/` | `4 passed` | 正确识别 `make: not found`，`passed: true` | 通过 |
| 成员3 yqy241880115 | `241880115` | `/root/241880115/draft` | `work/20261010-140139/` | `4 passed` | 正确识别 `make: not found`，`passed: true` | 通过 |

三份 `toolchain.lock` 的关键版本一致：Git `2.47.3`、Docker CLI `28.5.1`、Python `3.13.14`、pytest `8.4.2`。镜像名按学号隔离；镜像 ID、时间、耗时和缓存命中属于允许差异。完整说明见[三人运行结果对照](THREE_MEMBER_COMPARISON.md)。

## 3. 可重复工程环境

- `Makefile` 提供 `doctor → build → test → smoke → scan` 一键入口。
- 基础镜像固定 digest，Python 依赖使用带哈希锁文件。
- `scripts/doctor.py` 记录服务器资源、Docker 工具和仓库级 Git 身份。
- `services/draft/` 在非 root 用户下运行，并启用 `no-new-privileges`。
- 冒烟测试故意使用缺少 `make` 的破损 Dockerfile；内层构建失败、外层识别成功是预期结果。
- 三人的正式运行均固定到同一完整 40 位 SHA，未把后续纯文档提交误当作运行基线。

## 4. 密钥与运行安全

- `.env` 权限为 `600`，且未被 Git 跟踪；`work/` 保持忽略。
- 工作区、Git 历史和镜像元信息扫描均未发现真实密钥。
- 三人分别完成自行构造的假 Key 拒绝测试，删除假文件后复检通过；假 Key 未提交或推送。
- Docker TCP API 端口 `2375/2376` 未开放。
- `/var/run/docker.sock` 只用于课程服务器受控实验；它等价于宿主机高权限能力，不适合作为公开或不受信环境的部署方式。

## 5. A13 跨组互查

- A13 仓库：<https://github.com/Dufunare/2026-Devops-A13>
- A13 实际运行 SHA：`b755aff8df18cd363a2e556b201a7b3a240e1a44`
- A13 公开文档快照：`be3bae491dae139e7b592f9e6b7f4b8a95b16792`
- B13 已核对 A13 的 README 入口、环境、构建、测试、冒烟与密钥扫描说明。
- 成员2已在 A13 的 Pair13 Issue 留下[可追溯互查回复](https://github.com/Dufunare/2026-Devops-A13/issues/4#issuecomment-6106805327)。

互查只交换仓库 URL、完整提交 SHA、README 入口和脱敏结论，不包含服务器地址、密码、Token、`.env` 或原始 `work/`。

## 6. GitHub 协作记录

| 内容 | 作者 | PR | 非作者复核 |
| --- | --- | --- | --- |
| E4 环境、脚本、首次运行记录 | 成员1 | [#13](https://github.com/ma058/2026-Devops-B13/pull/13) | 成员3 Approve |
| 安全核验、成员3运行记录、三人对照初稿 | 成员3 | [#14](https://github.com/ma058/2026-Devops-B13/pull/14) | 成员2提出具体意见；成员1最终 Approve |
| 成员2运行记录、A13 互查、三人对照补全 | 成员2 | [#15](https://github.com/ma058/2026-Devops-B13/pull/15) | 成员1最终 Approve |

个人提交、PR、Review 与报告路径详见[贡献登记表](../../CONTRIBUTIONS.md)。

## 7. 最终验收结论

- 15 份有效契约样例通过，10 份无效样例均按预期拒绝。
- 33 项 Python 单元测试全部通过。
- A13 契约互操作 16 项检查全部通过。
- 三人服务器运行的源码 SHA、关键工具版本和验收结论一致。
- 三份脱敏个人报告、三人对照、A13 互查和贡献登记均已进入最终交付。
- 最终版本由 `e4-complete-2026-10-12` 标签固定，可直接作为 E5 起点。

## 8. 提交内容

课程平台若只能上传一个文件，提交由最终标签导出的 `2026-Devops-B13-E4-2026-10-12.zip`。若允许同时填写链接，附仓库地址、总 PR #13 和最终标签链接。
