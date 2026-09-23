# 2026 DevOps B13

本仓库用于 B13 与配对组 A13 的 E2 接口契约和 E3 测试基线。B13 负责 DRAFT 与 MDFixer；A13 负责 BuildChecker 与 EChecker。

当前仓库处于**跨组契约草案阶段**：E2 中跨组字段需要 A13 确认；E3 的 Implicit 小项目已在 WSL Ubuntu 实测，但尚未使用 A13 的 EChecker 复检。示例 JSON 是合成数据，不能当作服务运行结果；参考补丁有独立的本地验证记录。

实验执行顺序、成员分工和验收条件见 [任务流程](docs/TASK_FLOW.md)。

## 当前可运行的检查

在仓库根目录执行：

```powershell
python scripts/validate.py
python -m unittest discover -s tests -v
```

校验器使用 Python 标准库，不依赖联网安装。它检查仓库中的示例是否符合本仓库的公共契约；正式与 A13 冻结前，服务专有字段仍为草案。

在 Linux/WSL Ubuntu 中还可运行：

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_jsonschema.py
python3 scripts/verify_implicit.py
```

依赖安装应在项目专用的虚拟环境或 Conda 环境中执行。`check_jsonschema.py` 使用 Python `jsonschema` 包校验 JSON Schema 文件和样例；`verify_implicit.py` 还需要 Git、GNU Make 和 GCC，并在隔离副本中复现问题、验证修复和失败恢复。已完成的运行记录见 `evidence/E2/` 与 `evidence/E3/`。

仓库成员应使用各自的 GitHub 身份、个人分支和独立提交完成负责内容，并在 [贡献登记表](CONTRIBUTIONS.md) 中补充真实的 Issue、Commit、PR、Review 和运行证据。跨组契约只有在 A13 留下可追溯的确认记录后，才能从“草案”改为“已确认”。
