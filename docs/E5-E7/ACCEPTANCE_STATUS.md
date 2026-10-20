# E5–E7 验收状态

更新日期：2026-10-20。本表将公共基线验证与组员最终交付分开记录。

| 要求 | 当前状态 | 证据或负责人 |
| --- | --- | --- |
| E5 初始 make-not-found 日志 | PASS | evidence/E5-E7/member1/member1-e5-mirror-20261020 |
| 两类提示、回复、候选来源与选择 | PASS，助手辅助回放/整理，非独立模型实验 | docs/E5-E7/model-responses、候选 provenance |
| E5 修复构建及同镜像 ID 运行 | PASS | member1-e5-manual-20261020，hello E3 |
| E6 两轮构建、哈希、报告与运行 | 公共基线 PASS；成员2独立扩展 PENDING | 成员2 |
| 服务 24 项测试 | 公共基线 PASS | member1-build-20261020 |
| E7 五类故障场景 | 公共基线 PASS；成员3独立核验 PENDING | member1-e7-baseline-20261020 |
| 自主新增测试 | 成员1四项 PASS；成员2/3待实现 | tests/member1；两份任务书 |
| 正常 CI 和 artifact | PENDING | 成员3 |
| main 保护配置 | PENDING，正常 CI 后配置 | 成员3准备，成员1按权限协助 |
| 故意失败 PR 与实际拒绝合并 | PENDING | 成员3 |
| 同一 PR 修复恢复与最终合并 | PENDING | 成员3 |
| 成员1基线 PR | OPEN，待成员2 Review | PR #16 |
| 三人报告与最终备份 | 成员1完成；其余 PENDING | 各成员 |
| 最终标签与课程提交 ZIP | PENDING | 所有必做项通过后由成员1完成 |

## 成员一接下来怎么做

1. 将 MEMBER2_TASKS.md 和 MEMBER3_TASKS.md 分别发送给对应成员。
2. 成员2 Approve PR #16 后，核对最新提交和意见，再合并基线。
3. 等成员3提供正常 CI 和核对后的保护配置时，如需管理员权限，负责应用并保存实际返回结果。
4. Review 成员3 PR；成员3 Review 成员2 PR。各自按意见修正，依次合并。
5. 收齐两人的原始证据和 CI artifact，复核全部 PASS 后再生成最终提交包。

本轮不需要等 A13 提供数据才能推进。所有跨成员/跨组协调均可由负责人直接联系。
