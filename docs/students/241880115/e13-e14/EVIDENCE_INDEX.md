# 成员三 E13-E14 证据索引（于泉宇 / 241880115）

取阅位置约定：服务器 `s241880115@47.110.38.55` 家目录 `~`；仓库 `/home/s241880115/devops-students/241880115/draft` 内 `work/` 为运行原件（不入 Git）。原总归档保持不变，后续只读补导出的 C7 另包登记。两包清单均排除自身，保留合法隐藏文件。

## 总归档

- `~/member3-241880115-e13e14-evidence-20261123.tar.gz`（493382 字节）
  SHA-256 `2146709c5a86a0201fa07a378b3eb132a8b841ee42486b8282d17408d61999f8`
  内含 1106 项 manifest（`manifest-E13E14.sha256.txt`，排除自身），本轮成员一辅助审计逐项复算全部匹配。实际包含 486 个实验副本 `.git` 文件，之前“无.git”的表述不准确；12份 `.git/config` 仅含本地 `/course/data/...` origin 与常规配置，核查未见 credential/extraheader/含身份认证URL。原包不改写，外发材料另行排除 `.git`。
- C7 只读补导出：`member3-c7-supplement-20261123.tar.gz`，43,471字节，SHA-256 `365d1a4d1cff5b41bc7306d336998ca1d8151e0b298a93654f516a7578a87650`。
  `MANIFEST.json` 共93项，排除自身，包内94文件，不含`.git`。来源为上述成员三服务器的既有 `work/e13-c7-failed/` 与 `work/e13-c7-success/`；成员一仅只读下载/复算并打包，没有重新执行成员三实验。包含请求/退出码、两个完整结果目录、PROVENANCE和摘要。
  团队取阅位置：`/srv/b13-e13e14-handoff/member3-review-20261123/`；以同目录归档与`.sha256`核对。
- 前序归档（E11-E12 期，仍有效）：`member3-241880115-e13-receive-preflight-20261121.tar.gz`（2803 字节，SHA `7dae3b10…`）；其余见 E11-E12 索引。

## 分项索引

