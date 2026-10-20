# E5–E7 来源、目录与复现边界

- 日期：2026-10-20；小组 B13；仅执行 B 轨道 DRAFT。
- 起点：E4 标签 `e4-complete-2026-10-12`，提交 `7b231398e34e5e0935c77f7cea8aebefae5039d6`。
- 教学来源：用户提供的 `E5-7.zip` 中 `02_学生实验/DevOps_1020_Student_Cloud.zip`。
- 原 E5-7.zip SHA-256：`b61e99c131f5bc893ed94f2be18c964fa0a3559610a582009790fdb8a982177e`。
- `labs/B-draft/` 基于教学 B 轨道参考实现；其中核心源码、24 项测试与 DeepSeek 候选来自教学包，不计作 B13 从零编写的算法。
- `course/e5-e7/` 保存教学报告模板与 B 轨道 CI 演示素材。
- E2–E4 原有根目录入口继续保留。E5–E7 的命令均先进入 `labs/B-draft`；不得在根目录误运行旧 E4 的 `make all`。
- 教学 workflow 暂存于 `labs/B-draft/.github/workflows/`，GitHub 不会自动执行嵌套 workflow。成员3负责接入根目录 `.github/workflows/` 并设置正确工作目录、artifact 路径。
- 课程手册中的新建空仓库步骤在 B13 改为既有仓库的新分支接入，以保留 E2–E4 的 Git 历史；不得再次 `git init` 或覆盖主分支。

## 候选与论文边界

### B13 网络适配

2026-10-20 首次 E5 在 Docker Hub 拉取阶段连接拒绝，日志保留为基础设施失败。后续将镜像入口改为 E4 已使用的 DaoCloud 镜像入口，保留原 sha256 digest；Debian 软件源改为阿里云镜像，仍使用 Debian 签名校验。服务 Dockerfile 复用 E4 已验证的同摘要配置。没有更改实验程序、RUN make、CMD 或预期输出。

教学原候选的完整文本保留于 `course/e5-e7/originals/DeepSeek-E5.Dockerfile`，原哈希和适配后哈希均记录于候选 provenance.json。适配后的候选是带人工环境修改的回放，不冒充未经修改的原始模型回复。

教学 `autobuild.py` 是两轮构建与运行校验参考实现，候选来自已保存文件，命令本身不调用模型。`--replay` 使用教学包记录的 DeepSeek 回复；不得称为本组当次模型生成。

E5 必须使用本组实际失败日志生成提示，记录候选来源与选择原因。E6 必须将同一构建镜像 ID 用于实际运行。E7 的故障场景 PASS 表示符合预期失败行为。

本轮要求为 DRAFT 小样例复现、核心流程、测试和 CI，不包括 MDFixer 实验，也不要求复现论文全部项目或论文成功率。A13 可直接互查本轮结果，但 A13 的交付不阻塞 B13 的独立 DRAFT 验收。

## 记录规则

原始日志保存于实验目录 `work/` 并下载备份；GitHub 只放经过检查的证据和脱敏报告。`.env`、SSH 私钥和令牌不进入提交。教师参考运行记录不当作本组证据。每名成员只署名自己的执行、修改和 Review。
