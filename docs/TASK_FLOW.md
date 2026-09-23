# B13 成员1：从零开始的执行流程

本流程以 E2、E3 课件和三人分工为范围。成员1负责公共契约、校验、跨组集成、隐式规则修复样本和失败恢复；成员2负责 DRAFT 与通用运行证据；成员3负责 REPAIR 与三类显式声明修复。

## 阶段 0：仓库与身份

1. 在桌面 `devops/B13` 建立本地 Git 仓库，配置 `origin`。保留上级目录的 PPT、论文，不提交到仓库。
2. 检查 `git remote -v`、`git status`、`git config user.name` 和 `git config user.email`。每个人用自己的 GitHub 身份提交，不能代替别人制造贡献。
3. 网络可用后核对远端是否为空；若不是空仓库，先拉取并检查差异，不覆盖远端历史。
4. 在 GitHub 创建成员1的 Issue：公共契约与校验、产物与版本约定、Implicit 修复与恢复。成员2、3也分别创建自己的 Issue。

验收：仓库目录、远端地址、负责人和 Issue 可追溯。当前 `main` 已推送到 GitHub，成员1 Issue #1 已登记，E2 与 E3 已形成独立提交；成员1功能分支推送和 PR 尚待完成。

## 阶段 1：E2 公共任务模型

1. 成员1建立公共 Job Schema，定义 `schema_version`、`job_id`、`trace_id`、`job_type`、`status`、`input`、`output`、`error` 等字段。
2. 写状态与错误约定。检测出 MD/RD 是正常分析结果，写入 findings；构建失败、执行超时等写入 `error`。
3. 写四类 Job 的最小有效样例和无效样例。A13 服务专有字段只标记为草案，不冒充已协商的正式契约。
4. 编写本地校验器和自动测试：四类有效样例通过；未知 `job_type`、缺 baseline 的增量请求、错误状态缺 error 等被拒绝。

验收：`python scripts/validate.py` 与 `python -m unittest discover -s tests -v` 通过，且失败原因可定位到具体文件。

## 阶段 2：E2 产物、版本与设计记录

1. 定义 Artifact 记录：`artifact_id`、`type`、`uri`、`media_type`、`producer_job_id`，并约定完整 commit SHA、构建配置和生产任务的关联方式。
2. 草拟 `artifact://` 访问规则。若还没有共享存储，应明确这是待 A13 确认的方案，不能只留一个无法读取的 URI。
3. 维护 Backlog、ADR 和配对会议记录。`ADR-003` 单独说明课程要求“缺 baseline 的增量请求被拒绝”，而 EChecker 论文允许 clean build 建立历史基线。
4. 把 A13 的 FULL_CHECK/INCREMENTAL_CHECK 样例纳入校验，更新 Schema 与示例，并记录任何破坏性字段变更。

验收：B13 能解释 A13 的 MD 报告；A13 能解释 B13 的 DRAFT 产物，且双方能实际定位示例产物。

## 阶段 3：与 A13 对齐

需要三轮交流：

1. **字段对齐**：成员1确认公共 Job、状态、错误、版本；成员2确认 DRAFT 输出及 Linux 跟踪环境；成员3确认 MD 报告与 REPAIR 输入。
2. **样例互审**：交换有效和无效 JSON；互相说明如何读取产物、如何区分 finding 与系统失败，以及如何处理版本不匹配。
3. **契约冻结**：确定字段名、必填性、`artifact://` 解析、配置编号、Schema 版本与变更流程；未决项写入 Backlog。

成员1组织并记录会议，但各技术领域由对应成员作出说明。A13 的确认应保留在 Issue、PR Review 或双方可见的会议记录中。

## 阶段 4：E3 Implicit 测试基线

1. 准备固定的 C/Make 小项目，Makefile 使用 `%.o: %.c` 隐式规则，源码包含 `config.h`，但规则没有追踪头文件。
2. 固定源码版本、编译器、GNU Make 版本和构建配置；用人工 Oracle 标识预期 MD，不把 Oracle 当成工具检测结果。
3. 在隔离副本中验证修复前行为：完整构建后只改 `config.h`，普通 `make` 不重编译，程序仍输出旧值。
4. 应用参考 Patch，编译时使用 `-MMD -MP` 生成 `.d`，通过 `-include` 加载；再次只改头文件，普通 `make` 应重编译并输出新值。
5. 比较修复前后的 clean build 行为；有稳定二进制时比较哈希。使用 A13 的 EChecker 或课程固定 Oracle 验证目标 MD 已消除。
6. 提供故意无效的候选补丁，在隔离副本中确认构建失败、拒绝候选，并恢复到可构建版本。不得在真实工作树中用破坏性命令恢复。

验收：修复前问题能重现，修复后增量重建正确，`.d` 内容可检查，无效候选有拒绝与恢复证据。论文将 `.d` 视作隐式规则修复的一种策略，不能宣称它适用于所有项目。

## 阶段 5：个人 GitHub 贡献与提交

1. 成员1从自己的分支提交公共契约、校验器、ADR 和 Implicit 样本。每次提交说明具体修改。
2. 为每个工作包发 PR，描述 Issue、验证命令、实际日志、A13 已确认和待确认事项。
3. 成员1审查成员2的 PR；成员2审查成员3；成员3审查成员1。Review 要指出检查内容，不只写 `LGTM`。
4. 在 `CONTRIBUTIONS.md` 中链接个人 Issue、Commit、PR、Review 与运行证据。建议保留原始个人提交，不把所有工作压成一条集体提交。
5. E2 和 E3 分别完成检查表后，记录最终仓库 URL、提交 SHA、未完成项和下一步。

当前进展：成员1已使用个人 Git 身份完成仓库初始化、公共文档、E2 契约、换行规则和 E3 Implicit 基线提交；E3 提交为 `c65226b27043e0a688d1a4b41249cd7b0893f164`。功能分支推送、PR、成员 Review、A13 契约确认及 EChecker 复检尚未完成。
