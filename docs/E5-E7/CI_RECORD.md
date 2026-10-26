# 成员3 E7 CI 与主分支保护记录

## 1. 正常 CI

### 1.1 PR #17（成员3 分支 member3/e7-ci-gate）

| Run | 事件 | SHA | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| [39387032423](https://github.com/ma058/2026-Devops-B13/actions/runs/39387032423) | push | 6409edb | failure | 首跑失败：gate 命令未显式传构建预算，脚本默认 300 秒在 GitHub Runner 上不足（候选首次从零缓存安装 build-essential），success/wrong-output/build-failed/runtime-timeout 四个场景构建超时；失败证据随该 run artifact 归档 |
| [39387600346](https://github.com/ma058/2026-Devops-B13/actions/runs/39387600346) | pull_request | 6409edb | failure（41s） | 环境偶发：daocloud 镜像源对 docker:cli digest 的 metadata 解析间歇故障；如实记录为环境故障，不充当测试失败证据 |
| [39392487752](https://github.com/ma058/2026-Devops-B13/actions/runs/39392487752) | push | 248dbb7 | success | 修正提交 `248dbb7` 显式 `--build-timeout 600`，约 12 分钟全绿 |
| [39392494681](https://github.com/ma058/2026-Devops-B13/actions/runs/39392494681) | pull_request | 248dbb7 | success | 同上 |

### 1.2 main 正常 CI（#16/#17/#18 合并后）

- Run [40190185610](https://github.com/ma058/2026-Devops-B13/actions/runs/40190185610)，merge SHA `68fd630`，push 事件，**success**，3m13s。
- CI 日志核对（任务书要求，实测日志行）：
  - 根级 E2–E4 回归：`Ran 33 tests / OK`
  - tests/member1：4 项通过
  - tests/member2：**`Ran 19 tests in 0.039s / OK`——真实执行，不再 skipped**（含符号链接用例 `test_symlink_inside_project_is_rejected ... ok`）
  - tests/member3：`Ran 5 tests / OK`
  - 服务测试（gate unit-tests 场景）：24 passed
  - 三名成员的独立测试及根回归、服务测试分别列出数量，未合并计数。

## 2. 主分支保护

### 2.1 应用前现状核验（2026-10-24 实测）

- 传统 branch protection：`GET /repos/ma058/2026-Devops-B13/branches/main/protection` → 404
- Rulesets：`GET /repos/ma058/2026-Devops-B13/rulesets` → `[]`（空数组）
- 结论：两种保护机制此前均不存在（404 之外另行核验 rulesets，不以单一路径推断）；应用配置不会覆盖任何既有保护。

### 2.2 必需检查实测确认

- `GET /commits/248dbb7…/check-runs`：检查名（context）**`e7-b-quality-gate`**，App **ID 15368**（slug `github-actions`），与课程模板 `course/e5-e7/ci/B-main-protection.json` 逐字吻合。

### 2.3 生效确认（2026-10-26 实测）

- `GET /repos/ma058/2026-Devops-B13/branches/main` → **`"protected": true`**。
- 完整配置由成员1（仓库 admin）经 API 确认并与课程模板一致：必需检查 `e7-b-quality-gate`（App ID 15368）、`strict=true`（分支须最新）、`enforce_admins=true`（管理员同样受约束）、`required_conversation_resolution=true`、禁止强推/删除。
- 说明：成员3 为 collaborator（非 admin），读取 protection 详情 API 返回 404 属权限限制，不代表保护缺失；保护的实际效果由下文 PR #19 的合并阻止演示行为验证。
- 课程模板审批数 0 不等于取消人工 Review：#17 保留成员1 正式 Approve、#18 保留成员3 正式 Approve 的非作者审查记录。

## 3. 同一 PR 的失败与恢复演示（PR #19）

### 3.1 失败

- 分支 `member3/e7-gate-reject-demo`，故意错误提交 `91e555b`：将 `rejection-demo/B` 测试的 version 成功退出码预期写为 1（实际返回 0），实现未动。
- push run [40278042708](https://github.com/ma058/2026-Devops-B13/actions/runs/40278042708)：**failure**（3m6s），失败步骤实测为 "Run the real component and fault gate"（六场景 gate 的服务测试），为确定性的测试失败。
- PR run [40278273969](https://github.com/ma058/2026-Devops-B13/actions/runs/40278273969)：failure（26s），失败步骤 "Build the service image"——daocloud 偶发 metadata 故障，如实记录为环境故障，不充当测试失败证据。

### 3.2 合并被拒绝（保护行为验证）

- PR #19 页面实测：红色横幅 **"All checks have failed — 2 failing checks"**；两个 **Required** 检查（e7-b-quality-gate pull_request / push）红叉；**Merge 按钮灰色不可点击**（截图已存档）。
- 未使用管理员绕过（亦无管理员权限可用）。

### 3.3 修复（同一 PR）

- 提交 `7a50561`：采用 `course/e5-e7/ci/rejection-demo/B/fixed/test_ci_reject_demo.py`，预期恢复为正确退出码 0；**实现不变，仅恢复写错的测试预期，不写成修复 DRAFT 算法**。
- diff：`91e555b` → `7a50561`（1 个文件，替换测试函数与断言）。

### 3.4 恢复成功

- push run [40279319531](https://github.com/ma058/2026-Devops-B13/actions/runs/40279319531)：**success**
- PR run [40279327418](https://github.com/ma058/2026-Devops-B13/actions/runs/40279327418)：**success**

### 3.5 最终合并记录

- 状态：**MERGED**（成员1 复核后正常合并，非管理员绕过）
- Merge commit：`d1e76045d64830f7264ac03505a332af57067f3a`
- 合并时间：2026-10-26 14:35:01 (+0800)

## 4. 证据索引

| 证据 | 位置 |
| --- | --- |
| PR #17 四次 run 与链接 | 第 1 节表 |
| main 正常 CI 及测试日志核对 | Run 40190185610 |
| 保护前现状、check-runs、生效信号 | 第 2 节（API 实测输出） |
| 合并拒绝 UI（红叉×2、Merge 灰色） | PR #19 页面截图（本地另存） |
| 失败/恢复 run 与 SHA | 第 3 节表 |
| 失败与成功 CI artifact | 已按 14 天要求下载另存（本地），与 [MEMBER3_REPORT.md](MEMBER3_REPORT.md) 第 8 节归档说明对应 |
| 服务器原始运行证据 | 本人服务器 `/root/241880115/e5-e7-b13/labs/B-draft/work/m3-build-01`、`m3-gate-01`（未提交 Git） |

## 5. E7 完成标准对照

- [x] 正常 CI 有真实成功证据（PR #17 双绿 + main run 40190185610）
- [x] 主分支保护实际生效（protected:true + 合并被阻止行为验证）
- [x] 失败确实阻止合并（Required 检查红、Merge 按钮不可点）
- [x] 同一 PR 修复后恢复（7a50561 双绿）
- [x] 正常合并有真实记录（MERGED，merge commit d1e7604，2026-10-26 14:35:01）
- [x] 本记录与个人报告已提交
