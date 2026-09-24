# E2 MD 报告契约校验记录（成员3）

- 日期：2026-09-24
- 范围：`md-report.schema.json`、`md-report.json` 有效样例、2 份无效样例、`repair.request/succeeded/failed.json`、implicit 模板统一
- 分支：`feature/e2-repair-contract-m3`
- 状态：B13 本地验证；校验器 md-report 路由待成员1实现；A13 尚未确认专有字段

## 检查 1：MD Report Schema 自验（jsonschema 4.26.0，Windows Python 3.12）

结果：全部通过。

- Schema 通过 Draft 2020-12 结构检查。
- `contracts/examples/md-report.json` 通过 Schema。
- `fixtures/mdfixer/implicit-style/md-report.template.json`（统一后）通过 Schema。
- `md-report.invalid-short-sha.json` 被拒绝，唯一拒绝点 `repository.commit`：`'c65226b' does not match '^[0-9a-fA-F]{40}$'`。
- `md-report.invalid-detector.json` 被拒绝，唯一拒绝点 `detector`：`'B13_HOMEBREW_ORACLE' is not one of [...]`。

## 检查 2：标准库校验器

命令：`python scripts/validate.py`（Windows Python 3.12）

结果：退出码 1，**唯一失败项为 `md-report.json` 被按 Job 快照路由校验**（缺 `job_id` 等公共字段）——这是已知的校验器路由缺口，由成员1在本 PR 定稿后补充 md-report 路由，见 Draft PR 描述。其余全部符合预期：

- 原有 6 份 Job 样例 + 成员3重写的 `repair.request.json`、`repair.succeeded.json`、`repair.failed.json` 全部 PASS。
- 原有 3 份无效 Job 样例 + 成员3的 2 份无效 MD 报告样例均被拒绝（MD 反例当前由 create-job 兜底拒绝；路由补充后应由 MD Report Schema 按预期拒绝点拒绝）。

## 检查 3：单元测试

命令：`python -m unittest discover -s tests -v`（Windows Python 3.12）

结果：退出码 0，9 项测试全部通过，无回归。

## 检查 4：正式 JSON Schema 校验器

命令：`python scripts/check_jsonschema.py`（Windows Python 3.12，jsonschema 4.26.0）

结果：退出码 1，唯一失败项同上（`md-report.json` 路由到 job.schema.json）；4 份 Schema 均通过结构检查，含新增的 `md-report.schema.json`。

## 检查 5：Implicit 基线回归（模板统一后）

命令：`python3 scripts/verify_implicit.py`（WSL Ubuntu：GNU Make 4.3、gcc 11.4.0、Python 3.10.12、git）

结果：退出码 0，输出 `All implicit fixture checks passed. A13 EChecker recheck remains pending.` 模板字段统一未影响行为验证（该脚本不读取模板文件）。

## 限制

- E2 样例中的 URL、commit、镜像和 Artifact URI 均为合成值，不代表真实构建或跨组访问成功。
- `makefile_path` 基准目录、`INPUT_` 错误码前缀、混合报告过滤策略、修复后重检入口均为草案，待 A13 确认。
- 成员1完成校验器 md-report 路由后，检查 2/4 应全绿，本条目的将更新。
