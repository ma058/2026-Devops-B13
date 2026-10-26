# 成员3 E5–E7 个人实验报告

## 1. 基本信息与完成范围

- 执行人：成员3，学号 `241880115`，GitHub `yqy241880115`。
- 个人 PR：[PR #17](https://github.com/ma058/2026-Devops-B13/pull/17)（门禁判定测试与根级 CI 接入）、[PR #19](https://github.com/ma058/2026-Devops-B13/pull/19)（受保护主分支失败与恢复演示）。
- 交付分支：`member3/e7-ci-gate`、`member3/e7-gate-reject-demo`。
- 本人完成：E7 服务器独立运行（六项 gate）、5 项独立判定函数测试、教学 workflow 适配到仓库根、CI 修正与全绿、主分支保护准备与核验、同一 PR 失败→合并被拒→修复→恢复→合并闭环、[CI_RECORD.md](CI_RECORD.md)。

本人服务器运行与 GitHub Runner 运行分开记录，不互相冒充。

## 2. 服务器独立运行（E7）

- 服务器仓库：`/root/241880115/e5-e7-b13`（自 `origin` 克隆，入口 `labs/B-draft`）。
- 源码完整 SHA：`2228b193f023554d5b194dc2f400a67219d9128b`（`member1/e5-e7-bootstrap` 基线，与全组 E5–E7 公共基线一致）。
- 服务镜像：`b13-draft:241880115-e567`，完整 ID：

```text
sha256:fdc86683a77fe1a99d88558c9539ba01ed56567af7d393f2de3a0e1e84482ea8
```

## 3. 服务镜像工具链（容器内实测，2026-10-26 于本人镜像采集）

| 容器工具 | 实际版本 |
| --- | --- |
| Git | 2.47.3 |
| Docker CLI | 28.5.1，build e180ab8 |
| Python | 3.13.14 |
| pytest | 8.4.2 |
| 架构 | x86_64 |

采集方式：`docker run --rm --entrypoint <工具> b13-draft:241880115-e567 --version`（不经 shell 直跑，版本为容器内真实输出）。

## 4. 测试记录（分别统计，不相加）

| 测试入口 | 本人与 CI 实际记录 |
| --- | --- |
| 服务测试（pytest，容器内） | 24 passed，退出 0（gate unit-tests 场景） |
| 成员3 判定测试 `tests/member3/test_gate_oracle.py` | 服务器 Linux `Ran 5 tests / OK`（2026-10-26 实时复跑确认）；本地 Windows 同样 5 tests OK；main CI（run 40190185610）`Ran 5 tests / OK` |
| 根级 E2–E4 回归 | 33 项通过（本地与 CI 均确认） |

5 项判定测试内容：合法成功报告必须通过；构建/运行镜像 ID 不同拒绝；构建超时伪装运行超时拒绝；第二轮构建失败仍带 verification 拒绝；参考答案（Dockerfile.reference）泄漏拒绝。

## 5. 六项 gate（work/m3-gate-01，本人服务器）

`gate-result.json` 实测：`passed: true`，镜像 `b13-draft:241880115-e567`，`build_timeout_seconds: 600`。

| 场景 | 实际状态 | 流程退出码 | gate 判定 |
| --- | --- | --- | --- |
| unit-tests | 24 passed | 0 | PASS |
| success | SUCCEEDED | 0 | PASS |
| wrong-output | FAILED | 1 | PASS |
| invalid-candidate | 构建前拒绝 | 1 | PASS |
| build-failed | 第二轮构建失败 | 1 | PASS |
| runtime-timeout | TIMED_OUT（第二轮构建成功后运行超时） | 1 | PASS |

故障场景流程退出 1 属于预期，不等于 gate 失败；正常门禁为服务测试加五个工作流场景共六项检查。

## 6. 运行超时与容器清理证据

runtime-timeout 场景第二轮 `build_exit_code=0`，运行终态 `TIMED_OUT`（不使用构建超时替代运行超时）。运行容器 ID `6e5a1c296302de4c7909ddb181541c199b726176f7db900dfb6f06e511c86830`，`cleanup-check/stderr.log` 实测 `Error response from daemon: No such container: 6e5a1c29…`，确认运行容器已移除。证据位于 `work/m3-gate-01/gate/runtime-timeout/evidence/`（result.json、verify-container-id.txt、cleanup-check/）。

## 7. CI 修正与全绿（概要，详见 CI_RECORD.md）

首跑 run `39387032423` 因 gate 默认 300 秒构建预算在 GitHub Runner 上不足而失败；修正提交 `248dbb7` 显式 `--build-timeout 600`（与服务器及任务书一致），此后 push run `39392487752`、PR run `39392494681` 均 success；main 合并后 run `40190185610` success（3m13s）。

## 8. 原始证据归档

- 服务器原始 `work/m3-build-01`、`work/m3-gate-01` 保留在本人服务器目录，未提交 Git。
- 失败与成功两次 CI 的 artifact 已按 14 天保留要求从 GitHub 下载另存（含 PR #19 失败阶段 artifact），待最终交付时随归档一并提交索引。
- 本报告与 CI_RECORD.md 提交于 `member3/e7-reports` 分支。

## 9. 完成状态

- [x] 服务器独立运行（同基线 SHA、六项 gate 全过、运行超时清理证据）
- [x] 5 项独立判定测试（本地/服务器/main CI 三处一致）
- [x] 根级 CI workflow 接入并全绿
- [x] 主分支保护（准备、现状核验、生效确认；行为验证见 CI_RECORD.md）
- [x] 同一 PR 失败→合并被拒→修复→恢复→合并（PR #19，全程无管理员绕过）
- [x] 本报告与 CI_RECORD 提交
