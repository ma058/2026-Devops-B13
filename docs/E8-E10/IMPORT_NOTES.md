# 教学导入与版本说明

- 来源：`DevOps_E8_E10_20261031.zip` 中 `03_实验包`，包 SHA-256 见 TEAM_PLAN。
- 导入基线：B13 原 main `93a8d8a0883ee0b4b747270e33c552a5b36fd935`，保留已有历史和 E7 工作流。
- 公共 PR：[#21](https://github.com/ma058/2026-Devops-B13/pull/21)，公共导入提交 `5d77e6b`。
- 教学核心 `labs/e8e10/lab.py`、原 `test_profile.py` 未改；`environment` 含课程打包的 BuildChecker，只供本轮容器内真实动态重检，不宣称 A13 远程服务联调。
- 唯一环境适配：Dockerfile 将 Debian / security / pip 地址参数化；本地默认保留课程镜像源，GitHub Runner 用官方源。基础镜像 digest 和 requirements-dev.lock 哈希校验保持。
- 新 CI 从 `test_profile.py` 单文件改为发现 `test_*.py`，保证每位成员后续新增测试真实执行；A/B 教学自检均保留，B13 个人报告只记录本人实际完成的 B 轨道。
- 辅助脚本 `course/e8-e10/classroom_helpers.sh` 从课程包原样复制。本人完整手工等效驱动 `member1_run.py` 和自主测试与教学参考分别列明。

正常顺序：成员2审核 #21 → 两套 CI 通过 → 合并公共导入 → 个人 PR / 同伴 Review。成员1为尽早完成实验，先在个人分支从公共导入提交开展独立运行；个人 PR 暂以教学分支为 base，公共导入合并后改为 main，重新核对差异和 CI。不得提前合并个人 PR 或绕过保护。

本地桌面旧 `devops/B13` 当前 Git 报 `this operation must be run in a work tree`；为保护旧文件，新工作副本在 `C:\Users\ma058\Documents\Codex\B13-E8-E10\repo`。本轮未删除、重置或覆盖旧工作副本。
