# E3 MDFixer 显式声明修复验证记录：hybrid-style

- 运行时间（UTC）：2026-09-24T07:08:55.972659+00:00
- 执行环境：linux x86_64，GNU Make=GNU Make 4.3，CC=cc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0，Git=git version 2.34.1，Python=3.10.12
- Fixture：`fixtures/mdfixer/hybrid-style`，引入提交 `2810e238b99f3989120d58593eb5328282f38d41`
- Oracle 来源：B13_MANUAL_ORACLE（课程固定 Oracle 的程序化实现），不是 A13 检测器结果
- 证据结构：成员3草案，待成员2统一证据格式【待统一】

## 实际观察

1. 修复前：VALUE=1 完整构建输出 1；只改 config.h 为 VALUE=2 后普通 make **不重编译** main.o，程序仍输出旧值 1（复现漏重建）。修复前 Oracle：declared=['main.c']，actual=['config.h', 'main.c']，missing=['config.h']。
2. `git apply --check` 与 `git apply` 退出码均为 0；补丁改动行仅为依赖声明（patch_policy 校验通过）。
3. 修复后完整构建输出 2；再把 config.h 改为 VALUE=3 后不 clean 直接 make，main.o 被重编译，程序输出 3（增量重建恢复）。
4. 修复后 Oracle 重检：declared=['config.h', 'main.c']，missing=[]，目标 MD 数量为 0。
5. 声明风格分类：修复前 HYBRID，修复后 HYBRID，一致（期望 HYBRID）。
6. 修复前后 VALUE=1 clean build 的程序行为一致（输出 1），产物 SHA-256 相同：`c34d0d6e9e90d8226f45e9500d107f63e1e1fe06d56211b81895a89896d2adc3`。
7. Hybrid wildcard 守卫已实际检查：工作目录中 `*.h` 仅命中 config.h（唯一有效依赖），无无关文件，满足论文 wildcard 两条前置条件。

## 检查项汇总

| 检查项 | 说明 | 结果 |
|---|---|---|
| S1.build-before | 修复前完整构建退出码为 0 | PASS |
| S1.output-before | VALUE=1 完整构建后程序输出 1 | PASS |
| S3.no-rebuild-before | 修复前修改 config.h 后普通 make 不重编译 main.o（复现 MD） | PASS |
| S3.stale-output | 修复前增量构建后程序仍输出旧值 1 | PASS |
| S3.oracle-before | 课程固定 Oracle 在修复前报告 1 条 MISSING(main.o→config.h) | PASS |
| S4.apply-check | git apply --check reference.patch 通过 | PASS |
| S4.apply | git apply reference.patch 成功 | PASS |
| S4.patch-minimal | 补丁只修改必要的依赖声明 | PASS |
| S4.hybrid-guard | Hybrid wildcard 守卫：*.h 命中的 .h 全部为有效依赖且无无关文件 | PASS |
| S5.build-after | 修复后完整构建退出码为 0 | PASS |
| S5.output-after | 修复后完整构建输出当前 VALUE=2 | PASS |
| S7.incremental-rebuild | 修复后修改 config.h，普通 make 触发 main.o 重编译 | PASS |
| S8.incremental-output | 修复后增量构建输出新值 3 | PASS |
| S9.oracle-after | 修复后课程固定 Oracle 重检 MD 数量为 0 | PASS |
| S10.style-consistency | 修复前后声明风格一致（HYBRID → HYBRID，期望 HYBRID） | PASS |
| S11.behavior-equivalence | 修复后 clean build（VALUE=1）程序行为与修复前一致 | PASS |
| S11.artifact-hash | 产物哈希稳定且一致 sha256=c34d0d6e9e90d8226f45e9500d107f63e1e1fe06d56211b81895a89896d2adc3 | PASS |

## 限制

- A13 的 EChecker 修复后重检尚未执行，不能声称真实检测结果的 MD 数量为 0。
- 完整命令日志见同目录 `verify.log`，机器可读摘要见 `summary.json`。