| 实验 | 关键原件（仓库 work/ 或归档内路径） | 要点 |
| --- | --- | --- |
| E11-E12 门禁复验 | 原会话登记；本次总归档不含74项测试stdout，baseline console只含实验运行 | 登记74/74 OK @6eca1beb，2026-11-23T06:27Z；不作为本包已独立复算项，需要时另补原日志 |
| C6 演练 A | `work/e13-c6/`（probe.log、before/after.sha256、hit-scan.txt、clean-scan.txt、codes.txt） | HIT=1 脱敏 `sk-d***` → CLEAN=0 |
| C6 演练 B（括号字面量不漏报） | 归档 `c6-supplement-outside-repo/` 与 `e13-c6-supplement-scan/` | 4 形态全命中（`Brac***`，exit 1）；仓库外目录避免 git 过滤 |
| C6 镜像扫描 | `work/e13-image-scan.txt`（更正版）+ `e13-image-scan-stale-checkout-8829f42.txt` + `image-scan-corrected-note.txt` | 合并后 main 工作区+镜像 888 文件 0 命中；陈旧检出 5 命中如实留档并更正 |
| C7 失败隔离 | 原包只有codes/request；两个结果目录在服务器work中，现另有上述C7补包 | FAILED/SUCCEEDED、job/trace不同；失败2项、成功85项原result引用全部hash/bytes匹配，不是本次重跑 |
| 基线回归三次尝试 | `work/e13-baseline-01/02/03/` + 三份 console.log（归档同） | 01为metadata解析i/o timeout；02/03为600s客户端超时，分别保留，不混称 |
| 教师三项目首跑 | `work/e13-H1-jsmn-01/`、`work/e13-H2-inih-01/`、`work/e13-H3-tiny-aes-01/` + console.log；请求 `data/e13-upstream-student/*/request-e12.json` | 同因 600s 超时（iter-01 MISSING_MAKE 正确复现）；复测待网络恢复 |
| 网络劣化证据 | 归档 `network-degradation-note.txt` + 各构建 stderr（基线 iter-02：deb.debian.org 9.6MB≈483s；H1：tuna 单包 8-100s）；宿主 curl code=000 只有当时说明，未附原stdout/stderr | 构建stderr可复核；宿主网络结论按当时观察登记，不冒称原始探测已交付 |
| CI four-services E2E | 归档 `ci-runner-artifacts/e13e14-evidence-45127507842-1/`（GitHub artifact 下载原件）+ `ci-record-45127507842.md` 复算记录 | job-b0bb1feb/trace-9fa18c34、162 项复算 0 损坏 |
| Review #42 侧 artifact | 归档 `ci-runner-artifacts/pr42-run45148359925-ci-e14/` | job-c65d6caa/trace-adfd0020、162 项复算 0 损坏 |
| docker.io 修复记录 | 报告第 1 节 + 服务器本地镜像 `python:3.13-slim`（digest 70729b46 经 m.daocloud 拉取+tag） | 未改冻结输入，BuildKit 本地解析实测通过 |
| E13 v2 接收预检（前序） | `~/member3-241880115-e13-receive-preflight-20261121.tar.gz` | 672 项全过、Git 恢复八项检查 |
| **本人隔离链 normal**（b13-level-v1） | 服务器 `~/e14-member3-shared-runs/receipt-normal-2WfUgr/`（RECEIPT 全套）+ 导出 `member2-e13e14-m2-e14-7d51296470f1.tar.gz`（SHA `ce0df2b3edfa23595355580b08a725fe5539316dbe5a86d17f9d46a84a07a6ea`）；成员二签收包归档 | job-5aef836c/trace-80ccfb41、DRAFT 20fc9da2、736 文件/1446 含嵌套清单验收通过 |
| **C4 受控超时** | 服务器 `receipt-C4-1qOlU5/` + 导出 `…-26fc516f7f6d.tar.gz`（SHA `df357142ad2ee5fdffee6984be5ade29524113e71c06e0423549c879599ae61c`） | EXPECTED_TIMEOUT_VERIFIED、容器按 label 清理无残留（06:23:23Z）、job-0c6d7135/trace-d8a7516f |
| **恢复 normal** | 服务器 `receipt-normal-7ewu5S/` + 导出 `…-931a57f88511.tar.gz`（SHA `e4cb57f2de61fbbc221f0d6a7b2b2c564682e0bc9c19bf50e92c218826913dca`） | 新 job-c7d64981/trace-f896b4ed、DRAFT b77c2997、MISSING=0 |
| **C5 坏补丁** | 服务器 `receipt-C5-eEaKIs/` + 导出 `…-d5941d3d6bda.tar.gz`（SHA `61fb48298ff951c13220bb6c964014a339126f43fbea3c2c299c33b764378876`） | 坏补丁拒+源/Git 不变+真实 stderr；正确补丁过；job-c01c5e6b/trace-e34f025f |
| 故障矩阵核验与签收 | 负责人核验文（02_给成员一_成员三故障矩阵核验.md）+ 签收包 `给成员一_成员三服务器故障矩阵签收_20261124.zip`（含 .sha256，三份归档与原件逐字相同） | C4/恢复/C5 三项经负责人核验通过 |
| tomlc99 全项目编排准备 | 候选包 `给成员三_tomlc99全项目候选与验收范围_20261125.zip`（候选 `60d85982…`、六产物、空 stdin 用例、Makefile-only 五条依赖约定） | 候选已经成员二独立核验；正式任务待版本化 profile 交付后执行 |

## 跨机联调最终证据（A13 客户端 241830217 × 本人服务端，2026-11-26—27）

