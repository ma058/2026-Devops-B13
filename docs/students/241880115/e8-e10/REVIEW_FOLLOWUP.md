# 成员3 E8–E10 审核修订与证据索引

审核日期：2026-11-08。原作者：成员3 `yqy241880115`；审核、文案修订和补充复现：成员1 `ma058`，使用 Codex 辅助。本记录区分两人的实际执行，不把成员1补充产物记作成员3于11月3日保存的证据。

## 1. 源码与修订范围

- 成员3三阶段手工基线：`1ec3537e73995c4efce9d93315a7460e476631a3`，由三个 OUT 内的 `student-source-commit.txt` 确认。
- 成员3自主测试首次提交：`d001eeea1901cd3b1a3e3143acd90fdeb53eec2f`。
- 审核开始时 PR #23 head：`a3429636914e483e3c70001d6a80deca654ec595`，相对 main 新增7项测试与3份个人文档，未修改 lab.py。
- 7项新增用例分布为 E8 4项、E9 2项、E10 1项，满足每阶段新增自主测试要求。预期使用明确错误类别、固定缺失依赖和接受/拒绝条件，不复制运行结果充当预期。
- 本轮修订只更正文档和测试注释：哨兵内容不变不能证明未读取；不能宣称任意复杂Make都明确拒绝或源文件零风险；更正E8内部SHA，补齐证据来源。测试执行逻辑保持不变。

## 2. 成员3原始归档

文件名：`member3-241880115-e8e10-evidence-20261103.tar.gz`。

- 共享服务器完整路径：`/srv/b13/e8-e10-evidence/member3-241880115-e8e10-evidence-20261103.tar.gz`。
- 成员1接收副本：`C:\Users\ma058\Documents\Codex\B13-E8-E10\closeout-20261108\member3-241880115-e8e10-evidence-20261103.tar.gz`。
- SHA-256：`b0f0d2c838062ad5210b0af89b51e73ef85eaed36d4219bfc706160adec254bd`，接收后复算一致。
- 归档前缀为 `draft/work/`；共896个文件/目录条目，审核解包前检查无绝对路径、上级目录穿越或链接条目。归档只包含 work，源码和文档应结合上述Git提交及最终提交包查看。

| 内容 | 归档内路径（相对于 `draft/work/`） | 审核结果 |
| --- | --- | --- |
| E8固定报告/补丁/plan/旧报告拒绝 | `e8-B-manual.mjxNgN/` | 精确1条MD config.h、1条RD unused.h，direct补丁仅补config.h；6份Python步骤日志退出0 |
| E9三种风格输入与应用副本 | `e9-B-manual.3IoSfl/` | 三份输入报告、patch、plan齐全；macro apply-demo与预期应用结果一致；4份Python日志退出0 |
| E10三次接受/拒绝与动态重检 | `e10-B-manual.dSh1pJ/` | 三次validation、源Makefile前后副本、3行results/gate齐全；7份Python日志退出0 |
| 成员3自主测试日志 | `member3-tests-20261103-114036.log` | 14项均ok、无skip：成员3新增7项+教学7项 |
| 添加自主测试前的基线测试 | `member3-tests-20261103-114003.log` | 教学7项通过；不能当作新增测试已执行的证据 |
| 镜像构建记录 | `member3-build-20261103-113754.log` | 与各阶段environment-image-id记录一并保存 |
| CI实验产物 | `ci-e8e10/41575060702/`、`ci-e8e10/41575079843/`、`ci-e8e10/41575308347/` | 3份下载的E8–E10 artifact；原包无run.json，运行绑定由GitHub元数据另行核验 |

各阶段镜像ID均为 `sha256:e3030c3e6aac7c3231181e330b339b6afd444e0d43501fd04f7538dc015bbea4`。

样例内部SHA：E8 `1e6295c76d27627839aef25516d81aed884fab1d`；E9 direct `61e34a0db157c57f6afaef9aec29849f93c6443d`、macro `ec92840943f04ce55694ea8233f5aef0652ea7a2`、mixed `3e0fa79b1a78c613090d4754629c0b224eb882d3`；E10 `f17c473e78f2026555d0b5e9edbb8c378910c680`。这些是被测样例版本，不是外层学生源码版本。

成员1对E10原始10份 `trace/t.*` 和 `make-db.txt` 重新执行解析：findings、actual graph、declared graph、processes 均与保存JSON一致，无MISSING，仅保留 `main.o → unused.h` 的REDUNDANT；原始clean/build退出码均0。最终项目Makefile与 `source-after-accept.Makefile` 字节一致，源config.h保持VALUE=1，接受沙箱为VALUE=2。

原归档边界：14项日志未保存运行时未提交测试文件的独立快照；自主cosmetic负例运行在TemporaryDirectory中，原始validation和源前后副本随测试结束删除；原包也未保存报告提到的WSL首轮失败/恢复日志和两次shell cmp的独立输出。因此不将这些未归档内容标注为已抽验原件。

## 3. 审核开始时最新CI

以下4条均由GitHub运行元数据核验，head均为 `a3429636914e483e3c70001d6a80deca654ec595`，结论均为 `success`。

| 事件 | E8–E10 | 原E7 |
| --- | --- | --- |
| pull_request | [41575312831](https://github.com/ma058/2026-Devops-B13/actions/runs/41575312831) | [41575312757](https://github.com/ma058/2026-Devops-B13/actions/runs/41575312757) |
| push | [41575308347](https://github.com/ma058/2026-Devops-B13/actions/runs/41575308347) | [41575308337](https://github.com/ma058/2026-Devops-B13/actions/runs/41575308337) |

这些记录证明审核开始时的提交；本次文档修订形成新提交后，仍须核验新head对应检查，不能把旧run视为新提交结果。

## 4. 成员1独立审核复现

2026-11-08，成员1在独立目录 `/root/241880054/e8-e10-review-member3-20261108` 对 `a3429636914e483e3c70001d6a80deca654ec595` 运行课程镜像测试：14项全部ok、无skip；另外对只增加Makefile注释的候选保存持久证据。

- 共享归档：`/srv/b13/e8-e10-evidence/member1-review-member3-20261108.tar.gz`。
- 接收副本：`C:\Users\ma058\Documents\Codex\B13-E8-E10\closeout-20261108\evidence\member1-review-member3-20261108.tar.gz`。
- SHA-256：`fdd147a576b435ee33206080c5dc8ec9ca9805ccd49851bb0f180da1c7281250`，接收后复算一致。
- 归档前缀：`work/review-20261108/`；入口为 `source-commit.txt`、`image-id.txt`、`tests.log`、`reproduction.log`、`review_member3.py`。
- 负例证据：`cosmetic/cosmetic.patch`、`cosmetic/source-before.Makefile`、`cosmetic/source-after.Makefile`、`cosmetic/review-result.json`、`cosmetic/validation/validation.json`、构建/增量日志、重检及sandbox。

该独立复现的实际checks：patch_applies/build/test为true，header_change/no_missing为false；error=null，accepted=false、rollback=true、source_unchanged=true。此项补充可复核的技术证据，执行者和日期为成员1/11月8日，不改写成员3原始归档。

## 5. 最终登记

- 姓名、校区：于泉宇 / 南京大学苏州校区（成员3本人于 2026-11-08 补充登记）。
- 本次修订的提交、最新CI、最终Review及merge SHA：由组长在实际完成后登记；本文件不预先宣称已Approve或已合并。
