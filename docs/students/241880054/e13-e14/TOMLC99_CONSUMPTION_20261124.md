# 成员一 tomlc99 正式消费回执

马宇航，241880054，苏州校区；2026-11-24。结论：**新 A13 三层绑定报告已被 B13 E11-B 实际消费，四阶段成功。** 本项可以关闭；E13–E14 整体验收仍按后续清单推进。

## 执行与来源

本轮由成员一授权 Codex 在 B13 服务器隔离目录辅助执行。使用成员一现有环境镜像、只读挂载固定源码与输入、新可写 OUT；外层与两个下游 worker 均 UID 10001。外层具有 docker.sock 能力，不能据“非 root”声称与宿主安全隔离。没有替其他成员署名，也未将辅助运行写成人工独立复跑。

运行时间：UTC 2026-11-24T01:22:57Z 至 2026-11-24T01:23:04Z（北京时间 09:22:57–09:23:04），CLI 退出码 0。生产 API 8081/8083 未更换，事后 8081 health 仍为 ok；本次不是旧生产 API 的 HTTP 任务。

| 记录 | 固定值 |
|---|---|
| A 源 job | `job-fd1b21e39d41474699e43815b402804e` |
| A 源 trace | `trace-ad14eb26d03f4129a38ab57ad626c72a` |
| A 实现源码 | `b55dd6717dbed2d6b6e825a1f554321c31b6b574` |
| A 原执行 | E11-A / orchestrator，无 DRAFT |
| B 消费 job | `job-15dcdf2c3ba24a1487aae245776684bf` |
| B 消费 trace | `trace-52029a6df41a43c2ba5c7a39758a5e7b` |
| B 实际运行源码 | `f05faf5bcd3496184c580dc30e710cc960bf0398` |
| #49 合并提交（与运行源码 tree 相同） | `be3b232342956aacd7edb9c3a320e36a0e0ec4d8` |
| C0 | `592fc6f3d2463a58fe7f60b8d255ed242740bec0` |
| C1 | `b2dda5513fe4a7d250493528800fe425cae459a5` |
| profile | `0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1`；仅 `toml.o` |
| 编排环境 image ID | `sha256:bd6407d706b8a3174a5444e1363cb0432f3e2eae70dcb0a36a7d1c1e0cb5afad` |
| 本轮 DRAFT 成品 image ID | `sha256:d60fbdbfff205562b47a8d738dde22a9502761c1680de8792cb5e451c220cdf3` |

## 核验与修复

1. 来件内 A13 原 ZIP 的 679 项清单、666 个唯一 artifact URI 全部核验；result → incremental-check → incremental-report 的 profile 三层一致，原始 job/trace 与独立摘要绑定均通过。C0/C1 的 152/154 份受跟踪源码逐 Git blob 对照，A 实现增量 bundle 也经前置提交、完整性与祖先链验证。
2. 固定消费者独立派生的 fixed-md 与成员二交付字节相同。实际 `fixed-md-input.json` SHA 为 `328ec838926af9eee76781563de20ccd4404ff4b77e7086318db66005ac6f9ef`；`fixed_report_binding.exchanged_hash_verified=true`，同时记录并确认 A 源 result/envelope/payload 摘要及 job/trace，没有给旧原件补写字段。
3. 四阶段为 `draft → fixed-md → repair → recheck`。DRAFT 第一轮真实失败分类 MISSING_MAKE；第二轮真实 docker build 退出 0，验证输出原字节 `7b7d0a`（`{}` 加换行）、退出 0。候选是固定手工响应回放，本命令没有调用模型；第二轮存在 CACHED 层，不宣称重新下载依赖或无缓存构建。
4. 下游 `validate`、`full` 两个实际容器均使用上述 DRAFT 不可变 ID，退出 0，工具及实际 worker 源码摘要与固定实现相符。没有在 orchestrator 回退执行下游。容器删除记录及事后 inspect 不存在的记录已归档。
5. 补丁只将 `toml.o: toml.c` 改为 `toml.o: toml.c toml.h toml_extra.h`。`accepted=true`，`build/header_change/no_missing/patch_applies/test` 五项均 true；头文件探针记录真实 `cc` 执行及目标 mtime 增长。
6. 复检范围内 `toml.o` 的 MISSING 为 0；完整检测仍保留范围外 `toml_json → toml.h`。只承诺约定范围成功，不写“全项目无缺失依赖”。C1 受跟踪文件仅工作副本 Makefile 变化，其他输入原字节保持；运行源码 1005 文件和输入清单 683 文件前后摘要一致。

