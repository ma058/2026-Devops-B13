# E3 Macro 显式声明修复样本（B13 人工 Oracle）

`main.c` 包含 `config.h`。`Makefile.before` 中 `main.o` 的声明完全通过宏 `DEPS`（声明右侧全部为宏引用，DIS>=2，Macro 风格），`DEPS = main.c` 缺少实际依赖 `config.h`，因此只改 `config.h` 后 GNU Make 不重编译 `main.o`。

`reference.patch` 为 Macro 转换参考修复：在 `DEPS` 宏中追加 `config.h`，不改动规则行，保持宏声明风格。

`invalid.patch` 为无效修复候选：把编译 recipe 替换为 `false`。它可以被 `git apply` 干净应用，但应用后构建必然失败，用于验证「无效候选被拒绝；恢复原始 `Makefile` 后完整构建与程序行为一切如初」。

验证（在仓库根目录执行）：

```bash
python3 scripts/verify_mdfixer_explicit.py --style macro-style
```

脚本使用临时目录，不改动本目录原件。证据按 B13 通用运行证据 0.1 生成到 `evidence/E3/<日期>-<时间>-mdfixer-macro-style/`（observations.md、verify.log、summary.json 与每条命令的 stdout/stderr 分流日志，字段约定见 `evidence/README.md`）。`md-report.json` 的报告 commit 为引入本 fixture 的真实提交 SHA（两段式提交）。
