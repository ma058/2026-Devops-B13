# A13 v2 原件签收与 B13 请求取阅

日期：2026-11-23。记录人：成员一马宇航 / 241880054，Codex 辅助核验。原件由 A13 提供，报告不改写，不把签收等同于新的正式联调完成。

## A13 原件签收

本次收到 `A13_给B13_E13项目与当次报告_v2_20261118.zip`（564475 字节）。外层 SHA-256 与 A13 独立交付记录一致：

`e1b08ce371f372dd330e741bce46c28414e44b748e22e2f952df7bc2cd8498b0`

- ZIP 675 个文件，路径/重复项/CRC核验通过。
- report清单672项全量大小/哈希匹配，另两个根级文件与清单内对应原件逐字节相同。
- result有665个唯一artifact引用，连同阶段/信封共672次引用全部同job且匹配原件大小/摘要。
- Git恢复包99489字节，SHA `497479ebab2fc7955ca35f1298953ac18a289d7820963aff4adabcfd968bfdd2`；fsck、C0→C1祖先链通过，保留shallow；C0的152个、C1的154个源码快照均与Git blob一致。
- A13源job `job-cc3e73345c4549e485b6cb9124e3ed76` / trace `trace-7cf5d2b94318423eaddeb328af9e4da9`；生产实现SHA `497b49f74904ac0ff9b7e28c0f5a29dcbb6d2a98`，环境为orchestrator，不能记成DRAFT成品实际执行。

| 原件 | 字节 | SHA-256 |
|---|---:|---|
| result.json | 144737 | 84b38878cf10e6f862a0eedd26d052e4b5a22009359546ccf451adf58bb2f013 |
| incremental-check.json | 4766 | 05e561fca546d09a2ffa0d08c5a565e3d7322c084964d6ec664831b80ccd32e4 |
| incremental-report.json | 3790 | 3ae064328c43a34c84eaa707c68e648be5973ee15c28f311168869073a946652 |

三层job/trace/target及信封data/payload一致，增量包含toml.o→toml.h、toml.o→toml_extra.h。完整全量发现还保留toml_json→toml.h，不过滤成全项目MD0。详细数据见receipt-audit.json。

## 旧报告与新绑定报告的区别

原v2三层均缺profile_sha256。以B13代码40281a57实际只读运行：原件历史handoff可核对独立hash/身份并派生；绑定精确tomlc99 profile后，read_fixed_report正确返回PROFILE_HASH_MISMATCH。错误目标返回STALE_REPORT；错误外部hash以及追加换行仍沿用旧hash均返回ARTIFACT_HASH_MISMATCH。670份originals文件前后哈希不变。

历史派生件SHA为 `10e7affd5e03d9d8fc0a2821af670637f521e17993a58f586007b450266c37ef`，这是B13新生成的历史格式派生件，不是A13包中既有fixed-md；未补写profile字段，未执行构建/修复/API。见v2-preflight.json。这组预检不冒称完整正式C1–C3矩阵。

A13本次回复已复算并接受scoped profile的596字节及canonical SHA `0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1`。精确toml.o范围的profile值已对齐，可以用于A13新任务生成；新报告、整项目E14范围、窗口与联合RC仍待实际交付/确认。

## B13 实际请求可直接取阅

本目录 `b13-recorded-requests/` 给出6份正常链路实际请求body、原summary、逐文件摘要/来源索引和说明。来自成员二原归档 SHA `4157bd945a4fbd5bf3e87a935d0fb38a90fac77d478f97873e6101ef3f6e4707`，运行源码99f2c7a；不是从未来任务伪造的请求。

历史job/trace、/course路径和image_id不可直接在A13新任务重放。请按本机目录/新任务和A13实际API映射，新请求另存；认证头/token/env未复制。B13项目bundle/profile/candidate仍位于 `course/e13-e14/projects/b13-level-v1/`，项目内容在#42合并时未变。

## 下一步

1. A13按已对齐scoped profile用新任务输出result、信封、payload三层相同profile绑定，并附所有被引用原件、独立摘要、源码、job/trace及真实运行环境。
2. B13保持旧v2不动，对新原件另做正式消费与回签。
3. A13 241870063与B13成员二完成B13项目的实际运行/C5，以及tomlc99整项目范围方案；服务对口确认新协议版本/部署/时窗。
4. 联合集成入口与v0.9-rc所属仓库仍待双方明确；未对缺失回复默认接受，也未发布候选。