最初一次准备尝试因恢复的 bare Git 缺少空 `refs/` 目录，在 pipeline 启动前退出 128；没有产生 B job，也不是拒绝 A 报告。仅在派生输入副本补齐空目录后，在新 OUT 重试成功。两次原件分别保留于 `evidence/` 与 `evidence-attempt02/`，未覆盖失败记录。

## 原件与复算

归档：`member1-tomlc99-formal-consumption-20261124.tar.gz`，866065 字节，SHA-256：

`6159962922a0b6805c9655e14cfd1cd3d69fc813abfbae190548d4ddade5cdc5`

已从服务器下载后重验：1384 项 manifest 完整覆盖（清单自身不列入），result 的 1347 份产物逐一匹配；合法 `.gitignore` 等隐藏源码保留，导出不含实验副本 `.git`。详细独立审计见 `formal-consumption-audit.md/json`，来件审计见 `audit-handoff.md/json`。

团队只读取阅位置：`/srv/b13-e13e14-handoff/tomlc99-consumption-20261124/`。成员二、成员三以已有本人账号读取；A13 使用负责人转交的完整 ZIP，不要求新增服务器权限。

原件关键路径（相对于 tar 解包根）：

- `inputs/request.json`：发出的完整请求；`inputs/fixed-md.json`、`inputs/candidate.Dockerfile`：固定输入。
- `evidence-attempt02/run-01/result.json`：原始结果，SHA `bb83e2d4225cb27a0b8cf394dacea5dab42fcbf8431ace3db626962ce56fef9e`。
- 同目录 `fixed-md-input.json`、`repair-plan.json`、`candidate.patch`、`validation/validation.json`、`validation/header-probe.json`、`final-full/findings.json`。
- 同目录 `draft-build/` 与 `image-execution/`：构建、worker、工具、执行与清理证据。
- `evidence-attempt02/container-command.json`、inspect、stdout/stderr、退出码和输入前后清单；`source-manifest.json`、`preparation.json` 绑定运行源码。

A 原 ZIP SHA：`91fda34e63294d9c6a58bf8b541d4c389c7ab018c511badaf91a70334db47e90`。本次收到的外层交接 ZIP SHA 为接收方复算 `3edf566905c480ef05a621a5c1edf55b1c6f62762deb1289e549ac79e7e0bc2e`；未附独立同名 sidecar，不把本次生成的摘要冒充发送方原件。内层 A 原包的独立书面摘要、完整 manifest 与逐工件核验均通过。

运行源码使用 `git archive` 导出；1005 文件中 1004 与 Git blob 原字节一致，一份既有 CSV 文档按仓库属性转换为 CRLF（规范化换行后与 Git 一致），运行代码全部匹配。前后 1005 项不变指实际导出文件清单，不把该 CSV 的传输换行转换隐藏为字节相同。

## 关闭范围与余项

已关闭：新三层绑定报告收件、独立派生回读、成员一实际 B 消费、A→B 任务映射和可取阅原件。#49 已经成员二最终批准并正常合并，没有管理员绕过。

尚需按实际证据完成：#46 的成员三最终审批；成员三四服务故障注入/恢复及与 A13 的正式服务联调；A13 在 B13 项目的正式任务/DRAFT 下游原件。已核验的 A13 恢复/C5 和成员三 normal 不要求重做，也不扩大为这些尚未交付的整链结论。

教师隐藏测试资料已随结项项目包保存。课程材料未提供独立提交入口，不新增单独申请待办；教师结果到达后补实际 H 行。本文不是最终结项声明，也不改变冻结 profile 范围。
