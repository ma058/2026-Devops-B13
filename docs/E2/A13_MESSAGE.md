# 发给 A13 的接口对齐消息草稿

> 尚未发送。发送前请补上 B13 仓库链接、联系人和拟议交流时间。

A13 同学好，我们是 B13，负责 DRAFT 和 MDFixer。E2 公共 Job/Artifact Schema 与 B13 样例已在仓库中形成草案，希望和你们对齐以下事项：

1. 请提供 FULL_CHECK、INCREMENTAL_CHECK 的最小有效请求/结果 JSON，以及一个无效输入样例。我们会用同一套校验器验证，并把 A13 专有字段替换为你们确认的格式。
2. BuildChecker/EChecker 使用 DRAFT 环境时，需要哪些镜像、clean build 命令、工作目录、`project_root`、`configuration_id` 字段？Linux 系统调用跟踪是否需要容器 `ptrace` 或其他权限？
3. 请提供一份最小 MD 报告，明确 `target`、`dependency`、完整 commit SHA、构建配置、Makefile 位置和证据的字段名称。系统头文件、项目外依赖是否已过滤？
4. MDFixer 修复后，A13 如何读取 Patch 并执行 EChecker 重检？是否能返回修复前后的目标 MD 数量？
5. 大文件的 `artifact://` URI 最终映射到仓库文件、共享存储还是下载端点？请双方实际试读一份样例。
6. E2 课件要求缺 baseline 的增量请求被拒绝；论文允许先 clean build 建基线。我们拟采用“先 FULL_CHECK 建基线，再 INCREMENTAL_CHECK”的课程接口方案，请确认。

建议双方把结论写进共同可见的 Issue/PR 或 `docs/E2/pair-review.md`，并标出仍未决定的字段。B13 的当前示例 URL、SHA、镜像名均为合成值，不是实际实验结果。
