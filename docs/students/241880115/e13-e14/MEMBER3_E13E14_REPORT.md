# 成员三 E13-E14 个人报告（于泉宇 / 241880115 / yqy241880115）

日期：2026-11-23。执行标注：本文所列命令与核验由成员三授权的 AI 辅助代理在其本人账号/凭据下执行，学生本人为机械操作执行者（复制、敲命令、发送）；本人另做只读抽验。服务器网络故障证据、失败任务目录均为原始保留，未删除重跑覆盖。

## 1. 个人环境（与实际运行一致）

- 服务器：s241880115@47.110.38.55，会话身份 `uid=1000(s241880115) gid=1000 groups=1000,121(docker)`（2026-11-18T07:07:23Z 登录复验记录；E13 期间沿用）。
- 仓库：`/home/s241880115/devops-students/241880115/draft`；E13-E14 执行期间源码基点：先 `6eca1beb`（E11-E12 测试门禁 74/74 OK，2026-11-23T06:27Z 记录），后更新至合并后 main `0952fa97d6ef0a31f7e55b0c8e85633850580a0f`（含 PR #44 合并）。
- 镜像：`course-e11e12:241880115`（image ID `c2e7f3a4c990`），本地构建（E11-E12 期间），无 docker.io 直连依赖。
- 本人 Compose/编排参数（PR #44 已合并，保留于 main）：端口 `E14_PORT_BUILDCHECKER/ECHECKER/DRAFT/MDFIXER`（默认 18081-18084，本人 18281-18284，仅绑定 127.0.0.1）；容器身份 `user: "${E14_UID:-0}:${E14_GID:-0}"` 与编排器属主一致（解决 git dubious ownership，CI 导出 runner uid/gid，服务器用本人 uid/gid）；DRAFT 附加 docker.sock + `E14_DOCKER_GID` 组；`HOME=/tmp`；源码树只读挂载 + 仅 `/course/work` 可写；生产 API 8081 与编排端口互不影响；compose 项目名本人独立（e14-241880115）。
- 服务器 docker.io 不可达的基础设施修复：样例候选 pin `python:3.13-slim@sha256:70729b46…` 无法解析 —— 经 m.daocloud.io 拉取同 digest 后本地 tag `python:3.13-slim`，BuildKit 本地解析实测通过；未修改任何冻结输入，digest 一致。

## 2. C6 假钥匙红绿演练（原始证据在档）

- 演练 A（运行日志扫描器 `labs/e13e14/scan_runtime_logs.py`，源码来自教学包原字节导入，#44）：`work/e13-c6/probe.log` 写入假 `sk-` 钥匙 → 退出码 1，输出脱敏 `sk-d***`（LLM/API Key + 密钥赋值双模式命中）；改写为干净内容后同命令复扫 → 退出码 0（hits=0）。before/after SHA 与两次扫描输出均存档。
- 演练 B（源码扫描器 `scripts/secret_scan.py` 括号/引号/与号字面量不漏报补充，仓库外目录避免 git 跟踪过滤）：四种形态（quoted/bracketed/ampersand/bare，假值 `Brack3t[Pass]w0rd-Amp&Plus`）全部命中（4 处，脱敏 `Brac***`，退出码 1）——与 #42 引入的 AST 豁免机制对照，确认动态代码表达式豁免未误伤字面量报告。
- 扫描范围注明：工作区（888 文件含隐藏快照，合并后 main 工作区 0 命中）、运行日志（本人 work 目录与服务日志）、镜像（`--image course-e11e12:241880115` 0 命中）、历史（CI contracts 步骤 `--history` 于最终 head 通过；本地 `--all` 含本人历史本地分支的陈旧命中已如实记录）。首次镜像扫描曾误用陈旧检出 8829f42（工作区 5 命中），已更正后复扫（两份输出与更正说明均在档）。

## 3. C7 失败隔离演练（原始证据在档）

