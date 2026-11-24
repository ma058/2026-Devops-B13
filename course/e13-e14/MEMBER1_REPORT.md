# 成员一 E13–E14 阶段交付

马宇航 / 241880054 / 苏州校区 / GitHub `ma058`。日期：2026-11-22。

执行说明：本次由 Codex 辅助编写与执行，以成员一授权的服务器环境运行；不写成成员一本人手工独立执行，也不代替其他成员 Review。

## 本次完成

1. 增量导入教学新增文件，保留 E8–E12 现有实现和原工作流；来源见 `MATERIALS.md`。
2. E11-B 在 snapshot/DRAFT/修复前验证固定报告，新增可选 `fixed_report_sha256`，缓存并消费同一份原字节；保持旧请求、profile 和不可变镜像执行兼容。
3. A→B handoff 复用原严格消费器，核对 result/阶段/payload/引用/hash/job/trace/profile，保留原件与派生件来源链；增加正式交付元数据参数。
4. 新增 50 项可见测试；与教学自带 3 项合计 53 项。补充真实 C1/C2/C3/C8 准备驱动，以及下载清单非空、阶段绑定和临时进程组清理检查。
5. 公共 CI 接入成员一准备驱动，失败也先采服务日志再清理，保留合法隐藏快照；未将新模板替换为最终真实项目四服务实现。
6. 旧 `member1_cases.py` 的 stale 断言加强为构建前拒绝、无 snapshot/DRAFT、源字节保持，未放宽原安全要求。

## 版本与环境

- 主干起点：`6eca1bebfa262a3153352726dded1c78570c7580`。
- 教学导入提交：`fdbd25c`；报告校验提交：`41b127d`。
- 服务器实际测试源码：`1b667ddaad2d1cd22ec640f72d2664a90e585686`。后续报告/协议文档提交不改变该实验的代码版本；最终 PR diff 与 CI 另行核验。
- 实际运行时间：2026-11-22 14:12:05–14:12:20 UTC（北京时间22:12:05–22:12:20）。
- 环境镜像：`course-e11e12:241880054`，ID `sha256:bd6407d706b8a3174a5444e1363cb0432f3e2eae70dcb0a36a7d1c1e0cb5afad`。
- gcc 14.2.0 / make 4.4.1 / git 2.47.3 / strace 6.13 / Python 3.13.14 / amd64；包版本原件为 `toolchain.lock`。
- 容器 UID/GID=10001；源码 `/course` 只读，data/work可写，SYS_PTRACE与已有Docker socket组权限。Docker能力仍具有宿主权限影响，不因非root称为完全隔离。
- 服务器新个人目录 `/root/b13-e13e14-member1-20261122/`；未更改已有8081/8083服务、账号或SSH配置。运行后生产health仍为ok，临时API与测试容器已退出。
- 本轮生成样例 C0：`06bfe7598677d3ce1558807dbff0a8a622e147aa`；C1：`8da6d6f13f20a32e288d921983312ca61aed882f`。使用国内源变体，同时改 baseline/candidate 的镜像来源前缀、保持候选digest；来源明确为课程生成样例，不当作本组正式维护项目。

## 实测结果

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 修改前 E11–E12 回归 | 74/74 OK | 服务器既有个人镜像 |
| 修改后 E11–E12 回归 | 74/74 OK | 包含旧成员各自测试 |
| 新 E13–E14 套件 | 53/53 OK，无跳过 | Linux补跑Windows无法执行的真实symlink用例；部分单元成功路由显式stub Docker，不算真实构建 |
| C1 本地A→B | SUCCEEDED | 真实检测、DRAFT构建、成品镜像内validate/full；A85、B227份产物校验 |
| C2 错目标 | STALE_REPORT | stages=[]，无snapshot/DRAFT/patch，原项目保持 |
| C3 篡改字节+旧hash | ARTIFACT_HASH_MISMATCH | stages=[]，原件/原项目保持 |
| C8 旧异步API | 同key同job、不同输入409 | 真实HTTP、完成的E11-A任务、85份下载及manifest/响应头/字节三方hash匹配 |
| 源码/历史/环境镜像扫描 | exit0 | 883个受跟踪文件；镜像扫描范围为既有扫描器的history/env，不宣称完整镜像层无秘密 |
| 本轮运行日志扫描 | exit0 | text_files=710，hits=0，errors=0 |

真实 C1 的 B job 为 `job-2285fc804b5d4f929b9d9298fc0f19b9`，trace为 `trace-73577d5ce6ba473b8b8ec5c4557a7c7d`。DRAFT 成品 ID 为 `sha256:fbaf21b913d819acfc68d2b9045e6af8a6204c8c5d44242b9998eb7e4c79f0d4`，实际操作为 validate/full，五项validation为true。

C8 job为 `job-1152f9791c1742b2a9ca889e0b423a30`，trace为 `trace-86f77047381a49d4818b79014cda92c6`。进程组清理记录分别证明父进程停止和观察时原独立进程组消失，不宣称证明了已逃逸进程组的后代。

