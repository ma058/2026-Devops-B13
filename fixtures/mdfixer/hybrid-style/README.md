# E3 Hybrid 显式声明修复样本（B13 人工 Oracle）

`main.c` 包含 `config.h`。`Makefile.before` 中 `main.o: main.c $(HEADERS)` 混用普通文件与宏（DIS 同时含 1 与 >=2，Hybrid 风格），`HEADERS` 为空宏，缺少实际依赖 `config.h`。

`reference.patch` 为 Hybrid 转换参考修复：保留直接项 `main.c`，把头文件宏更新为 `HEADERS = $(wildcard *.h)`。

wildcard 守卫（MDFixer 论文 III-D 前置条件）：本 fixture 目录中 `*.h` 仅命中 `config.h`，而 `config.h` 正是 `main.c` 实际包含的头文件（唯一有效依赖），不存在无关 `.h` 文件。若守卫条件不成立，必须回退为显式列举 `HEADERS = config.h`。守卫由验证脚本在步骤 S4 实际检查。

`invalid.patch` 为无效修复候选：把编译 recipe 替换为 `false`。它可以被 `git apply` 干净应用，但应用后构建必然失败，用于验证「无效候选被拒绝；恢复原始 `Makefile` 后完整构建与程序行为一切如初」。

验证（在仓库根目录执行）：

```bash
python3 scripts/verify_mdfixer_explicit.py --style hybrid-style
```

脚本使用临时目录，不改动本目录原件。证据按 B13 通用运行证据 0.1 生成到 `evidence/E3/<日期>-<时间>-mdfixer-hybrid-style/`（observations.md、verify.log、summary.json 与每条命令的 stdout/stderr 分流日志，字段约定见 `evidence/README.md`）。`md-report.json` 的报告 commit 为引入本 fixture 的真实提交 SHA（两段式提交）。
