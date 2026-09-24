# E3 Macro 显式声明修复样本（B13 人工 Oracle）

`main.c` 包含 `config.h`。`Makefile.before` 中 `main.o` 的声明完全通过宏 `DEPS`（声明右侧全部为宏引用，DIS>=2，Macro 风格），`DEPS = main.c` 缺少实际依赖 `config.h`，因此只改 `config.h` 后 GNU Make 不重编译 `main.o`。

`reference.patch` 为 Macro 转换参考修复：在 `DEPS` 宏中追加 `config.h`，不改动规则行，保持宏声明风格。

验证（在仓库根目录执行）：

```bash
python3 scripts/verify_mdfixer_explicit.py --style macro-style
```

脚本使用临时目录，不改动本目录原件。`md-report.json` 的报告 commit 为引入本 fixture 的真实提交 SHA（两段式提交）。
