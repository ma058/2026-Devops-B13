# 成员一：b13-level-v1 真实 A13 报告 C2/C3 补验

结论：当前 main 的现有严格实现可直接消费这份已核验的真实 A13 报告，无需增加适配或放宽约束。2026-11-28 UTC 13:00:55–13:01:01，马宇航（241880054）授权 Codex 在 Windows 10 / Python 3.11.8 的新隔离目录执行两个构建前拒绝场景，均通过。本次为 `LOCAL_PREVIEW`，不声称由 A13 本人跨机执行，不代替组级 RC 验收。

## 身份与原件

- 本次实际代码：`fb4be620da9587ea3dc35581eeb2599ffe98fae7`。8 个导入文件先与 Git blob 逐字比较再复制至 `run01/implementation/`；未改实现。对应完整源码 ZIP SHA-256 为 `8e5aed518902eb42fca3f88d7fc2cd640e60033943acb0e98f3ec8a871abf330`，完整 ZIP 另在负责人 `nov28-final/github/B13-source-fb4be620.zip`，本小包保留所用 8 文件。
- A13 源 Job：`job-456068d41f694e8aa563d29bdcbf1849`，Trace：`trace-4707d6738c354193ab3f2ea19290c0a2`；原 result 53,330 字节，SHA-256 `92d1a700d96cf253ae597d32f9f51b4410ac3be7961698059922e72718126664`。
- A13 外部接收包登记 SHA-256：`5a5b213f4d2fbe8fd91526ceb341244f1656aea559ffcd8791c09e91f6a056cb`，133,116 字节。外层包与 M2 消费原件已在 `nov26-closeout/member2-original-audit/independent-audit.md` 独立核过。本小包复制该 A Job 目录的 242 个文件，保留前后原位置摘要。
- 项目 C0：`cb6545b3e8eddda5bec89b12ee390ae5e930f822`；C1：`5cfaf2014db78635b61d88b62760481834a344d5`。从已接收的 `project.bundle` 克隆，核实祖先关系及 C1 的 10 个受跟踪文件逐字匹配 Git blob。bundle 原件随 `run01/inputs/` 保存。
- 原冻结 profile `b13-level-v1`，canonical SHA-256 `f0367b454aff9cb0a5304e3e3330b61d4bbd01c3f19069eaf5930a1664d3733b`，修复目标 `main.o`、`helper.o`。
- 当前 handoff 转换器重新核验 A 的三层绑定和所有声明引用，派生出与既有接收件相同的 fixed-md：3,116 字节，SHA-256 `1a40bf524133427de60271c843865a3e37908b9298b998def6e9d3c9da0644e4`。匹配 C1 的真实 `read_fixed_report` 正向对照通过。

## 新执行结果

| 场景 | 改动 | 新 Job / Trace | 结果 |
| --- | --- | --- | --- |
| C2 | 只将请求 target 改为真实存在的完整 C0 SHA；不改报告 | `job-33e9069c4b7f42e6a416c1c744cda594` / `trace-43c98a86451b4946876ecc450524b03e` | `STALE_REPORT`、退出码 1、`stages=[]` |
| C3 | 只将 fixed_report 路径换成单独加一个 LF 的副本；仍传旧 hash | `job-5195ff52f42740b5b00e7e295d9cc128` / `trace-fa219533216d4862a3bb2b3075ffd273` | `ARTIFACT_HASH_MISMATCH`、退出码 1、`stages=[]` |

C3 副本 3,117 字节，SHA-256 `846c48b9a47dde877d2668c6b21e2c304932e0f1339d2a60ab9b119ca60a2682`；JSON 结构仍合法，错误来自字节摘要不符。

调用的是当前原样 `pipeline.main()` 与 `read_fixed_report`。驱动对 snapshot、DRAFT、Docker/image runtime、scan/patch/validate 入口施加 fail-stop guard；若进入任一入口，会抛出 `RuntimeError` 并让本次验证失败，不返回伪造成功。实际只执行了真实 Git 目标解析，guard 记录为零，没有构建、编译、修复、服务器配置或新 HTTP 操作。

三份完整源码快照各 10 文件，字节与 hash 全部相同，三份 Git 状态为空；原位置的 242 份 A 文件不变。另一个只读标准库验证器重算了 246 个保留输入、8 个实现文件、4 个结果引用及 30 份快照，并核实请求差异仅为约定字段，全部通过。

## 复核入口与脚本依赖

解包根目录运行 `python verify_preserved_negatives.py run01`，只复算保存的文件，不运行实验代码、不联网。完整摘要计数见 `independent-verification.json`。实际请求、结果、stdout/stderr、退出码见 `run01/C2/` 与 `run01/C3/`；guard、Git 命令、A/输入前后摘要、篡改说明及来源索引均保留。源快照包括合法隐藏文件。

`run_guarded_negatives.py` 是实际驱动原件，不是独立环境安装器。它依赖负责人工作区的可信 checkout `nov28-handoff/review`、已审计的 `nov26-closeout/member2-original-audit/archive-03/job`、`archive-02/runs/b-run-30dcucih/inputs`。重新执行须先恢复这些固定来源并使用全新输出目录；不能覆盖 run01。代码未从 A 原件导入执行。

证据 ZIP 不含仅供运行的 `run01/working-project/` 或其 `.git`；保留 project.bundle 及完整受跟踪源码快照。原请求路径如实记录为执行时的 Windows 绝对路径。清单排除自身，外侧另附完整 SHA-256；`package-verification.json` 记录重开 ZIP 后全量复算，文件本身位于 ZIP 外侧避免循环引用。

历史成功 C1 必须另记：成员二 B Job `job-a7e0a32b540e4749b49555e4692ee086` / Trace `trace-9652067df8f8442495c72de59c11eaa8` 的接收源码为 `ebdaeed36c0255a425f49cbf5c75ae8eeed2cac5`，实际完成 DRAFT、修复、复检，已由 PR #52 集成。此历史执行不是本次 main 的执行，也不是成员一本人运行；本次没有重复其成功链。

凭据特征扫描仅覆盖拟纳入本 ZIP 的原始文件字节，检查私钥头、GitHub token、AWS access-key 形状；详见 `credential-feature-scan.json`。不递归解码嵌套归档，不保证未知秘密形式不存在；不输出任何匹配值。

## 团队取阅

原件 `member1-real-b13level-C2-C3-20261128.zip`，315998B，SHA-256 `4f05cc4a351e5325dd965f00ac2158e7e153184bab83da3e682644c7b889d780`，已上传 `/srv/b13-e13e14-handoff/member1-real-negative-20261128/`，服务器复算通过且成员二本人账号可读。ZIP共324文件，清单323项；本页其他脚本/JSON在原包中，随负责人材料提供，不将原始输入全量上传公开Git。
