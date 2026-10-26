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

注：PR #19（演示修复用例合入 main）之后，main 上的服务测试为 **25 项**（24 项基线服务测试 + 1 项演示修复用例 `test_version_returns_success_exit_code`），见 main run `40280677012`；本人服务器基线运行的 **24 项保持不变**，两者分别统计。

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

首跑 run `39387032423` 因 gate 默认 300 秒构建预算在 GitHub Runner 上不足而失败；修正提交 `248dbb7` 显式 `--build-timeout 600`（与服务器及任务书一致），此后 push run `39392487752`、PR run `39392494681` 均 success；main 合并后 run `40190185610` success（3m13s）；PR #19 合并进 main 后 run `40280677012` 亦 success（服务测试 25 项，见第 4 节注）。PR #20 报告轮经历 40 分钟墙与镜像源缓慢问题，按任务书预案恢复官方来源并成对变体修复后，最新提交 `2151766` 双绿（push run `40293323355`、PR run `40293328400`，官方源下约 7 分钟六项检查全过），完整演变与口径见 CI_RECORD 第 1.4 节。

## 8. 原始证据归档（已实际交付）

全部证据包已实际交付至共享服务器目录 **`/root/e5-e7-evidence/member3/`**（成员1 可直接取用）：

| 文件 | SHA-256 | 对应 run / 源码 SHA | 内容与关键路径 |
| --- | --- | --- | --- |
| `m3-server-raw-evidence-20261026.tar.gz` | `bd3957cc4a8adabd3dfe3f37171f79c46eb0253d091b36a0f0c09594431086fe` | 源码 SHA `2228b19`（本人服务器独立运行） | 共 187 个文件：`m3-build-01/`（构建与单元测试日志）、`m3-gate-01/`（`gate/gate-result.json`、六场景各自 `evidence/`、运行超时 `cleanup-check/stderr.log`、`verify-container-id.txt`） |
| `e7-b-evidence-39392494681-1.zip` | `2c6688d5cad553cd72a674debdbc197c072fbd1c0854833e4668193d53326f92` | PR run `39392494681`（PR #17，`248dbb7`，success） | CI artifact：`work/ci/` 下 gate 控制台日志、六场景产物、扫描结果 |
| `e7-b-evidence-40278042708-1.zip` | `88725a0b8e594aca9ebd8d49c564a417f5364e8d83080ef075eceb260290bf23` | push run `40278042708`（PR #19 失败阶段，`91e555b`，failure） | CI artifact（失败版）：含失败场景日志 |
| `e7-b-evidence-40293328400-1.zip` | `1439ba6c33588c4714ead1f4eae60203e841ab0d98f1bfc8d162f7c93a087b16` | PR run `40293328400`（PR #20，`2151766`，success） | 最新双绿 CI artifact：gate 全部产物及变体哈希 `candidate-ci.sha256`、`broken-ci.sha256` |
| `pr19-merge-blocked-screenshot-20261026.png` | `d2283f102d67f471ebdf3fc44e2b8ccfbe2ff0ddd7bffcb55420a2199db0ae2d` | PR #19 @ `91e555b` | 合并拒绝 UI 原件：All checks have failed（2 failing checks）、两个 Required 红叉、Merge 按钮灰色不可点 |
| `pr19-description-screenshot-20261026.png` | `6fb523bc8ff1156d873aa4e80451a4521b06be2d0f04256e46e4e4caa5003d90` | PR #19 | PR 页面状态原件 |

服务器原始 `work/` 目录本体保留在 `/root/241880115/e5-e7-b13/labs/B-draft/work/`（未提交 Git）；交付索引见 [CI_RECORD.md](CI_RECORD.md) 第 4 节。

## 9. 完成状态

- [x] 服务器独立运行（同基线 SHA、六项 gate 全过、运行超时清理证据）
- [x] 5 项独立判定测试（本地/服务器/main CI 三处一致）
- [x] 根级 CI workflow 接入并全绿
- [x] 主分支保护（准备、现状核验、生效确认；行为验证见 CI_RECORD.md）
- [x] 同一 PR 失败→合并被拒→修复→恢复→合并（PR #19，全程无管理员绕过）
- [x] 本报告与 CI_RECORD 提交
