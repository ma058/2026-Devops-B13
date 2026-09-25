# 成员2交付审查回复

- 日期：2026-09-26
- 审查人：成员1
- 审查分支：`origin/feature/member2-draft-evidence`
- 审查提交：`fac61f9 feat(member2): add DRAFT contracts, Docker baseline and evidence collection`
- 状态：需要修改后再提交 PR

## 审查结论

成员2的 DRAFT 契约、Docker 人工基线和通用证据采集方向可以接受。DRAFT 专有约束位于 `job_type=DRAFT` 的条件分支中，没有改变其他已知 Job 类型的字段语义；证据采集器也能区分命令退出码、检查结论、未执行检查和预期失败。

当前分支尚不能直接合并。成员2需要先同步已合并的 E2 PR #6、修复无效样例、重新生成绑定干净提交的最终证据，并使用自己的 GitHub 身份创建 PR。

## 成员1实际执行的验证

### 成员2分支自身

- `python scripts/validate.py`：合法样例通过，无效样例被拒绝
- `python -m unittest discover -s tests -v`：15 项全部通过
- `python3 scripts/check_jsonschema.py`：3 份 Schema 结构合法，样例与反例符合当前脚本预期
- `git diff --check`：未发现空白符错误

### 与 E2 PR #6 的集成模拟

成员1在隔离工作树中将 `origin/feature/e2-repair-contract-m3` 合入成员2分支：

- `scripts/validate.py` 自动合并成功
- `tests/test_contracts.py` 出现一处内容冲突
- 冲突原因是双方都在同一位置追加测试
- 正确解决方式是同时保留成员2的 DRAFT 测试和成员1的 MD Report 测试

按上述方式临时解决后：

- 22 项单元测试全部通过
- 4 份 Schema 均通过 Draft 2020-12 结构检查
- DRAFT、REPAIR、MD Report、Implicit 模板和所有已有 Job 样例可同时校验

这只是成员1的隔离集成模拟，没有替成员2修改或提交其分支。

## 必须修改的问题

### 1. 修复 `failed-without-error.json`

当前文件：

```text
contracts/examples/invalid/failed-without-error.json
```

在新的 DRAFT 约束下不再是“只有缺少 error 一个错误”的反例。正式 JSON Schema 实际报告 6 个错误：

1. `error` 为 `null`
2. 缺少 `input.context_files`
3. 缺少 `input.build`
4. 缺少 `input.max_iterations`
5. 缺少 `input.configuration_id`
6. 缺少 `input.repository.url`

请以有效的 `draft.failed.json` 为基础，只把 `error` 改为 `null`，确保该反例只有一个拒绝原因。还应增加针对性测试，不能只断言“存在任意错误”，而应断言拒绝原因确实是失败状态缺少错误对象。

### 2. 同步最新 `main`

E2 PR #6 已合并到 `main`，合并提交为：

```text
efc1a204202dc644ab37959e351d11e62f9477c6
```

请在自己的分支合入最新 `main`，解决 `tests/test_contracts.py` 的冲突时保留双方测试，不要删除 MD Report 或 DRAFT 任一侧的覆盖。

### 3. 重新生成最终证据

当前已提交的成员2证据记录绑定旧 HEAD `b6f47cd`，并明确标记 `dirty=true`。这些记录可以保留为开发过程证据，但不能作为最终干净提交的唯一验收依据。

同步 #6、修复反例并提交后，请至少重新生成：

- 契约校验记录
- 单元测试记录
- 正式 JSON Schema 校验记录
- DRAFT 基线或现有镜像复验记录

最终记录应绑定新的完整 Commit SHA；若运行前仓库干净，`source.dirty` 应为 `false`。A13 EChecker 没有执行时必须继续明确写为未执行。

### 4. 使用成员2身份创建 GitHub 贡献

远端已有分支 `feature/member2-draft-evidence`，但截至审查时没有对应的开放 PR。请由成员2本人：

1. 创建或关联自己的 Issue
2. 推送修复提交
3. 创建 Draft PR
4. 在 PR 中列出实际运行环境、命令和证据目录
5. 请求成员1和成员3 Review

成员1不会代替成员2创建提交或 PR，以免贡献记录归属错误。

## PR 前检查清单

- [ ] 已同步包含 `efc1a20` 的最新 `main`
- [ ] 已保留 DRAFT 与 MD Report 双方测试
- [ ] `failed-without-error.json` 只有一个拒绝原因
- [ ] 22 项或更多集成测试全部通过
- [ ] 4 份 Schema 正式校验通过
- [ ] 最终证据绑定新的完整 Commit SHA
- [ ] 最终证据正确记录 dirty 状态
- [ ] 未执行 A13 EChecker 的事实已保留
- [ ] 已由成员2本人创建 Issue、提交和 Draft PR

## 给成员2的简短回复

你的 DRAFT、Docker 基线和证据采集总体方向通过预审，但现在还不能合并。请先同步已合并的 `main`（含 #6），在 `tests/test_contracts.py` 冲突中保留双方测试；再把 `failed-without-error.json` 改成只有 `error=null` 一个错误。目前该文件有 6 个 Schema 错误。修复并提交后重新生成绑定干净 Commit SHA 的契约、测试、Schema 和 DRAFT 证据，然后用你自己的 GitHub 身份创建 Draft PR 并请求 Review。