完整标识与摘要见 `member1-evidence-summary.json`；原始请求、日志、stage、下载结果、源码快照与bundle均在下列归档。

## 证据取阅与复算

- 归档：`member1-e13-preparation-1b667dd.tar.gz`，1,270,728字节。
- SHA-256：`0366ea798ee1cb513cf92d7c1d6bc50edbc112cc1d383db535dfc952a02e340a`。
- 团队服务器可读位置：`/srv/b13-e13e14-handoff/member1-20261122/`，含归档和 `archive-verification.json`；已验证成员三账号可读。亦随本次桌面交付包提供，不要求分享root凭据。
- 驱动证据清单746项、外层归档清单789项已逐项复算；清单排除自身，合法 `.gitignore` 快照保留，`.git` 不入原始证据归档。
- 关键路径：`repo/work/member1-e13-1b667dd.../summary.json`、`C1-local-A/`、`C1-B-consumption/validation/validation.json`、`C2-rejection/result.json`、`C3-rejection/result.json`、`C8-http/download-checks.json`、`C8-http/server-cleanup.json`。目录中的 `1b667dd...` 应替换为上文完整源码SHA。
- 复现命令和正式交付参数见 `labs/e13e14/README.md` 与 `HANDOFF_CONTRACT.md`。CI是另一个执行环境，最终run/head/artifact索引登记在本分支PR描述和阶段交付包中，不把服务器日志写成CI日志。

## CI 首跑缺陷与修复

`b89ec19` 的新工作流首跑（push `45031889227`、PR `45031943346`）中，契约及成员一C1/C2/C3/C8已通过；四服务教学彩排在EChecker被Git拒绝：宿主创建的副本属于Runner UID，模板容器使用root，出现 `detected dubious ownership`。同head的原E7/E8–E10/E11–E12六次运行成功。

修复通过 `E14_UID/E14_GID` 让四角色与编排器使用相同身份；仅DRAFT额外加入实际Docker socket组。保留Git所有权检查，不设置 `safe.directory=*`。参数未提供时保留模板默认root行为，实际环境必须如实记录。后续CI必须在修复后head重跑，不能把首跑失败写成网络偶发。首跑日志及artifact另存，详见最终交付CI索引。

第一轮修复 `bc8bd52` 进一步暴露无passwd条目的Runner UID缺少可写HOME：PR run `45032279265` 的DRAFT原始stderr为 `ERROR: mkdir /.docker: permission denied`。再次补齐四角色 `HOME=/tmp`，保持相同UID/Socket组，不放宽DRAFT缺失make的判定。两轮失败日志和artifact均保留；通过后的最终head/run在PR描述与交付包登记。

推送第二轮修复前，已在服务器独立Compose项目 `b13-e14-m1-check` 验证相同配置：UID/GID10001、HOME=/tmp、仅DRAFT增加Socket组，完整五阶段SUCCEEDED，job `job-aab901e2087448e09c9674fea1e0dee9` / trace `trace-f94a01fd77914889943aaa5137b0c9fd`，四角色日志均对应此任务。运行使用既有测试源码1b667dd加归档中的新版Compose文件；清理只移除此项目，生产health仍ok。这是课程生成样例四服务彩排，不是实际项目/profile成品执行贯通或正式E14验收。此修复链对应Issue #41，随PR #40正常评审合并。

## 当前边界与后续

上述 A 端来源全部为 `LOCAL_SIMULATED_A`，是成员一准备链路；尚不是A13本人客户端、本轮双向实际项目矩阵、教师隐藏测试或正式E14验收。新四服务同步接口未宣称具有旧异步接口幂等功能。

成员二负责本组实际维护项目、服务/profile/成品执行衔接及C4/C5，并Review本PR；成员三负责隔离编排、扫描/CI扩展与C6/C7，之后由成员一Review。A13需提供本轮项目和当次报告的独立交付信息；教师隐藏测试与正式RC条件另列。具体交接见 `NEXT_STEPS.md`。

## 2026-11-23 收件与集成补录

成员一按正常流程合并#40、修正并审查#44；成员三正式批准#42最终head40281a57后，已正常合并#42（merge 1f8d9c7b2644a6063115d86df250aed9226d21f1）。未绕过保护。此前最终head的Linux旧74/新104/scanner6均通过，CI八次全绿、914文件下载复算通过；成员二原归档2387项清单已核验。执行者为成员一授权下的Codex辅助审查/复验，不代签成员二个人实验。

本次补收A13 v2原件，完成完整归档/产物引用/Git源码核验及历史报告只读预检。670份originals哈希前后不变，未运行A项目脚本或Docker。已把B13正常任务的6份请求body及原件索引提供于exchange目录，供A13字段对照。详细摘要与拒绝测试见 `exchange/20261123-v2-receipt/README.md`。

A13 scoped profile精确值已回签；新绑定报告、真实项目公共编排及跨组矩阵尚待对应交付，不把旧v2历史handoff成功等同于正式C1，也不把拒绝预检等同于完整E13门禁。#46共享协议和#47成员三证据另行按最终head审查；最终结项/RC继续由实际证据决定。
