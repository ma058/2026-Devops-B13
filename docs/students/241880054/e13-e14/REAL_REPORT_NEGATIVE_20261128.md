# 成员一：真实 A13 报告 C2/C3 构建前拒绝补验

执行人记为马宇航（241880054）授权的 Codex 辅助执行；实际环境为 Windows 10、Python 3.11.8，UTC 2026-11-28 12:54:32–12:54:48。结果：两个预期拒绝均通过，未进入快照、DRAFT、Docker、编译、修复或复检。本次不是新的 A13 客户端执行，也不是 Linux/Docker 成功链路的再次运行。

## 固定输入与实现

- B13 实现：`fb4be620da9587ea3dc35581eeb2599ffe98fae7`。从已核验的当前 main 工作树逐文件与 `git show` 比较后，复制 8 个实际导入文件至 `run01/implementation/`；未修改实现源码。摘要见 `implementation-source.json`。
- 实现来源源码 ZIP：`nov28-final/github/B13-source-fb4be620.zip`，SHA-256 `8e5aed518902eb42fca3f88d7fc2cd640e60033943acb0e98f3ec8a871abf330`。该完整 ZIP 位于负责人工作区及结项源码材料，本小包仅保存实际导入的 8 个文件。
- A13 原 Job：`job-fd1b21e39d41474699e43815b402804e`；Trace：`trace-ad14eb26d03f4129a38ab57ad626c72a`。原 `result.json` SHA-256 为 `60b3b84db2319d0eb11e59a3bea5ebbaebe701a29918f8dfc846d895a8e13656`。
- tomlc99 C0：`592fc6f3d2463a58fe7f60b8d255ed242740bec0`；C1：`b2dda5513fe4a7d250493528800fe425cae459a5`。在隔离克隆中核实 C0 是 C1 祖先；C1 的 154 个受跟踪文件与 Git blob 逐字一致。
- 使用既有正式旧范围 `a13-tomlc99-release-1`，修复目标只有 `toml.o`，canonical profile SHA-256 为 `0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1`。未改成六产物 full profile。
- 使用当前实现重新读取完整 A 原件并派生 fixed-md；得到与 11 月 24 日已验收派生件相同的 5,095 字节及 SHA-256 `328ec838926af9eee76781563de20ccd4404ff4b77e7086318db66005ac6f9ef`。匹配 C1 的 `read_fixed_report` 正向读取通过；不重复成功构建。

## 实际结果

| 场景 | 唯一变更 | 新 B Job / Trace | 真实结果 |
| --- | --- | --- | --- |
| C2 | 请求 target 从 C1 改为实际存在的完整 C0 SHA；报告不变 | `job-bd1836d888784262ad7d473dffbb6f81` / `trace-fde82b4cdd754f3e8345f12dcbfa33c7` | `STALE_REPORT`，退出码 1，`stages=[]` |
| C3 | 请求指向另存的报告副本；副本末尾增加一个 LF，仍传原 hash | `job-d0c4378e83ff4343b371ce05c0995b57` / `trace-3541fd92a1bf440c84690907ad9daff1` | `ARTIFACT_HASH_MISMATCH`，退出码 1，`stages=[]` |

C3 副本为 5,096 字节，SHA-256 `273ac400a2eb1994f95a012369b05b11137b6ede6d518d51feaa4c457e5c4c65`；仍是可解析 JSON，拒绝原因来自字节 hash。A 原件及正式派生件均未修改。

两次运行实际调用当前 `pipeline.main()`，未替换 `read_fixed_report` 的判断。驱动只允许实际 Git 目标解析；快照、DRAFT、镜像运行、扫描、修复、验证入口一旦被调用，会抛出不被 pipeline 转为预期拒绝的 `RuntimeError`，使驱动失败。日志中 forbidden calls 为空。此设计验证“进入副作用前拒绝”，不声称验证后续 Docker 执行，也不把 mock 的返回值写成成功。

