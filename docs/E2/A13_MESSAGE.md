# 发给 A13 的接口对齐消息

## 发送前由 B13 补全

- B13 仓库：<https://github.com/ma058/2026-Devops-B13>
- 契约分支：`member1/e2-contracts-e3-implicit`（发送前确认已推送）
- 契约 Commit SHA：`af194c40ffd1394fb56cc9f5b2367b7feffb5a3b`（E2 Schema、样例和校验器）
- GitHub PR：`【创建后填写；若尚无 PR，写“待创建”】`
- B13 联系人及联系方式：`【填写】`
- 建议交流时间或回复期限：`【填写】`

> 当前公共契约、A13 服务专有字段和 `artifact://` 规则均为 B13 草案。只有 A13 在双方可见的 Issue、PR 或会议记录中确认后，才能标记为正式约定。

## 可直接发送的正文

A13 同学好，我们是配对组 B13，负责 DRAFT 和 MDFixer；了解到 A13 负责 BuildChecker 和 EChecker。B13 已提交 E2 公共 Job/Artifact 契约草案和可校验样例，希望双方完成一次字段对齐和样例互审。

仓库：<https://github.com/ma058/2026-Devops-B13>

请以本消息上方填写的契约分支和完整 Commit SHA 为准，避免双方查看不同版本。关键文件如下：

- 公共请求 Schema：`contracts/schemas/create-job.schema.json`
- 公共任务结果 Schema：`contracts/schemas/job.schema.json`
- Artifact Schema：`contracts/schemas/artifact.schema.json`
- 四类有效样例：`contracts/examples/`
- 预期拒绝的反例：`contracts/examples/invalid/`
- 状态与错误约定：`docs/E2/status-and-errors.md`
- Artifact 访问草案：`contracts/artifact-access.md`
- baseline 决策记录：`docs/E2/ADR-003-baseline-policy.md`

希望 A13 对以下事项逐项回复“接受 / 建议修改 / 尚未实现”，并在建议修改时给出字段示例：

1. **公共 Job 字段**：是否接受 `schema_version`、`job_id`、`trace_id`、`job_type`、`status`、`input`、`output`、`error`？是否接受当前状态枚举 `QUEUED/RUNNING/SUCCEEDED/FAILED/TIMED_OUT/CANCELLED`？
2. **FULL_CHECK 与 INCREMENTAL_CHECK**：请提供各一份最小有效请求和成功结果 JSON，以及至少一份预期拒绝的输入。请说明 `build_command`、`project_root`、`configuration_id`、`base_commit`、baseline 和实际依赖图分别如何表达。
3. **baseline 策略**：E2 课件要求缺少 baseline 的增量请求被拒绝；论文允许先 clean build 建立历史基线。B13 草案采用“先 FULL_CHECK 建基线，再 INCREMENTAL_CHECK”的课程接口方案，请确认是否可实现。
4. **MD 报告**：请提供最小报告样例，明确 finding 类型、`target`、`dependency`、Makefile 路径、完整源码 Commit SHA、构建配置及证据字段。请说明路径规范化规则，以及系统头文件和项目外依赖是否过滤。
5. **DRAFT 环境**：BuildChecker/EChecker 使用 B13 DRAFT 产物时，需要哪些镜像信息、clean-build 命令、工作目录、`project_root` 和 Linux 权限？若使用系统调用跟踪，是否需要容器 `ptrace` 或其他权限？
6. **Artifact 读取**：当前 `artifact://pair13/<producer_job_id>/<filename>` 只是逻辑 URI。请确认实际采用仓库文件、GitHub Release、共享存储还是下载端点，并与 B13 双向试读一份样例；本地绝对路径不能作为跨组方案。
7. **修复后复检**：MDFixer 输出 Patch 后，A13 如何读取 Patch、应用到指定 Commit，并重新运行 EChecker？请返回修复前后目标 MD 数量、新增 MD 数量、构建结果和复检所用的 Commit/configuration。
8. **错误与版本**：请确认“检测到 MD/RD 属于成功 finding，而构建失败、超时、权限错误属于任务 error”的区分；同时确认 Schema 版本升级和破坏性字段变更的通知方式。

B13 当前样例中的仓库 URL、40 位 SHA、镜像名和 Artifact URI 均为合成值，不代表真实服务运行或跨组访问成功。E3 Implicit 样本目前只通过 B13 人工 Oracle 和本地脚本验证，尚未获得 A13 EChecker 复检结果。

建议把双方结论写入共同可见的 GitHub Issue/PR，并记录：日期、参会人、双方样例 Commit SHA、已确认项、未决项和负责人。B13 会同步更新 `docs/E2/pair-review.md`。

## 收到 A13 回复后的登记检查

- [ ] 在 `docs/E2/pair-review.md` 记录日期、参会人和原始回复链接。
- [ ] 把 A13 样例保存到双方约定的位置，并标注来源 Commit SHA。
- [ ] 按确认结果更新 Schema、样例、ADR 和校验测试。
- [ ] 实际完成一次 Artifact 双向读取，而不只确认 URI 字符串。
- [ ] 使用 A13 EChecker 复检 E3 样本，并保存原始报告。
- [ ] 对任何仍未决定的内容建立 Issue，不把它写成已达成一致。
