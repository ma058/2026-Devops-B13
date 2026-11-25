# 成员三 E13-E14 CI 记录（于泉宇 / 241880115）

## 1. 源码与合并链

- 本人 PR #44：单干净提交 `6042567f308bc980c98e88b7b77c10477196a067`（基点 main `6eca1bebfa262a3153352726dded1c78570c7580`；首次提交 8829f42 因测试假密钥字面量被扫描命中，已按 #28→#29 先例重建分支移出历史）。成员一同步其实现后的最终 head `77a4000`（含扫描器字面量漏报与 CI 日志采集失败假绿修正），正式 Approve 后正常合并：merge `0952fa97d6ef0a31f7e55b0c8e85633850580a0f`（2026-11-23T09:32:32Z）；Issue #45 已关闭。参数化端口/身份机制/只读挂载/失败采集顺序全部保留于 main。
- 旧门禁回归（本人 head CI）：e11e12-integration、e8e10-quality-gate PASS（既有回归未缩减）。

## 2. 本人 head 的 four-services E2E（run 45127507842，PASS 3m43s）

- result.json：SUCCEEDED，job `job-b0bb1feb022942f49ec6e9f823e165ec` / trace `trace-9fa18c34ed9b4419bf65a3297680e119`；五阶段 draft→full-check→incremental-check→repair→recheck 全过；base `776c6e39…` / target `0be96ea8…`。
- DRAFT 双迭代：iter-01 exit=1（failure_class=MISSING_MAKE，失败原件保留）；iter-02 exit=0 → 镜像 `sha256:e8e6418b04d6b42158…`。
- 四角色日志 6 条（role/job_id/trace_id/status/elapsed_ms 字段齐全，共享同一 job）：echecker 23ms / draft 11660ms / buildchecker 179ms / mdfixer 1135ms / buildchecker 128ms / buildchecker 128ms。
- 采集状态：compose_up_exit=0 / orchestrate_exit=0 / scan_work_exit=0 / scan_logs_exit=0（失败采集结构就位，本次为正常路径）。
- artifact `e13e14-evidence-45127507842-1`（retention-days: 14）下载后逐项复算：**162 项 sha256+bytes 全对、bad=0**；扫描 151 文件 hits=0 errors=0。本地复算记录 `ci-record-45127507842.md` 已入归档。

## 3. contracts 步骤（同 head）

py_compile + test_contract（10 项）+ labs/e13e14/tests（28 项）+ compose config 全过；唯 `scripts/secret_scan.py . --history` 步骤曾失败于成员二分支历史 4 处命中（667bc445；--all 扫全部分支头——本地全分支复现定位并出具证据），成员二以 `0889bafd` 重写分支历史、成员一同步后全绿。本人内容经根扫描器 878 文件 0 命中 + 线性历史复验干净。

## 4. Review 侧 CI 复核（成员二 #42 最终 head 40281a57）

- 10 项检查（contracts/e7-b/e8e10/e11e12/four-services ×2）全部 SUCCESS 于该 head（2026-11-23T09:35-36Z）。
- PR run 45148359925 artifact 下载 914 文件；result.json SUCCEEDED（job-c65d6caa644b48de976f4179b9538c57 / trace-adfd0020225347948b46480def235a31）；**162 项产物清单逐项复算 bad=0**（与成员一独立复算一致）。

## 5. 本人服务器隔离链 CI 侧记录（b13-level-v1，2026-11-23/24）

- 共同 PR #46（四角色公共编排接入真实项目）：成员二在 Runner 19381-84 以 member2-e14-1 跑通（run 45164222990，job-99536c92/trace-3d7a843f、DRAFT c12ce1d3…、编排镜像 8bfcacb5…、735 项复算）；父提交 f52de747 五场景 CI 提供六份真实请求原件。本人对 #46 最终 head `9725bbc…` 完成实时复核后正式 APPROVE（2026-11-24T06:22:41Z），后由负责人正常合并（main `6244f76`）。
- 本人服务器四项运行（normal/C4/恢复/C5，见个人报告第 5.1 节）：为服务器侧共享链路实测（XFTP kit + `服务器独立运行.sh`），非 CI Runner 运行；每项导出归档与 .sha256 随信交成员二，RECEIPT 服务器保留。CI 侧不重复登记本人服务器运行为 Runner 记录。

## 6. 失败与恢复记录（诚实登记）

- 服务器基线 `e13-baseline-01` 是 iter-01 的 docker.io metadata i/o timeout，外层 DRAFT_FAILED 表示没有复现预期 missing-make；`02/03` 及 H1/H2/H3 的首跑才是 `Docker client command exceeded 600s`。各任务原始result与构建stderr均保留。宿主网络探测只有事后说明文字，本包未交原stdout/stderr；客户端超时不等于已证明BuildKit终止。Runner当前证据仅覆盖教学fixture正常路径，不代替这些公开上游项目或故障恢复的实跑。网络恢复后 2026-11-23 晚已由真实项目链（第 5.1 节）证实服务器构建路径恢复；基线与 H1-H3 若复测按新目录另行登记。
- 教师隐藏测试：**尚未收到结果**；已按负责人决定随结项包归档材料，不以双方互查或自写测试代替。
