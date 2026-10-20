# 发给成员三：E5–E7 工作安排

你负责 E7 故障门禁、判定函数的扩展测试、GitHub Actions 与“失败阻止合并、修复后恢复”的完整闭环。请使用自己的 GitHub 身份提交代码、报告、PR 和 Review。

## 1. 基线与工作目录

- 仓库：<https://github.com/ma058/2026-Devops-B13>
- 成员1基线：`member1/e5-e7-bootstrap`，由成员2 Review 后合入 main。
- 公共已跑通代码：`e54b1adc9fe81e6c2537beb5f480baabd2ed4b0f`。
- 你的分支：`member3/e7-ci-gate`。
- 实验目录：`labs/B-draft`。
- 个人报告：`docs/E5-E7/MEMBER3_REPORT.md`。
- CI 证据报告：`docs/E5-E7/CI_RECORD.md`。

在自己的服务器目录开始。若目录已存在，先检查，勿覆盖。基线未合入 main 时，从 origin/member1/e5-e7-bootstrap 起步，合并后更新到 main。

```bash
mkdir -p /root/241880115
cd /root/241880115
git clone https://github.com/ma058/2026-Devops-B13.git e5-e7-b13
cd e5-e7-b13
git config --local user.name 241880115
git config --local user.email '241880115@localhost'
git fetch origin
git switch -c member3/e7-ci-gate origin/main
git rev-parse HEAD
cd labs/B-draft
python3 scripts/lab_cloud.py doctor
python3 scripts/lab_cloud.py build --image b13-draft:241880115-e567 --out work/m3-build-01 --build-timeout 1200
python3 scripts/lab_cloud.py gate --image b13-draft:241880115-e567 --candidate fixtures/b13-candidates/error-driven.Dockerfile --out work/m3-gate-01 --build-timeout 600
```

与成员2约好构建时段。每次用新 --out 目录，保留失败记录。

## 2. 必须检查的六项

| 项目 | 预期 |
| --- | --- |
| 服务单元测试 | 基线 24 passed；增加服务测试后记录实际数量 |
| success | SUCCEEDED，exit 0，两轮构建，输出 hello E3 |
| wrong-output | FAILED，exit 1，output_matches=false |
| invalid-candidate | FAILED，exit 1，无构建轮次，构建前拒绝改 CMD |
| build-failed | FAILED，exit 1，第二轮构建失败，不进入运行验证 |
| runtime-timeout | 第二轮 build=0，TIMED_OUT，exit 1，运行容器已移除 |

gate 整体退出 0，gate-result.json 中六项均 passed=true。不能用构建超时替代运行超时：必须检查第二轮构建成功，以及 cleanup-check 提示容器不存在。

## 3. 自主新增测试

阅读 `scripts/run_e7_b_gate.py` 的 evaluate() 和 check_artifacts()。在 `labs/B-draft/tests/member3/` 添加独立判定函数测试，至少覆盖：

1. 正常报告中的“构建镜像 ID 与运行镜像 ID 不同”必须拒绝。
2. 将构建超时伪装成 runtime-timeout 必须拒绝。
3. 第二轮构建失败却仍出现 verification 必须拒绝。
4. 一份合法成功报告必须通过。

这些测试检查门禁本身的判断能力，不能只复制实现代码。运行 `python3 -m unittest discover -s tests/member3 -v`，将命令接入 CI。它们与服务内 24 项测试单独计数。

请同时 Review 成员2 PR，重点看缺失/额外清单项、路径安全、合法证据通过和实际 E6 记录；发现问题直接联系成员2。

## 4. 接入真正会执行的 CI

教学 workflow 位于 `labs/B-draft/.github/workflows/e7-quality-gate.yml`，嵌套目录不会被 GitHub 自动执行。将它接入仓库根目录 `.github/workflows/e7-quality-gate.yml`，做以下适配：

