# 成员三 E13-E14 证据索引（于泉宇 / 241880115）

取阅位置约定：服务器 `s241880115@47.110.38.55` 家目录 `~`；仓库内 `work/` 为运行原件（不入 Git）。总归档为单一 tar.gz（内含逐文件 manifest，排除清单自身，含合法隐藏文件）。

## 总归档

- `~/member3-241880115-e13e14-evidence-20261123.tar.gz`（493382 字节）
  SHA-256 `2146709c5a86a0201fa07a378b3eb132a8b841ee42486b8282d17408d61999f8`
  内含 1106 项 manifest（`manifest-E13E14.sha256.txt`，排除自身）。
- 前序归档（E11-E12 期，仍有效）：`member3-241880115-e13-receive-preflight-20261121.tar.gz`（2803 字节，SHA `7dae3b10…`）；其余见 E11-E12 索引。

## 分项索引

| 实验 | 关键原件（仓库 work/ 或归档内路径） | 要点 |
| --- | --- | --- |
| E11-E12 门禁复验 | `work/`（服务器）+ 总归档 e13-baseline-*.console.log 前 `run_e11e12.py test` 输出 | 74/74 OK @6eca1beb，2026-11-23T06:27Z |
| C6 演练 A | `work/e13-c6/`（probe.log、before/after.sha256、hit-scan.txt、clean-scan.txt、codes.txt） | HIT=1 脱敏 `sk-d***` → CLEAN=0 |
| C6 演练 B（括号字面量不漏报） | 归档 `c6-supplement-outside-repo/` 与 `e13-c6-supplement-scan/` | 4 形态全命中（`Brac***`，exit 1）；仓库外目录避免 git 过滤 |
| C6 镜像扫描 | `work/e13-image-scan.txt`（更正版）+ `e13-image-scan-stale-checkout-8829f42.txt` + `image-scan-corrected-note.txt` | 合并后 main 工作区+镜像 888 文件 0 命中；陈旧检出 5 命中如实留档并更正 |
| C7 失败隔离 | `work/e13-c7-failed/`、`work/e13-c7-success/`、`work/e13-c7-codes.txt`、`data/e13-c7-failed-request.json` | FAILED/SUCCEEDED、job/trace 不同、85 产物复核 PASS |
| 基线回归三次尝试 | `work/e13-baseline-01/02/03/` + 三份 console.log（归档同） | 全部 DRAFT 600s 超时（网络劣化），原件保留待复测 |
| 教师三项目首跑 | `work/e13-H1-jsmn-01/`、`work/e13-H2-inih-01/`、`work/e13-H3-tiny-aes-01/` + console.log；请求 `data/e13-upstream-student/*/request-e12.json` | 同因 600s 超时（iter-01 MISSING_MAKE 正确复现）；复测待网络恢复 |
| 网络劣化证据 | 归档 `network-degradation-note.txt` + 各构建 stderr（基线 iter-02：deb.debian.org 9.6MB≈483s；H1：tuna 单包 8-100s）+ 宿主 curl code=000 记录 | 宿主/容器同挂；小文件正常 |
| CI four-services E2E | 归档 `ci-runner-artifacts/e13e14-evidence-45127507842-1/`（GitHub artifact 下载原件）+ `ci-record-45127507842.md` 复算记录 | job-b0bb1feb/trace-9fa18c34、162 项复算 0 损坏 |
| Review #42 侧 artifact | 归档 `ci-runner-artifacts/pr42-run45148359925-ci-e14/` | job-c65d6caa/trace-adfd0020、162 项复算 0 损坏 |
| docker.io 修复记录 | 报告第 1 节 + 服务器本地镜像 `python:3.13-slim`（digest 70729b46 经 m.daocloud 拉取+tag） | 未改冻结输入，BuildKit 本地解析实测通过 |
| E13 v2 接收预检（前序） | `~/member3-241880115-e13-receive-preflight-20261121.tar.gz` | 672 项全过、Git 恢复八项检查 |

## Git 侧（已合并/已批准）

- PR #44：分支重建记录（8829f42 字面量污染 → 6042567 单干净提交）；合并 merge `0952fa97`；Issue #45 关闭。
- PR #42：本人正式 APPROVE（2026-11-23T10:45:16Z，六点核验正文在 PR 页面）；run 45148359925 下载复算记录在归档。

## 排除项

归档不含 `.git`、`.env`、真实凭据；假值仅用于隔离副本（仓库外/运行时拼接构造，源码字面量零提交）。
