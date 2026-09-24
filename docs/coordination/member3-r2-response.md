# 成员3协调指令 R2 回复

- 日期：2026-09-24
- 回复人：成员1
- 对应材料：成员3协调指令 R2
- 状态：A/B/C 三项已拍板；等待成员3创建 Draft PR

## 总体结论

成员3提出的 A/B/C 三点理解基本正确，按本文约定执行。成员3先提交包含 Schema、样例和说明的 Draft PR；成员1在看到最终 Schema 后负责校验器路由与单元测试。Draft PR 在四项验证通过并完成非作者 Review 前不得合并。

## 问题A：Implicit 模板的 detector 值

接受成员3提出的来源区分方案。

### detector 枚举

```text
BUILDCHECKER
ECHECKER
INSTRUCTOR_ORACLE
B13_MANUAL_ORACLE
```

### 使用规则

1. B13 自建的 Implicit Fixture 报告使用 `B13_MANUAL_ORACLE`。
2. 成员3自建的三个显式 Fixture 报告使用 `B13_MANUAL_ORACLE`。
3. 逐字段复刻课程 E3 手册人工答案的 E2 契约样例可以使用 `INSTRUCTOR_ORACLE`，但必须在 `provenance` 和样例说明中标明课程手册出处。
4. `BUILDCHECKER` 和 `ECHECKER` 只用于对应工具的真实输出，不得用于人工构造报告。

`detector` 表示报告生成者或判断来源；`provenance` 用于补充具体来源、版本和证据。两者不是同义字段，成员3应在字段表中分别解释。

### producer_job_id

`producer_job_id` 采用条件必填：

- `BUILDCHECKER`、`ECHECKER`：必须提供真实 `producer_job_id`
- `INSTRUCTOR_ORACLE`、`B13_MANUAL_ORACLE`：允许省略或为 `null`

人工报告不得为了通过 Schema 编造 Job ID。

## 问题B：无效样例的位置与路由

成员3可以通过自己的 Draft PR 在 `contracts/examples/invalid/` 中增加 MD Report 无效样例，由成员1 Review。

校验路由必须同时覆盖：

- `contracts/examples/`：有效 MD Report 必须通过 `md-report.schema.json`
- `contracts/examples/invalid/`：无效 MD Report 必须被同一 Schema 拒绝

### 无效样例拆分

不把短 SHA 和未知 detector 放在同一个反例中，以免一个错误遮蔽另一个错误。至少拆成：

```text
contracts/examples/invalid/md-report.invalid-short-sha.json
contracts/examples/invalid/md-report.invalid-detector.json
```

两个文件均以 `md-report` 开头，由两个校验器路由到 MD Report 校验。每个样例需要记录其唯一的预期拒绝原因。

## 问题C：E2 合成 SHA 与 E3 真实 SHA

成员3的理解正确，需要区分契约样例和实验运行证据。

### E2 契约样例

`contracts/examples/` 中可以使用符合格式的 40 位合成 SHA，前提是：

- `contracts/examples/README.md` 继续明确说明其为合成数据
- 不把该 SHA 写入 E3 运行证据
- 不声称该 SHA 对应真实 Fixture 或真实工具执行

### E3 Fixture 报告

`fixtures/mdfixer/*/` 下的正式报告必须引用真实 Git Commit。成员3提出的两段式提交方案接受：

1. 第一个 Commit 提交 Fixture、源码、Makefile、Patch 和 expected 文件。
2. 第二个 Commit 把第一个 Commit 的真实 40 位 SHA 写入 MD Report。

当前 Implicit Fixture 可以引用：

```text
c65226b27043e0a688d1a4b41249cd7b0893f164
```

该 SHA 仅在报告分析的源码与 Makefile 和此提交中的内容一致时有效。如果后续改变被分析的 Fixture 内容，必须引用新的真实 Fixture Commit。

## Draft Schema 的补充约束

### makefile_path

每条 finding 的 `makefile_path` 必填。为避免顶层和 finding 内字段不一致，正式 Schema 暂不重复定义顶层 `makefile_path`。

路径相对于仓库根目录还是项目根目录仍标记为草案，由成员3直接向 A13 确认。收到 A13 回复后再冻结其语义。

### location

`location` 暂定为可选字段。如果保留，应定义为结构化对象，不使用语义不明确的自由字符串。其字段和行号规则在 Draft PR Review 中确认。

### provenance

`provenance` 应能够说明人工答案的出处或工具报告的版本来源。课程样例应写明课程手册位置；B13 人工样例应写明对应 Fixture、Commit 和人工判断依据。

## Draft PR 必须包含

1. `contracts/schemas/md-report.schema.json`
2. `contracts/examples/md-report.json`
3. `contracts/examples/invalid/md-report.invalid-short-sha.json`
4. `contracts/examples/invalid/md-report.invalid-detector.json`
5. `docs/E2/repair-contract.md` 的字段表和版本政策
6. 更新后的 Implicit MD Report 模板
7. 三个显式 Fixture 及其报告、Patch 和验证证据
8. 已知未决项，特别是 A13 尚未确认的路径语义和复检字段

## 分工与集成顺序

### 成员3

1. 创建 Draft PR。
2. 提供最终 Schema、有效样例、两个独立无效样例和字段说明。
3. 允许成员1向协作分支增加独立 Commit，或提供可供成员1建立依赖分支的分支名。
4. 保持成员3自己的提交作者信息。

### 成员1

在 Draft PR 可审查后实现：

- `scripts/validate.py` 的 MD Report 最小检查与路由
- `scripts/check_jsonschema.py` 的 Schema 路由
- `tests/test_contracts.py` 中的有效和无效 MD Report 测试
- 原有 Job、Artifact 和请求校验的回归测试

成员1使用自己的 Git 身份创建独立 Commit，不替代成员3的贡献。

## 验证与合并条件

合并前必须实际运行：

```powershell
python scripts/validate.py
python -m unittest discover -s tests -v
```

```bash
python3 scripts/check_jsonschema.py
python3 scripts/verify_implicit.py
```

并满足：

- [ ] Schema 自身合法
- [ ] 有效 MD Report 通过
- [ ] 短 SHA 样例因 SHA 原因被拒绝
- [ ] 未知 detector 样例因枚举原因被拒绝
- [ ] 原有 8 份有效 Job 样例继续通过
- [ ] 原有无效 Job 样例继续按预期拒绝
- [ ] Implicit Fixture 验证继续通过
- [ ] E2 合成数据与 E3 真实证据明确区分
- [ ] A13 未确认字段继续标记为草案
- [ ] 至少一位非 PR 作者完成有效 Review

## 当前等待事项

在成员3发来 Draft PR 链接和分支名之前，成员1不提前编写依赖未知 Schema 的校验逻辑。收到链接后进入 Schema Review 和校验器集成阶段。
