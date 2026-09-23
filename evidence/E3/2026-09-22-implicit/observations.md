# E3 Implicit 人工样本运行记录

- 运行日期：2026-09-22（Asia/Shanghai）
- 执行环境：WSL2 Ubuntu，Linux 6.6.87.2-microsoft-standard-WSL2 x86_64
- GNU Make：4.3
- GCC：13.3.0
- Python：3.12.3
- Git：2.43.0
- 命令：在仓库根目录执行 `python3 scripts/verify_implicit.py`
- 脚本退出码：0
- Oracle 来源：`B13_MANUAL_ORACLE`，不是 A13 检测器结果
- 仓库 commit SHA：尚无本地提交，待成员1使用自己的 Git 身份完成首个提交后补充

## 实际观察

1. 原始 Makefile：首次 `make` 编译并运行输出 `1`；只把 `config.h` 改为 `VALUE=2` 后，`make` 报告 `Nothing to be done for 'all'`，程序仍输出旧值 `1`。
2. 参考补丁：`git apply --check` 和 `git apply` 退出码均为 0；编译命令包含 `-MMD -MP`；生成的 `main.d` 包含 `main.o` 与 `config.h`；再把头文件改为 `VALUE=3` 后，普通 `make` 重新编译，程序输出 `3`。
3. 修复前后在 `VALUE=1` 的 clean build 生成的 `app` SHA-256 相同：两侧均为 `29eda946d1c03145a17716400ca297bc9b66a6fba5827363682d0facfd63ab05`。
4. 无效补丁：`git apply --check` 和应用均成功，但 `make` 执行 `false` 后退出码为 2；脚本拒绝该候选，恢复原 Makefile 后 `make` 退出码为 0，程序输出 `1`。
5. A13 的 EChecker 修复后重检尚未执行，不能声称真实检测结果的 MD 数量已为 0。

第一次测试暴露 `reference.patch` 的 hunk 行数错误，`git apply --check` 报 `corrupt patch at line 15`；已将 hunk 从 `-7,9 +7,11` 修正为 `-7,7 +7,9`，重跑以上全部测试通过。

## 2026-09-23 复验

在同一 WSL Ubuntu 环境重新执行 `python3 scripts/verify_implicit.py`，退出码为 0。修复前陈旧输出、修复后头文件依赖重建、clean-build SHA-256 一致性以及无效候选拒绝与恢复均再次通过。A13 EChecker 仍未运行，Oracle 仍标记为 `B13_MANUAL_ORACLE`。
