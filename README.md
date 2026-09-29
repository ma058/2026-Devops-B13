# 2026 DevOps B13 — E2 / E3 / E4

本仓库是 B13 小组（3 人）的 DevOps 实验仓库。B13 负责 DRAFT 与 MDFixer，并提供公共任务契约、REPAIR/MD 报告契约、可复现测试样本、自动校验脚本和运行证据。

提交入口见 [提交说明](docs/SUBMISSION.md)，个人 GitHub 活动见 [贡献登记表](CONTRIBUTIONS.md)。E3 跨组收尾固定版本使用 Git 标签 [`e3-complete-2026-09-29`](https://github.com/ma058/2026-Devops-B13/tree/e3-complete-2026-09-29)。

E4 从上述标签开始。B 组官方模板已经接入仓库，服务器运行证据仍须由三名成员分别生成。完整执行顺序、三人分工、服务器安全边界与验收清单见 [E4 可重复工程环境计划](docs/E4/README.md)。

## E2 交付

- `contracts/schemas/`：Artifact、Create Job、Job、MD Report 四份 JSON Schema
- `contracts/examples/`：DRAFT、FULL_CHECK、INCREMENTAL_CHECK、REPAIR 与 MD Report 的有效及无效样例
- `docs/E2/`：契约说明、设计决策与 AI 使用记录
- `scripts/validate.py`：不依赖第三方包的快速校验器
- `scripts/check_jsonschema.py`：基于 Draft 2020-12 的正式 Schema 校验
- `tests/`：契约与证据采集单元测试

## E3 交付

- `fixtures/draft/`：DRAFT Docker 人工基线
- `fixtures/mdfixer/implicit-style/`：Implicit 声明修复、参考补丁和无效补丁
- `fixtures/mdfixer/target-style/`：Target 风格声明修复样本
- `fixtures/mdfixer/macro-style/`：Macro 风格声明修复样本
- `fixtures/mdfixer/hybrid-style/`：Hybrid 风格声明修复样本
- `scripts/verify_implicit.py`：Implicit 样本端到端验证
- `scripts/verify_mdfixer_explicit.py`：Target、Macro、Hybrid 三类样本端到端验证
- `contracts/paired/a13/`：A13 固定提交的跨组 Artifact 与 Schema 快照
- `scripts/verify_a13_interop.py`：A13 图/报告互读、路径约束和 MISSING-only 消费验证
- `evidence/`：命令输出、结构化摘要、环境信息和产物哈希

## 最终验收结果

最终 `main` 独立复验结果：

- 标准库契约校验：15 份有效样例通过，10 份无效样例均按预期拒绝
- Draft 2020-12 校验：4 份 B13 Schema、1 份 A13 配对 Schema 及全部样例符合预期
- 单元测试：33 / 33 通过
- A13 跨组互操作：16 / 16 通过；固定 A13 `bc1ed352…`，验证图差分、报告读取、路径安全和 MISSING-only 过滤
- Implicit：问题复现、修复、增量重建、行为等价、无效候选拒绝与恢复全部通过
- Target：21 / 21 通过
- Macro：21 / 21 通过
- Hybrid：22 / 22 通过
- DRAFT 镜像复验：5 / 5 通过

## E4 工程骨架

- `services/draft/`：DRAFT 的 `version` 与 `smoke` 命令及 4 个单元测试
- `compose.yaml`：挂载宿主机 docker.sock，并设置 CPU、内存与进程数限制
- `Makefile`：`doctor → build → test → smoke → scan` 一键流程
- `requirements-dev.in` 与 `requirements-dev.lock`：带哈希的 Python 依赖锁
- `scripts/doctor.py`：服务器资源、Docker 工具与仓库级 Git 身份自检
- `scripts/secret_scan.py`：工作区、Git 历史与镜像密钥扫描
- `docs/E4/`：三人分工、运行记录模板、A13 互查清单与 AI 使用记录

E4 需要在分配的 Linux 服务器运行：

```sh
make doctor
make all
```

预期结果为 4 个单元测试通过，DRAFT 冒烟测试正确识别 `Dockerfile.broken` 中缺少 `make` 的预期失败，并由 `smoke.json` 记录 `passed: true`。这不表示内层 Dockerfile 构建成功。

## 复现命令

在仓库根目录执行：

```powershell
python scripts/validate.py
python -m unittest discover -s tests -v
python scripts/verify_a13_interop.py
```

在 Linux 或 WSL Ubuntu 中执行：

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_jsonschema.py
python3 scripts/verify_implicit.py
python3 scripts/verify_mdfixer_explicit.py
```

上述脚本在隔离副本或临时目录中测试修复，不会用破坏性命令覆盖真实工作区。
