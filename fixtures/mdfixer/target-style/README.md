# E3 Target 显式声明修复样本（B13 人工 Oracle）

`main.c` 包含 `config.h`。`Makefile.before` 中 `main.o: main.c` 直接列举依赖（声明右侧全部为普通文件，DIS=1，Target 风格），但未声明头文件 `config.h`，因此只改 `config.h` 后 GNU Make 不重编译 `main.o`，程序仍输出旧值。

`reference.patch` 为 Target 转换参考修复：直接向 `main.o` 的依赖列表追加 `config.h`，不改变原有声明风格。

验证（在仓库根目录执行）：

```bash
python3 scripts/verify_mdfixer_explicit.py --style target-style
```

脚本使用临时目录，不改动本目录原件。`md-report.json` 的报告 commit 为引入本 fixture 的真实提交 SHA（两段式提交：先提交本目录内容，再提交写入真实 SHA 的报告）。
