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

## Git 侧（已合并/已批准）

- PR #44：分支重建记录（8829f42 字面量污染 → 6042567 单干净提交）；合并 merge `0952fa97`；Issue #45 关闭。
- PR #42：本人正式 APPROVE（2026-11-23T10:45:16Z，六点核验正文在 PR 页面）；run 45148359925 下载复算记录在归档。

## 排除项

原总归档含实验副本 `.git`，保留为原件，不能称为已排除；C7补包排除 `.git`。本轮文件名和Git配置核查未发现 `.env`、私钥文件、token/env凭据或认证URL；此为核查范围声明，不扩大为所有二进制已证明不含任何敏感数据。假值仅用于隔离副本和扫描测试，红测输出保持脱敏。
