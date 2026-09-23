# E3 Implicit 声明测试样本（B13 人工 Oracle）

`main.c` 包含 `config.h`。原始 Makefile 的 `%.o: %.c` 规则没有跟踪头文件，因此只改 `config.h` 后，GNU Make 可能不重编译 `main.o`。该问题需要按固定构建配置验证，不应仅凭 `make` 首次成功就认为没有 MD。

`reference.patch` 是课程样例的 `.d` 修复，使用 `-MMD -MP` 生成依赖文件，并用 `-include` 加载。MDFixer 论文对隐式声明允许项目特定的其他策略，不能把此 Patch 当作通用算法。

`invalid.patch` 故意破坏构建，用来验证“拒绝候选并恢复”流程。两个 Patch 都只能在隔离副本中应用，不要直接修改本目录的 `Makefile`。

运行：

```bash
python3 scripts/verify_implicit.py
```

请从仓库根目录执行。脚本使用临时目录，不改动样本原件。正式记录需补充完整 Git commit SHA、GNU Make/GCC 版本、命令输出和退出码。`md-report.template.json` 中的占位符必须在样本提交后替换为真实 SHA；当前不能把它当作正式 MD 报告。
