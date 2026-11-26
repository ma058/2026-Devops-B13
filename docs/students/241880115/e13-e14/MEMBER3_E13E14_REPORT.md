# 成员三 E13-E14 个人报告（于泉宇 / 241880115 / yqy241880115）

日期：2026-11-23。执行标注：本文所列命令与核验由成员三授权的 AI 辅助代理在其本人账号/凭据下执行，学生本人为机械操作执行者（复制、敲命令、发送）；本人另做只读抽验。服务器网络故障证据、失败任务目录均为原始保留，未删除重跑覆盖。

## 1. 个人环境（与实际运行一致）

- 服务器：s241880115@47.110.38.55，会话身份 `uid=1000(s241880115) gid=1000 groups=1000,121(docker)`（2026-11-18T07:07:23Z 登录复验记录；E13 期间沿用）。
- 仓库：`/home/s241880115/devops-students/241880115/draft`；E13-E14 执行期间源码基点：先 `6eca1beb`（原会话登记 E11-E12 测试门禁 74/74 OK，2026-11-23T06:27Z；本次总归档未包含该测试 stdout，不能据此声称下载者已独立复算该条），后更新至合并后 main `0952fa97d6ef0a31f7e55b0c8e85633850580a0f`（含 PR #44 合并）。
- 镜像：`course-e11e12:241880115`（image ID `c2e7f3a4c990`），本地构建（E11-E12 期间），无 docker.io 直连依赖。
- 本人 Compose/编排参数（PR #44 已合并，保留于 main）：端口 `E14_PORT_BUILDCHECKER/ECHECKER/DRAFT/MDFIXER`（默认 18081-18084，本人 18281-18284，仅绑定 127.0.0.1）；容器身份 `user: "${E14_UID:-0}:${E14_GID:-0}"` 与编排器属主一致（解决 git dubious ownership，CI 导出 runner uid/gid，服务器用本人 uid/gid）；DRAFT 附加 docker.sock + `E14_DOCKER_GID` 组；`HOME=/tmp`；源码树只读挂载 + 仅 `/course/work` 可写；生产 API 8081 与编排端口互不影响；compose 项目名本人独立（e14-241880115）。
- 服务器 docker.io 不可达的基础设施修复：样例候选 pin `python:3.13-slim@sha256:70729b46…` 无法解析 —— 经 m.daocloud.io 拉取同 digest 后本地 tag `python:3.13-slim`，BuildKit 本地解析实测通过；未修改任何冻结输入，digest 一致。

## 2. C6 假钥匙红绿演练（原始证据在档）

- 演练 A（运行日志扫描器 `labs/e13e14/scan_runtime_logs.py`，当次红绿原件用于证明这次扫描行为，不宣称与教学包字节完全一致或覆盖最终#44全部扫描边界）：`work/e13-c6/probe.log` 写入假 `sk-` 钥匙 → 退出码 1，输出脱敏 `sk-d***`（LLM/API Key + 密钥赋值双模式命中）；改写为干净内容后同命令复扫 → 退出码 0（hits=0）。before/after SHA 与两次扫描输出均存档。归档中的 probe.log 已是清理后内容，复算匹配 after.sha256；红测原字节未单独保存，因此 before.sha256 作为当时记录保留，不声称可从包内重算红测输入。
- 演练 B（源码扫描器 `scripts/secret_scan.py` 括号/引号/与号字面量不漏报补充，仓库外目录避免 git 跟踪过滤）：四种形态（quoted/bracketed/ampersand/bare，假值 `Brack3t[Pass]w0rd-Amp&Plus`）全部命中（4 处，脱敏 `Brac***`，退出码 1）——与 #42 引入的 AST 豁免机制对照，确认动态代码表达式豁免未误伤字面量报告。
- 扫描范围注明：工作区（888 文件含隐藏快照，合并后 main 工作区 0 命中）、运行日志（本人 work 目录与服务日志）、镜像（`--image course-e11e12:241880115` 0 命中）、历史（CI contracts 步骤 `--history` 于最终 head 通过；本地 `--all` 含本人历史本地分支的陈旧命中已如实记录）。首次镜像扫描曾误用陈旧检出 8829f42（工作区 5 命中），已更正后复扫（两份输出与更正说明均在档）。