- **服务端总包**：服务器 `~/member3-241880115-interop-final-evidence-bundle-20261127.tar.gz`（3581442 字节，SHA-256 `f9e6dedf8546ee5395d5e172944ea48cb507b11dde641c7de6a9f37432163cb0`）= 六子归档 + 总索引 `interop-final-evidence-index.json`（自 SHA `dbfe1a5462867f4974ec217c471758e5c4c248d4db76333c17939900d0bd189e`）。原件原样保留，不重新打包不覆盖；负责人已取回复核；用户机本地留档副本：本人工作区 `联调证据留档\`（复制件，SHA 同上）。交付前敏感审查 CLEAN：session.sh 仅路径/端口/镜像变量、config.json 仅 token 路径引用、无 token.secret/私钥入包，唯一模式命中=manifest 内 session.sh 合法 SHA 前缀撞形（非凭据）。
- **五轮服务端归档**（服务器 `~`，原样保留；完整 job/trace/DRAFT 镜像/manifest 见总索引与个人报告第 7 节）：
  - normal `member3-241880115-interop-normal-job-e5b6db98-20261126.tar.gz`（551514B，`9300d3ad60147654094ae056db2d13726a3b062a99f9b139ef6415cc055d0b04`，manifest 762 项）
  - C4 `member3-241880115-interop-c4-job-32fce11c-20261127.tar.gz`（76484B，`1036e65b865ea51f3c4813e84bc8ee9679a584200d12e5861fcccb47e62f1d89`，167 项，含首次 403 鉴权拒绝服务端日志原件）
  - recovery `member3-241880115-interop-recovery-job-ca339fc3-20261127.tar.gz`（391357B，`35618b6732873cdbea84d0a5818a1c79e8b82394d3cca5acb28621da5a3ce225`，761 项）
  - C5 `member3-241880115-interop-c5-job-8532b300-20261127.tar.gz`（883531B，`ac6c73cf98f7a0036cebc44d05147e6e6101e5ebb9c068a87a613084571527ac`，903 项，含 bad/repair 双链）
  - C8 `member3-241880115-interop-c8-job-eea43b0f-20261127.tar.gz`（1712237B，`3274605eda7fd9a2df3b89d7c3e24dd78ae23457e24f329b87aee302132c0fd7`，2634 项，含 409 复现响应原件+Store.submit 源码节选+API 容器日志）
  - c5-handoff-1 `c5-handoff-1-job-8532b300.tar.gz`（4934B，`f41ffa0cebfb42ed803d36a8facf0ac629a4c0c6a0e7175790ce0aace14f4370`；27 份回滚原件；双清单均保留未覆盖：初版 `0a36cc798ca4cac19b0e79b865efdccde97dabd0237431ea26d361b6d2cca8a8`、合规 `c0bdab9729035553841968f019dc17b46e76eca28cd2b0155fa84a5613171efa`）
- **A13 客户端总归档（本人已签收；供负责人复制留档与复算，不需向 A13 重索）**：用户机本地留档 `A13_最终归档留档\a13-client-final-evidence-20261127.tar.gz`（2508573B，SHA-256 `3fea847de93b5482a67cc5c170dcde89595a2b10fcd5abcd9bea42615adf7f7b`；总索引 `a13-client-archive-index.json` 自 SHA `e7335171d1eab2a5a245d296228f3e6ad1ae49539516997f8257466b8bb7c29e`；五子归档经本人独立复算一致：normal 10308B/`d334e3d5711fdfb3bb04c8342dae9da26731d2160525555c98c22f70db8748a0`、C4 5355B/`219687db0ed0386587609fc2fc457dad3ac3dab47748821b0154cb6a8baa316d`、recovery 10285B/`ee1c71646c72e0c074971ba6507fa8ea74ef09d36b29b4a1c8a705e43f405679`、C5 16154B/`67584919d080f7a3254fbb5e52ef564829a64c455f6b3a450e8af27e5ae1e3bb`、C8 2516184B/`5bb952a15bc73c5985aa88933b54072b9cb89d56e3b071d53505d9fe92204012`）。
- **双边联合验收记录（三份私聊原件，不入公开 Git；负责人经既有受限渠道复制留档，本人已签收）**：
  - A13 客户端验收总回签（2026-11-28，6754B，SHA-256 `cf691c46aa9c26d8d66574a39007871cc68d86d63bde71e7da0f09b3869a4080`）
  - B13 服务端验收总回签（2026-11-27，3598B，SHA-256 `1c9f5f21b1889f4f8f6ec3cce24ab74582c208fef0488a2c60fac0c94e1a1226`）
  - B13 最终确认 A13 总归档（2026-11-28，3929B，SHA-256 `b821ee5b8ef76088982085cc76c364071920f5f80a571d5e7a0404ffe58bbe8b`）
- **A13 侧记录**：A13 PR #29 公开确认（FINAL_REPORT/PAIR13_SIGNOFF/EVIDENCE_INDEX，对方仓库记录，非本人执行）；A13 回签所载双端审计记录 `a13-b13-bilateral-evidence-audit-20261127.json`（SHA-256 `42b32e31612ed477327b2188ebf5e2d01cf08a8a98cb622a828f80b7b080e352`，结果 PASS_ARCHIVE_AND_CROSS_END_AUDIT）按其申报登记：该记录未含于 A13 总归档，本人未单独复算其 SHA。

## Git 侧（已合并/已批准）

- PR #44：分支重建记录（8829f42 字面量污染 → 6042567 单干净提交）；合并 merge `0952fa97`；Issue #45 关闭。
- PR #42：本人正式 APPROVE（2026-11-23T10:45:16Z，六点核验正文在 PR 页面）；run 45148359925 下载复算记录在归档。
- PR #46：本人正式 APPROVE（2026-11-24T06:22:41Z，实时 head `9725bbc…` 复核依据在 PR 页面）；已由负责人正常合并（main `6244f76`）。
- PR #47（个人报告三件套）：已合并（2026-11-23T11:07:44Z，merge `60c8dcf5`）。

## 排除项

原总归档含实验副本 `.git`，保留为原件，不能称为已排除；C7补包排除 `.git`。本轮文件名和Git配置核查未发现 `.env`、私钥文件、token/env凭据或认证URL；此为核查范围声明，不扩大为所有二进制已证明不含任何敏感数据。假值仅用于隔离副本和扫描测试，红测输出保持脱敏。
