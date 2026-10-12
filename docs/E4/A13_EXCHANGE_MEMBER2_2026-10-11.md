# B13 成员2与 A13 的 E4 README 互查记录

## 信息与证据来源

记录人：B13成员2，Lacrym1ra；日期：2026-10-11。

| 项目 | B13 | A13 |
| --- | --- | --- |
| 仓库 | [ma058/2026-Devops-B13](https://github.com/ma058/2026-Devops-B13) | [Dufunare/2026-Devops-A13](https://github.com/Dufunare/2026-Devops-A13) |
| 实际运行 SHA | `519ca0fce2a5417e3f855a101bc5c938252a03d5` | `b755aff8df18cd363a2e556b201a7b3a240e1a44` |
| 服务 | DRAFT | BuildChecker |
| 入口 | 根 README E4 段、docs/E4/README.md | 根 README E4 段、docs/E4/README.md |
| 标准命令 | make doctor、make all | make doctor、make all |
| 成功证据目录 | work/20261011-150116/（成员2） | work/20260930-154610/（A13公开摘要） |

A13公开文档读取快照为 `be3bae491dae139e7b592f9e6b7f4b8a95b16792`；回复中记载的历史 main 是9bafaf8…，二者均不是此次 A13 独立运行 SHA。

来源：

- [A13公开互查回复](https://github.com/Dufunare/2026-Devops-A13/blob/be3bae491dae139e7b592f9e6b7f4b8a95b16792/docs/E4/B13_EXCHANGE_RESPONSE_2026-10-10.md)。
- [A13独立运行摘要](https://github.com/Dufunare/2026-Devops-A13/blob/be3bae491dae139e7b592f9e6b7f4b8a95b16792/docs/E4/RUN_241870063.md)。
- [A13实际运行基线 README](https://github.com/Dufunare/2026-Devops-A13/blob/b755aff8df18cd363a2e556b201a7b3a240e1a44/docs/E4/README.md)、[Compose](https://github.com/Dufunare/2026-Devops-A13/blob/b755aff8df18cd363a2e556b201a7b3a240e1a44/compose.yaml)、[Dockerfile](https://github.com/Dufunare/2026-Devops-A13/blob/b755aff8df18cd363a2e556b201a7b3a240e1a44/services/buildchecker/Dockerfile)。
- [B13成员2直接回复](https://github.com/Dufunare/2026-Devops-A13/issues/4#issuecomment-6106805327)，作者为Lacrym1ra。

## A13 对 B13 的公开回复

| 项目 | A13 判定摘要 | B13处理 |
| --- | --- | --- |
| 环境 | 独立克隆、Git身份与doctor流程接受 | 本人已按流程执行 |
| 构建 | 固定镜像digest、依赖锁和工具记录接受 | 本人构建成功并核对 |
| 测试 | 成员1的4 passed记录接受 | 本人补充独立4 passed |
| 冒烟 | 接受内层make缺失失败、外层passed=true的含义 | 本人结果符合该语义 |
| 密钥扫描 | 密钥管理与负例流程接受 | 本人补充扫描及假Key负例、复检 |
| docker.sock提醒 | 接受并提醒高权限风险需保留 | 保留风险边界，不声称已实现论文原环境 |
| B13完成状态 | 由B13完成报告、PR和标签收口 | 仍待合并与main回归 |

这些接受结论来自A13已发布的公开回复，不冒充2026-10-11新收到的私人聊天消息，也不扩展为对本报告PR的Review。

## B13 对 A13 的五项检查

| 项目 | B13判定 | 静态检查与运行来源 |
| --- | --- | --- |
| 环境 | 接受并建议README补充说明 | README有独立目录、仓库级Git身份和doctor入口；SYS_PTRACE、network_mode:none在Compose中明确，但README未直接解释这些约束与Linux/Docker/Compose等前提。建议补充，已在Issue发送。 |
| 构建 | 接受 | README有make all/build入口，Dockerfile固定digest，依赖锁流程明确。运行成功来自A13作者公开摘要。 |
| 测试 | 接受 | README说明测试应全部通过；A13公开摘要声明测试阶段成功，没有提供精确测试数量，不补造数量。 |
| 冒烟 | 接受 | README预期config.h可观察、app_output为1、passed=true。公开摘要声明完整流水线通过；B13未读取原始smoke.json。 |
| 密钥扫描 | 接受 | README说明.env权限、忽略及扫描流程，A13公开摘要声明扫描通过。 |

A13的正常构建冒烟与B13的预期失败冒烟不同；不要求两组测试数量、输出或镜像ID相同。README建议属于可操作的改进意见，目前没有据此宣称A13流水线失败。

## 直接交流与后续

已在现有Pair13 Issue #4发布成员2直接回复，引用实际SHA、五项结论和B13本人结果，避免重复新建交流Issue。请A13在该Issue更正任何不准确的运行信息，并反馈README建议的处理情况。

双方公开回复和本次直接回帖足以形成当前README互查记录；本次建议的进一步回执尚未取得，不写成已采纳。若对方更正实际运行SHA，应同步更新本记录并重新核对。

边界：B13未代替A13服务器重跑，未取得其原始work/字节；A13实际运行结论依赖公开作者摘要。本记录只交换脱敏信息，没有包含服务器连接信息、凭据、私人聊天截图或原始环境日志。