三个时间点（之前、C2 后、C3 后）各 154 份源文件原字节/摘要完全相等，三份 `git status --porcelain` 均为空；原输入位置的 673 个 A 文件前后相等。独立验证脚本另行复算 676 份保留输入、8 份实现、4 项结果引用及全部 462 份快照，均通过。详见 `independent-verification.json`。

## 证据与复核

- `run01/C2/`、`run01/C3/`：实际请求、stdout/stderr、退出码、pipeline 原结果与目标解析日志。
- `run01/snapshots/`：完整 154 文件的三次快照，包含合法 `.gitignore`、`.editorconfig`，另附字节摘要与 Git 状态。
- `run01/inputs/A-originals/`：接收的 A 原件；内部 `project.git.tar.gz` 是既有输入原档，未执行其中脚本。
- `run01/inputs/`：profile、候选、正式 fixed-md、单独的篡改副本、匹配请求。
- `run01/*before.json` / `*after.json`、`execution-guard-observations.json`、`project-git-observations.json`：前后记录与实际 Git 命令。
- `run_guarded_negatives.py`：本次执行驱动。它有工作区依赖：`nov28-handoff/review` 当前可信 Git checkout、`nov24-consumption/prepared-inputs`、`nov24-consumption/audit-project.git`；并非在任意解包目录一键重跑。只有明确恢复这些固定来源后，才应使用新的 `--out` 执行。原 `run01` 不能覆盖。
- `verify_preserved_negatives.py`：可移植的只读复算脚本，只需 Python 标准库，不导入或执行包内实验代码。在解包根目录运行 `python verify_preserved_negatives.py run01` 即可复核保存的证据。
- 证据归档排除仅供本次运行的 `run01/working-project/`（含 `.git`）；完整 C1 快照及 A 原仓库归档保留，原请求绝对路径如实记录，没有伪改成解包位置。
- `MANIFEST.sha256.json` 为归档各文件摘要，排除自身；ZIP 外侧另附完整 SHA-256。`package-verification.json` 记录重新读取 ZIP 后全量复算。

此前成功 C1 保留为历史运行：`nov24-consumption/formal-consumption-audit.md`，B Job `job-15dcdf2c3ba24a1487aae245776684bf` / Trace `trace-52029a6df41a43c2ba5c7a39758a5e7b`；它实际完成 DRAFT、五项验证与修复后范围内 MD0，本次未重复。该历史档案不在本小包，负责人结项材料已有相应索引。

## 判定边界

本次可登记“成员一针对真实 A13 三层绑定报告完成 C2/C3 的本地构建前拒绝补验，LOCAL_PREVIEW”。它补齐原先只有教学样例/旧 v2 只读预检的缺口，但不代表双方重新冻结全项目 profile，不代替 A13 本人跨机原件或教师隐藏测试结果。`toml_json → toml.h` 等旧范围外发现的保留状态不因本次拒绝测试改变。

凭据检查的实际范围和模式见 `credential-feature-scan.json`：只扫描本小包拟纳入的原始文件字节中列出的高置信度凭据特征；不递归解码嵌套压缩归档，也不证明不存在未知格式的秘密。扫描仅记录文件路径与匹配类型，不输出任何匹配值。

## 团队取阅

归档 `member1-real-tomlc99-C2-C3-20261128.zip`，919067B，SHA-256 `b312c6db7f7b03820fb86fbc0d0d0cae8f1cec0836dafcd4315898cdf897a3ee`。已上传 `/srv/b13-e13e14-handoff/member1-real-negative-20261128/`，服务器复算通过，已验证成员二本人账号可读；使用本人既有SSH访问，不共享root凭据。ZIP共1186文件，MANIFEST清单1185项，不含工作克隆.git；本页所述脚本与其他JSON在原包中。原件不作为公开Git附件，随负责人交付包提供。
