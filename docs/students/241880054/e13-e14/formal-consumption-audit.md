# 成员一 tomlc99 正式消费证据审计（2026-11-24）

结论：**PASS_FORMAL_E11_B_CLI_CONSUMPTION**。下载归档的完整性、A13 新报告绑定、真实 DRAFT 两轮、同一镜像内补丁验证与复检、源码变化范围及清理记录均通过核验。本记录由工具辅助独立检查下载原件产生，没有重新执行项目或修改服务器。

## 执行身份与输入

| 项目 | 固定值 |
| --- | --- |
| B13 执行代码 | `f05faf5bcd3496184c580dc30e710cc960bf0398` |
| B13 本次 job | `job-15dcdf2c3ba24a1487aae245776684bf` |
| B13 本次 trace | `trace-52029a6df41a43c2ba5c7a39758a5e7b` |
| A13 报告源 job | `job-fd1b21e39d41474699e43815b402804e` |
| A13 报告源 trace | `trace-ad14eb26d03f4129a38ab57ad626c72a` |
| C0 | `592fc6f3d2463a58fe7f60b8d255ed242740bec0` |
| C1 | `b2dda5513fe4a7d250493528800fe425cae459a5` |
| profile SHA-256 | `0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1` |
| 派生 fixed-md 输入 SHA-256 | `328ec838926af9eee76781563de20ccd4404ff4b77e7086318db66005ac6f9ef` |
| 成员一已有环境镜像 | `sha256:bd6407d706b8a3174a5444e1363cb0432f3e2eae70dcb0a36a7d1c1e0cb5afad` |
| 本轮 DRAFT 成功镜像 | `sha256:d60fbdbfff205562b47a8d738dde22a9502761c1680de8792cb5e451c220cdf3` |

执行方式为成员一授权、Codex 辅助的独立 CLI，使用上述已有环境镜像运行 `pipeline.py` 的 `e11-b` 路线，成功时段为 **2026-11-24 01:22:57–01:23:04 UTC**。没有把任务提交到生产 API，没有登记为成员一或其他同学人工独立运行。归档中的生产服务 `/health` 只是事后可用性检查。

## 下载原件与完整性

- 归档：`member1-tomlc99-formal-consumption-20261124.tar.gz`，866065 字节。
- SHA-256：`6159962922a0b6805c9655e14cfd1cd3d69fc813abfbae190548d4ddade5cdc5`，与 `.sha256` 及 `export-summary.json` 均一致。
- tar 仅含安全相对路径普通文件，无重复、大小写碰撞、链接或特殊文件；清单 1384 项逐一复算通过，恰好覆盖清单自身以外的文件。
- 已递归遍历 115 份 JSON：1358 次带字节数/摘要的 B 侧工件引用全部匹配，对应 1347 个唯一 URI；源报告中另有 6 次仅含摘要的 A13 链接，也均与本次已核验的 A13 原件相符。
- 四阶段 `draft → fixed-md → repair → recheck` 共享同一 B13 job/trace、C1、profile，全部 `SUCCEEDED`。B 侧保存的 fixed-md 输入与独立预检派生件逐字节一致，源 result/stage/payload 的摘要及 A13 job/trace 绑定保持原值。

## 真实构建、验收与修复结果

