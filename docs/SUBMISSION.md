# B13 E2 / E3 补交说明

## 1. 基本信息

- 小组：B13
- 小组人数：3 人
- 配对组：A13
- GitHub 仓库：<https://github.com/ma058/2026-Devops-B13>
- 提交分支：`main`
- 固定版本：[`e3-complete-2026-09-29`](https://github.com/ma058/2026-Devops-B13/tree/e3-complete-2026-09-29)
- 贡献记录：[CONTRIBUTIONS.md](../CONTRIBUTIONS.md)

## 2. E2 交付内容

E2 已形成可执行的任务与报告契约：

- 公共 Artifact、Create Job、Job 与 MD Report JSON Schema
- DRAFT、FULL_CHECK、INCREMENTAL_CHECK、REPAIR 四类 Job 样例
- MD 报告有效样例和针对性无效样例
- 标准库快速校验器、Draft 2020-12 正式校验器与单元测试
- 契约说明、设计决策、证据采集格式与 AI 使用记录

主要入口：

- [`contracts/schemas/`](../contracts/schemas/)
- [`contracts/examples/`](../contracts/examples/)
- [`docs/E2/`](E2/)
- [`scripts/validate.py`](../scripts/validate.py)
- [`scripts/check_jsonschema.py`](../scripts/check_jsonschema.py)
- [`tests/`](../tests/)

## 3. E3 交付内容

E3 已提供 DRAFT Docker 基线和 MDFixer 四种声明风格样本：

- Implicit：使用 `.d` 依赖文件修复头文件漏追踪
- Target：在目标规则中补充真实依赖
- Macro：通过宏维护依赖列表
- Hybrid：保留混合声明风格并验证 wildcard 守卫
- 每类 MDFixer 样本均包含原始缺陷、参考补丁、无效候选和恢复验证
- 固定读取 A13 `bc1ed352…` 的 FULL/INCREMENTAL Artifact，并验证图差分、路径约束和 MDFixer 输入过滤
- 运行证据包含命令、退出码、环境、检查结论和 SHA-256

主要入口：

- [`fixtures/draft/`](../fixtures/draft/)
- [`fixtures/mdfixer/`](../fixtures/mdfixer/)
- [`scripts/verify_implicit.py`](../scripts/verify_implicit.py)
- [`scripts/verify_mdfixer_explicit.py`](../scripts/verify_mdfixer_explicit.py)
- [`scripts/verify_a13_interop.py`](../scripts/verify_a13_interop.py)
- [`contracts/paired/a13/`](../contracts/paired/a13/)
- [`evidence/E3/`](../evidence/E3/)

## 4. 最终验证结果

在最终 `main` 的独立 Git 副本中完成验收：

| 验证项 | 结果 |
| --- | --- |
| `scripts/validate.py` | 15 份有效样例通过；10 份无效样例按预期拒绝 |
| `python -m unittest discover -s tests -v` | 33 / 33 通过 |
| `scripts/check_jsonschema.py` | 4 份 B13 Schema、1 份 A13 配对 Schema、全部正反样例与 Implicit 模板均符合预期 |
| `scripts/verify_a13_interop.py` | A13 跨组互读 16 / 16 通过 |
| `scripts/verify_implicit.py` | 全流程通过 |
| Target 风格 | 21 / 21 通过 |
| Macro 风格 | 21 / 21 通过 |
| Hybrid 风格 | 22 / 22 通过 |
| DRAFT 镜像复验 | 5 / 5 通过 |

三类显式样本的最终结构化证据：

- [`2026-09-27-001743-mdfixer-target-style`](../evidence/E3/2026-09-27-001743-mdfixer-target-style/)
- [`2026-09-27-001749-mdfixer-macro-style`](../evidence/E3/2026-09-27-001749-mdfixer-macro-style/)
- [`2026-09-27-001755-mdfixer-hybrid-style`](../evidence/E3/2026-09-27-001755-mdfixer-hybrid-style/)
- [`2026-09-29-a13-interop`](../evidence/E3/2026-09-29-a13-interop/)

## 5. 教师复现方式

Windows / PowerShell：

```powershell
python scripts/validate.py
python -m unittest discover -s tests -v
python scripts/verify_a13_interop.py
```

Linux / WSL Ubuntu：

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_jsonschema.py
python3 scripts/verify_implicit.py
python3 scripts/verify_mdfixer_explicit.py
```

## 6. 提交时填写的文字

```text
B13 组三人 E2/E3 实验补交。
GitHub 仓库：https://github.com/ma058/2026-Devops-B13
固定版本：e3-complete-2026-09-29
提交说明：https://github.com/ma058/2026-Devops-B13/blob/main/docs/SUBMISSION.md

仓库包含 E2 的四类任务契约、MD Report 契约、有效/无效样例、自动校验与单元测试，以及 E3 的 DRAFT Docker 基线、Implicit/Target/Macro/Hybrid 修复样本、A13 固定 Artifact 互读、端到端验证脚本和结构化运行证据。最终独立复验中，33 项单元测试全部通过，A13 互操作 16 项检查全部通过，Implicit 全流程通过，Target/Macro/Hybrid 共 64 项检查全部通过。
```

## 7. 实际提交清单

- 提交 GitHub 仓库链接
- 同时提交或粘贴本文件链接
- 若平台允许附件，可将本文件导出为 PDF；仓库仍作为代码、提交记录和证据的唯一正式来源
- 提交后检查仓库可访问，`main` 与 `e3-complete-2026-09-29` 标签均可打开