## 3. C7 失败隔离演练（原始证据在档）

- 请求 `data/e13-c7-failed-request.json`（base 改为全零 → 期望失败）→ `work/e13-c7-failed`（exit 1）；随后正常 e11-a 请求 → `work/e13-c7-success`（exit 0）。两任务 job_id/trace_id 均不同、状态 FAILED/SUCCEEDED 不串扰；成功任务 85 项产物逐项 sha256 复核通过（`C7_ISOLATION=PASS`）。原总归档只带该请求和退出码，遗漏两个结果目录；成员一于本轮只读补取服务器已有原件，失败 2 项/成功 85 项 result 引用全部复算匹配，并形成独立补包，见证据索引。这是辅助核验/补导出，不是成员三重新运行。

## 4. E13 教学样例与教师三项目（服务器侧如实受阻，原始失败证据保留）

- 基线回归（e12.json 样例）三次尝试按原件分开登记：`e13-baseline-01` 已建立项目副本，但 iter-01 解析 docker.io 基础镜像元数据出现 i/o timeout，导致 `DRAFT_FAILED / Baseline did not reproduce missing make`；不是 data 未生成，也不是 600s 客户端超时。`e13-baseline-02/03` 则在后续候选构建返回 `Docker client command exceeded 600s`。H1-jsmn/H2-inih/H3-tiny-aes 的 `-01` 首跑同为 600s 客户端超时；H1 iter-01 的 MISSING_MAKE 缺陷复现正确（exit 1、分类 MISSING_MAKE）。这些公开上游项目是本组补充实验，不是教师未公开隐藏测试结果。
- 可直接读取的失败证据是各任务的原始 DRAFT result 与构建 stderr，支持镜像源解析失败及 apt 下载缓慢（deb.debian.org 9.6MB Packages 索引约483s、H1的tuna下载缓慢）。宿主 curl code=000、小文件3-5s和GnuTLS观察来自当时登记的网络说明；本包没有对应宿主探测原始 stdout/stderr，不能将说明文字当作已独立复算的网络探测。网络原因属于基于这些观察的诊断；未推导具体运营商根因，也未证明客户端超时后BuildKit已经停止。恢复后使用新目录复测。
- GitHub Runner 的教学 fixture 正常链有通过证据（见 CI_RECORD）；没有据此证明服务器失败的这三项公开上游项目已在Runner执行通过，或四服务故障/恢复已经验收。

## 5. 四服务与 E14 CI（Runner 侧全绿）

- PR #44：本人分支单干净提交 `6042567`（基点 6eca1beb）→ 成员一同步其实现后最终 head `77a4000` → 正常合并（merge `0952fa97`，2026-11-23T09:32:32Z；Issue #45 关闭）。参数化、身份机制、只读挂载、失败证据采集顺序修正全部保留于 main。
- four-services E2E（本人 head 的 run 45127507842，3m43s PASS）：五阶段全过（job-b0bb1feb/trace-9fa18c34）、DRAFT 双迭代（iter-01 MISSING_MAKE 失败原件保留→iter-02 成功镜像 sha256:e8e6418b…）、四角色 role/job/trace/status/elapsed_ms 日志 6 条、采集状态四项全零、扫描 151 文件 hits=0；artifact 162 项下载后逐项 sha256+bytes 复算 0 损坏。
- 本人服务器侧四服务本地编排（18281-84 端口）：2026-11-23 网络恢复后已执行，见第 5.1 节实测记录（normal、C4、恢复、C5 四项 SHARED_RUN=PASS，均经签收/核验）。

## 5.1 本人服务器隔离链实测（b13-level-v1，2026-11-23/24）

网络恢复后按成员二交付的共享链路（member2-e14-1，同步 POST /v1/run，六请求贯穿同一 job/trace）以本人账号（s241880115 uid=1000）、本人隔离端口段逐项执行；每项独立新栈、新端口、新 job/trace、新 RECEIPT（服务器 `~/e14-member3-shared-runs/receipt-*`），源码 `341d182a`，服务镜像 `sha256:cf313aa1…`：