- 请求 `data/e13-c7-failed-request.json`（base 改为全零 → 期望失败）→ `work/e13-c7-failed`（exit 1）；随后正常 e11-a 请求 → `work/e13-c7-success`（exit 0）。两任务 job_id/trace_id 均不同、状态 FAILED/SUCCEEDED 不串扰；成功任务 85 项产物逐项 sha256 复核通过（`C7_ISOLATION=PASS`）。

## 4. E13 教学样例与教师三项目（服务器侧如实受阻，原始失败证据保留）

- 基线回归（e12.json 样例）三次尝试：`e13-baseline-01`（data 未生成即失败）/`02`/`03` 均终止于 DRAFT docker 构建 600s 客户端超时。H1-jsmn/H2-inih/H3-tiny-aes 首跑同因（`-01` 目录原件保留；请求文件已按 03 指南生成在档）。H1 iter-01 的 MISSING_MAKE 缺陷复现正确（exit 1、分类 MISSING_MAKE）。
- 根因证据：docker 构建内 apt 下载极端缓慢（deb.debian.org 9.6MB Packages 索引 ~483s；tuna 单包 8-100s），与当日 GitHub GnuTLS 抖动同为服务器出口网络劣化；小文件探测 3-5s 正常、中等传输失败（宿主 curl Packages.xz code=000 超时），容器与宿主同受影响。失败任务目录、构建 stderr、网络探测记录均在档。网络恢复后按手册以新目录复测。
- 相同样例在 GitHub Runner 端完整通过（见 CI_RECORD），链路正确性已有运行器侧证据。

## 5. 四服务与 E14 CI（Runner 侧全绿）

- PR #44：本人分支单干净提交 `6042567`（基点 6eca1beb）→ 成员一同步其实现后最终 head `77a4000` → 正常合并（merge `0952fa97`，2026-11-23T09:32:32Z；Issue #45 关闭）。参数化、身份机制、只读挂载、失败证据采集顺序修正全部保留于 main。
- four-services E2E（本人 head 的 run 45127507842，3m43s PASS）：五阶段全过（job-b0bb1feb/trace-9fa18c34）、DRAFT 双迭代（iter-01 MISSING_MAKE 失败原件保留→iter-02 成功镜像 sha256:e8e6418b…）、四角色 role/job/trace/status/elapsed_ms 日志 6 条、采集状态四项全零、扫描 151 文件 hits=0；artifact 162 项下载后逐项 sha256+bytes 复算 0 损坏。
- 本人服务器侧四服务本地编排（18281-84 端口）：待服务器出口网络恢复后执行（DRAFT 候选构建含 apt，同第 4 节阻塞原因）；受控故障注入与恢复复测同批执行——此项为**待执行**，不以 CI 正常路径替代，不填"通过"。

## 6. Review 轮转（成员二 #42）

- 对最终 head `40281a57ed525d1655e4df71ed05239323c0d159` 完成正式 Review 并 APPROVE（2026-11-23T10:45:16Z）：六点核验（head/base/diff 与 10 项检查、真实项目非样例冒充、member2-e14-1 协议校验链与 worker 受限性、测试无放宽、secret_scan AST 豁免判定为误报修复而非门禁降低、run 45148359925 artifact 914 文件下载与 162 项清单复算 0 损坏）。Review 正文在 PR 页面。

## 7. 边界与未竟事项

1. 服务器出口网络劣化期间，一切含 apt 下载的 docker 构建（教学样例基线、教师三项目、真实项目候选、本人本地四服务 DRAFT）受阻——失败原件保留、根因证据在档、恢复后新目录复测。
2. 真实项目（b13-level-v1/a13-tomlc99-release-1）公共编排接入与 A13 241830217 联调：按任务单推进中（另见 EVIDENCE_INDEX 与后续回执），不因 #42 批准或 #44 合并而宣称结项。
3. 教师隐藏测试若针对本轮提交，未返回结果前记"待结果"，不以自写测试代替。