1. DRAFT 两次实际执行 `docker build`。首轮原始日志记录 `make: not found`、底层 exit 127，外层 build exit 1，分类为 `MISSING_MAKE`；第二轮 build exit 0，产出上述不可变镜像 ID，运行输出字节为 `7b7d0a`（`{}\n`），退出码 0。
2. 第二轮日志明确出现 `CACHED`，包括安装工具与编译层。因此登记为真实 Docker 构建且使用缓存，不写成无缓存重新安装或全量重新编译。候选来自已交付 Dockerfile 的教学回放，没有新的模型/API 调用。
3. 后续 `validate` 与 `full` 各自创建真实容器，创建/结束 inspect 的镜像 ID 均等于本轮 DRAFT 镜像；两容器退出码均为 0，worker 自报 UID 均为 10001。随容器复制的四份 worker/分析源码均与 f05 提交的 Git blob 摘要一致。
4. `accepted=true`，`patch_applies/build/test/header_change/no_missing` 五项都为 true。头文件探针原始 strace 重算得到成功的 `/usr/bin/cc` 调用，确实以固定编译参数编译 `toml.c → toml.o`，mtime 从 `1795483381253008480` 增长到 `1795483382849008026`。修改头文件前后运行输出均为 `{}\n`，退出码均为 0。
5. 用固定 f05 分析器重新分析最终 **10 份原始 strace + Make 数据库**，发现、实际图、声明图、进程图与保存结果逐字段一致。范围内 `toml.o` 的 MISSING 为 0；全项目仍保留范围外 `toml_json → toml.h`，没有扩大为全项目缺陷清零。
6. 与可信 Git 数据中的 C0/C1 逐 blob 对比：C0 152 份源码一致，DRAFT 输入的 C1 154 份源码一致；最终 target-project、最终复检副本的 154 份受跟踪文件中仅 `Makefile` 按补丁变化。验证沙箱另有预期的 `toml.h` 追加探针字节，未写回目标源码。

唯一接受的 Makefile 修改为：

```diff
-toml.o: toml.c
+toml.o: toml.c toml.h toml_extra.h
```

修复后 Makefile SHA-256：`3602a2f363cced6bfacd5b7a71882adc69c1309887a59240356feef0130ec1f2`。

## 执行代码、输入与权限边界

1005 份执行源码归档清单一致，服务器导出前再次核验未变化；683 份输入的前后清单相等，并与本地准备副本摘要相等。源代码归档与 f05 Git blob 核对时，1004 份字节完全一致；唯一差别是 `docs/students/241880115/e11-e12/数据与联调记录.csv`，因 `text=auto` 和系统 `core.autocrlf=true`，`git archive` 将 LF 转为 CRLF（3971→3981 字节），换行规范化后完全相同。运行代码没有此差异，不将 1005 份全部写成 Git blob 原始字节相等。

外层编排容器使用 UID 配置 `10001:10001`、`no-new-privileges`；`/course` 与 `/inputs` 只读、`/evidence` 可写，同时挂载可写 Docker socket。因此不能把非 root 描述为无宿主 Docker 能力。两个下游 worker 为 UID 10001、网络关闭、无宿主 bind mount，并记录 no-new-privileges。

两个下游容器的 `docker rm` 返回 0，事后逐 ID inspect 均返回不存在；两次外层容器清理均返回 0，事后容器列表中没有本任务名称。DRAFT 输出核验容器使用 `--rm`，后续清理日志记录其已不存在。未把服务器其他仍在运行的容器列为本任务残留。

## 首次准备失败独立保留

`evidence/` 保存首次执行：**01:21:11 UTC、exit 128**，错误为 `/inputs/project.git` 不被识别为 Git 仓库，流水线尚未生成 result。准备 tar 只打包文件，漏掉空的 `refs/` 目录；第二次在服务器补建该空目录后，使用新的 `evidence-attempt02/` 重试成功。输入文件摘要没有修改；首次日志与清理记录保留原状，未覆盖、未计为实验成功。

审计时没有修改 `prepared-inputs`，通过核对其 HEAD、packed-refs、shallow、pack/index 与安全恢复副本相等，再从恢复副本读取 C0/C1 Git blob。

## 可复查文件

- `formal-consumption-audit.json`：机器可读核验结果与执行边界。
- `formal-consumption-reference-audit.json`：全部递归工件引用核验。
- `formal-consumption-recomputed-graphs.json`：从原始 trace/Make 数据库独立重算的结果。
- `audit_formal_consumption.py`：只读审计程序；仅调用可信 `verify_result` 和分析函数，没有调用 `formal` 或 `main`。
- `server-evidence/`：安全提取的原件副本；原 tar 与 SHA 文件保持不变。

本记录可支持本次 A13 新报告的 B13 E11-B 正式消费回签。它不替代其他服务联调、教师隐藏测试或尚未交付的 E13–E14 验收项。