| 运行 | 端口 | 结果 | job / trace | DRAFT 镜像 | 导出归档 SHA-256 |
|---|---|---|---|---|---|
| normal | 18281-84 | PASS，MISSING=0，仅 Makefile 变化 | job-5aef836c… / trace-80ccfb41… | sha256:20fc9da2… | ce0df2b3…（1537381B） |
| C4 受控超时 | 18285-88 | EXPECTED_TIMEOUT_VERIFIED；超时容器按 ownership label 定位 kill+rm，06:23:23Z 复核无本人容器残留，source_unchanged | job-0c6d7135… / trace-d8a7516f… | sha256:d5d14eda… | df357142…（1232165B） |
| 恢复 normal | 18289-92 | PASS，MISSING=0（新任务恢复，不与故障任务共用身份） | job-c7d64981… / trace-f896b4ed… | sha256:b77c2997… | e4cb57f2…（1537482B） |
| C5 坏补丁 | 18293-96 | PASS；坏补丁 accepted=false、完整源码与 Git 状态不变、真实 apply-check stderr 原件；随后正确补丁通过、MISSING=0 | job-c01c5e6b… / trace-e34f025f… | sha256:cbfbae84… | 61fb4829…（1570079B） |

四项五退出码全 0（CLIENT/CAPTURE/CLEANUP/VERIFICATION/DIAGNOSTIC_SCAN），运行日志扫描（711/151/711/808 文件）hits=0。normal 经成员二签收（736 文件、735 外层清单、1446 含嵌套校验全过，tar 前缀为工具名、identity 为本人已确认）；C4/恢复/C5 三项经负责人核验通过（签收包 zip 与原件逐字相同）。既有 C6/C7 演练与 normal 不重复计入故障矩阵；四容器 healthy 仅作存活观察，业务证据以六请求链原件为准。本轮成员一 CLI 的 tomlc99 消费（job-15dcdf2c）不属本人实验，不并入本表。

## 6. Review 轮转（成员二 #42 与共同 PR #46）

- 对最终 head `40281a57ed525d1655e4df71ed05239323c0d159` 完成正式 Review 并 APPROVE（2026-11-23T10:45:16Z）：六点核验（head/base/diff 与 10 项检查、真实项目非样例冒充、member2-e14-1 协议校验链与 worker 受限性、测试无放宽、secret_scan AST 豁免判定为误报修复而非门禁降低、run 45148359925 artifact 914 文件下载与 162 项清单复算 0 损坏）。Review 正文在 PR 页面。
- 对共同 PR #46 最终 head `9725bbc431eb473ae1161d41291c9dd977d262b6` 完成正式 Review 并 APPROVE（2026-11-24T06:22:41Z）：实时 head 复核（341d182→20ab492 为 14 份文档/JSON 增量、实现零变动；20ab492→9725bbc 为 main 同步合并）、11 项检查实时全绿、实现核心经本人第 5.1 节端到端实证、member2_faults 窄域门控审定。#46 已由负责人正常合并（main 推进至 6244f76）。

## 7. 边界与未竟事项

1. tomlc99 E14 全项目编排：候选（`60d85982c0d07649a5506b567680728747cd8c981829c2cfec962fc64ee36340`，六产物+空 stdin 独立运行用例）已经成员二独立核验并经本人研读，采集计划就绪；**正式新任务待 A13 版本化全项目 profile 经成员二复算后交付本人执行**——已收候选试建包不当作正式 profile，已关闭的旧 toml.o 消费不重开。
2. 正式跨机服务联调：待 A13 241830217 回复五项确认（实际连接人+本人公钥、两个候选时段、专用栈端口/镜像/SHA/profile 版本、X-E14-Token 获取方式、请求发起与故障顺序安排）；旧账号 a13-241830088 已于 11-23 到期且仅授权 127.0.0.1:8081，不作为 E14 四服务通道，不按"既有隧道可用"对外承诺开始时间。本人现有本机四角色 HTTP 证据不冒充 A13 跨机记录；"新栈恢复"不冒充同一部署的恢复；C8 异步 /v1/jobs 幂等单独登记。
3. 教师隐藏测试：任务书/PPT 无独立申请入口，材料已随结项包归档；**尚未收到结果**，不以双方互查代替。
4. 第 4 节服务器侧失败的基线与教师三项目：失败原件保留（RECEIPT 在档），如需复测按新目录另行登记，不与 5.1 节真实项目链混计。
