# E3 MDFixer 显式声明修复验证记录：macro-style

- run_id：`2026-09-27-001749-mdfixer-macro-style`
- 开始/结束（UTC）：2026-09-26T16:17:47.981511+00:00 → 2026-09-26T16:17:53.847990+00:00
- 执行环境：linux x86_64（6.6.87.2-microsoft-standard-WSL2），GNU Make=GNU Make 4.3，CC=cc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0，Git=git version 2.34.1，Python=3.10.12
- 源码：`https://yqy241880115@github.com/ma058/2026-Devops-B13.git`，HEAD `fbb794b6075b3a9f69e21b390ddcc1fef68db54a`，dirty=False
- Fixture：`fixtures/mdfixer/macro-style`，引入提交 `5f599d2592fbf4a678950b7f7b2886b6844ad9e4`
- Oracle 来源：B13_MANUAL_ORACLE（课程固定 Oracle 的程序化实现），不是 A13 检测器结果；A13 EChecker 修复后重检尚未执行
- 证据格式：B13 通用运行证据 0.1（B13_DRAFT），与 evidence/README.md 一致

## 实际观察

1. 修复前：VALUE=1 完整构建输出 1；只改 config.h 为 VALUE=2 后普通 make **不重编译** main.o，程序仍输出旧值 1（复现漏重建）。修复前 Oracle：declared=['main.c']，actual=['config.h', 'main.c']，missing=['config.h']。
2. `git apply --check` 与 `git apply` 退出码均为 0；补丁改动行仅为依赖声明（patch_policy 校验通过）。
3. 修复后完整构建输出 2；再把 config.h 改为 VALUE=3 后不 clean 直接 make，main.o 被重编译，程序输出 3（增量重建恢复）。
4. 修复后 Oracle 重检：declared=['config.h', 'main.c']，missing=[]，目标 MD 数量为 0。
5. 声明风格分类：修复前 MACRO，修复后 MACRO，一致（期望 MACRO）。
6. 修复前后 VALUE=1 clean build 的程序行为一致（输出 1），产物 SHA-256 相同：`c34d0d6e9e90d8226f45e9500d107f63e1e1fe06d56211b81895a89896d2adc3`。
8. 无效候选拒绝与恢复：`invalid.patch`（编译 recipe 替换为 `false`）可干净应用，应用后构建失败（退出码非 0，候选被拒绝）；恢复原始 Makefile 后完整构建成功，程序输出 1，一切如初。

## 检查项汇总

| 检查项 | 期望 | 状态 |
|---|---|---|
| S0.report-commit | md-report.json 引用的 fixture 提交与 git 历史一致（真实提交） | PASS |
| S1.build-before | 修复前完整构建退出码为 0 | PASS |
| S1.output-before | VALUE=1 完整构建后程序输出 1 且正常退出 | PASS |
| S3.no-rebuild-before | 修复前只改 config.h 后普通 make 成功且不重编译 main.o（复现漏重建） | PASS |
| S3.stale-output | 修复前增量构建后程序仍输出旧值 1 且正常退出 | PASS |
| S3.oracle-before | 课程固定 Oracle 在修复前报告 1 条 MISSING(main.o→config.h) | PASS |
| S4.apply-check | git apply --check reference.patch 通过 | PASS |
| S4.apply | git apply reference.patch 成功 | PASS |
| S4.patch-minimal | 补丁只修改指定 Makefile 的必要依赖声明（文件范围+行内容+应用后实际变更） | PASS |
| S5.build-after | 修复后完整构建退出码为 0 | PASS |
| S5.output-after | 修复后完整构建输出当前 VALUE=2 且正常退出 | PASS |
| S7.incremental-rebuild | 修复后修改 config.h，普通 make 成功且触发 main.o 重编译 | PASS |
| S8.incremental-output | 修复后增量构建输出新值 3 且正常退出 | PASS |
| S9.oracle-after | 修复后课程固定 Oracle 重检 MD 数量为 0 | PASS |
| S10.style-consistency | 修复前后声明风格一致（期望 MACRO） | PASS |
| S11.behavior-equivalence | 修复后 clean build（VALUE=1）构建成功且程序行为与修复前一致 | PASS |
| S11.artifact-hash | 补充检查：修复前后 VALUE=1 产物 SHA-256 一致 | PASS |
| S12.invalid-apply-check | git apply --check invalid.patch 通过（补丁格式合法、可干净应用） | PASS |
| S12.invalid-apply | git apply invalid.patch 成功 | PASS |
| S12.invalid-rejected | 应用无效候选后构建失败（退出码非 0），候选被拒绝 | PASS |
| S12.recovery | 恢复原始 Makefile 后完整构建成功且程序输出 1 并正常退出 | PASS |

总体结果：**PASS**

## 限制

- A13 的 EChecker 修复后重检尚未执行，不能声称真实检测结果的 MD 数量为 0。
- 每条命令的原始 stdout/stderr 见同目录 `NNN.stdout.log`/`NNN.stderr.log`（分流保存，不保留跨流交错顺序）；机跑完整日志见 `verify.log`；机器可读摘要见 `summary.json`。