- job 名保持 `e7-b-quality-gate`。
- shell 步骤默认工作目录设为 `labs/B-draft`。
- upload-artifact 的 path 是仓库根相对路径，改为 `labs/B-draft/work/ci/`，不是简单沿用 work/ci。
- 候选路径使用 `fixtures/b13-candidates/error-driven.Dockerfile`，注明实际来源与人工网络适配。
- checkout 保留完整历史、persist-credentials=false；构建/执行失败也上传 artifact，保留 14 天。
- 在 gate 前运行成员1 `tests/member1`、成员2 `tests/member2`、成员3 `tests/member3` 的测试；未合入的测试目录暂不要写成已经执行。
- 额外在仓库根执行原有 `scripts/validate.py`、`python3 -m unittest discover -s tests -v` 和 `scripts/verify_a13_interop.py`，保留 E2–E4 回归。
- 核对 workflow 中 actions 标签实际可用。如果网络镜像在 GitHub Runner 不可达，保存原始失败并调整镜像来源，仍保持摘要和候选约束一致，不能删 gate 绕过失败。

先把正常 CI PR 跑绿，由成员1 Review、合并至 main。此阶段不要加入故意失败测试。

## 5. 主分支保护

正常 CI 在 main 执行成功后，读取实际 check-runs，核对名称和 GitHub Actions App ID。保护模板在 `course/e5-e7/ci/B-main-protection.json`，不得盲用模板 App ID。

必须达到：required check=e7-b-quality-gate，strict=true，enforce_admins=true，通过 PR 合并。模板 required_approvals=0 是课程门禁配置，小组仍保留非作者人工 Review 记录。

已有保护规则应先备份并保留，不要覆盖更强的已有保护。你有管理员权限则按实验手册配置；没有则把核对后的配置与 check-run 链接交成员1应用，不需要共享 Token，也不需要修改成员权限。先取得配置成功证据，再进行下一步。

## 6. 同一个 PR 的失败与恢复

在最新 main 建 `member3/e7-gate-reject-demo`。仓库根已有演示素材：

- 错误测试：`course/e5-e7/ci/rejection-demo/B/test_ci_reject_demo.py`
- 修复测试：`course/e5-e7/ci/rejection-demo/B/fixed/test_ci_reject_demo.py`
- 放置目标：`labs/B-draft/services/draft/tests/test_ci_reject_demo.py`

先提交错误测试并创建 PR：version 实际返回 0，故意断言 1。等待本 PR 最新 SHA 的 CI 真正失败，保存失败测试日志和 artifact。核实 PR 为 OPEN/BLOCKED、必需检查失败、管理员约束开启后，尝试普通合并并保存拒绝日志；不要使用 --admin 或绕过保护。

如果发现保护未生效，先修正配置，不能尝试让失败 PR 真的合入 main。记录实际拒绝，不以“预计会拒绝”替代。

随后在同一 PR 复制 fixed 测试，提交、推送。等待最新 SHA 检查通过，保存通过 artifact 和合并前状态，交成员1复核后正常合并，保存 MERGED、mergeCommit、mergedAt。

未额外增加服务测试时，教学基线 24 passed，演示失败为 1 failed/24 passed，恢复为 25 passed；你新增的独立 tests/member3 数量另列。

## 7. 交付与备份

提交自己的实现 PR、演示 PR、个人报告和 CI_RECORD.md。报告包括：

- 本人 SHA、服务镜像 ID、六项 gate 表、超时清理、扩展测试。
- 正常/失败/恢复各自 run URL、触发 SHA、下载 artifact 文件名及哈希。
- 保护配置、合并拒绝日志、修复 diff、最终合并记录。
- 明确恢复改的是故意写错的测试预期，不写成修复了 DRAFT 算法。

原始 work 和 CI artifact 在本地另存交成员1；14 天保留期内及时下载。不要把凭据或整个 .git 打包。

与成员2直接对接测试入口和互相 Review；与 A13 的 CI 排错也可自行交流。A/B 门禁检查名、测试数和程序输出不同，不需要统一。只有管理员专属配置和最终集成需要成员1处理。
