# B13 通用运行证据（0.1，组内待确认草案）

成员2维护格式和 `scripts/collect_evidence.py`；各样本负责人生成自己的真实证据。
这不是 E2 Job Schema，也不表示 A13 已确认。历史证据保留，不倒填缺失信息。

## 目录与字段

```text
evidence/E3/<日期>-<时间>-<工具>-<风格或样本>/
  observations.md
  verify.log
  summary.json
  001.stdout.log
  001.stderr.log
  ...
```

三份主文件兼容原 Implicit 风格；分流日志保留原始字节。已有输出目录会被拒绝，避免覆盖。
`verify.log` 按命令记录 stdout、stderr 两段，不声称保留两个流的交错时间顺序。

| summary 字段 | 含义 |
|---|---|
| evidence_schema_version / format_status | 0.1 / B13_DRAFT，与 Job schema_version 分开 |
| run_id / suite / case | 目录运行编号、阶段、具体样本 |
| started_at / finished_at | UTC ISO 8601 时间，带时区 |
| source | 仓库 URL 查询结果、完整 HEAD、dirty、Git 状态、运行前源码文件 SHA-256 |
| environment | 实际采集进程 OS、架构、cwd；Docker 基线另记容器 OS、架构、工具输出 |
| tools | Python/Git/Make/GCC/Docker 版本；不可用时 value=null，reason 说明原因 |
| commands | argv 数组、cwd、时间、exit_code、timed_out、execution_error、分流日志相对路径 |
| checks | id、expected、actual、status、command_id |
| artifacts | 本证据目录日志和附件的相对路径及 SHA-256 |
| provenance | 人工 Oracle 或检测器来源；detector_executed 默认为 false |
| result | PASS / FAIL / INCOMPLETE / NOT_RUN |
| image / base_image | DRAFT 附加字段：实际镜像 ref/ID/digest 和基础镜像 inspect 记录 |

源码未提交时 HEAD 不足以标识运行内容，因此必须同时保留 dirty 与 file_sha256。
源码指纹排除 evidence/、Git 忽略文件；摘要不对自身求哈希，避免循环引用。
Docker 镜像 ID 不是 registry digest；本地镜像没有 RepoDigests 时记空数组，不虚构 digest。

## 最小接入：包装已有脚本

在仓库根目录运行（Python 命令按本机环境选择）：

```sh
python scripts/collect_evidence.py --output evidence/E3/2026-09-24-implicit-run01 --case mdfixer-implicit -- python scripts/verify_implicit.py
```

此方式只产生 `command_exit` 检查，具体行为断言仍在原脚本和原始日志中。
它不会从 exit=0 推断出 MD=0、产物等价或所有内部步骤通过。

成员3脚本合入后，可用同样命令替换为 `scripts/verify_mdfixer_explicit.py`；
在当前未提供该脚本的版本中，显式样本接入只能标待验证。

## 逐项接入：由样本脚本提供结果

```python
from collect_evidence import Recorder  # scripts/ 下脚本可直接导入

r = Recorder(output_directory, "E3", "mdfixer-target")
try:
    command, stdout, stderr = r.run(["make"], cwd=temporary_fixture)
    r.check("build", 0, command["exit_code"], command["exit_code"] == 0, command["id"])
    # 由样本负责人调用其他命令，并比较输出、依赖及哈希。
except Exception as exc:
    r.check("runner_error", "no exception", repr(exc), False)
finally:
    r.finish("人工 Oracle；A13 EChecker 尚未运行。")
```

`run` 不使用 shell 自动解析；管道/复合命令需要显式传入 `sh -c` 或相应 shell。
`--cwd` 决定命令目录，source 仍绑定本仓库；Python API 可用 root 指定其他源码根目录。
命令超时保留已采集输出，exit_code=null、timed_out=true。无法启动时记录 execution_error。

## 判断规则

- 检查项：PASS / FAIL / SKIPPED / NOT_RUN。必需检查缺失时应显式添加 NOT_RUN，不能省略后称全部完成。
- 有 FAIL 则总体 FAIL；无 FAIL 但有 SKIPPED/NOT_RUN 则 INCOMPLETE；全 PASS 才 PASS；无检查则 NOT_RUN。
- broken 构建预期失败需要同时确认非零退出及工具链缺失原因。普通命令包装的 `--expect-exit` 只检查退出码，不能代替此语义判断。
- 人工 Oracle 与 A13 检测必须区分。若某测试套件不包含 A13 检测，可在 provenance/观察说明注明未运行，不将人工测试的 PASS 扩大为联调成功。
- 超时、网络失败不能冒充预期的构建失败。
- stdout 和 stderr 不做脱敏；不要传入密钥或凭据。代理参数如含凭据，须先改为无凭据的任务局部通道。

## 已验证与限制

见本次 evidence/E2 和 evidence/E3 实际目录。现有 Implicit 可使用命令包装接入；
显式三风格脚本不在当前仓库，由成员3接入后生成自己的记录。
本工具不实现远程 Artifact 发布，不自动提交 Git，也不覆盖任何人的旧证据。

## 干净提交复验（成员2，2026-09-26）

先提交代码，再将本批输出写到仓库外的新目录；全部完成后复制到 evidence/ 并单独提交。
这样每项记录采集的 Git 状态都是实际完整工作区状态，不需要过滤未提交证据来得到 dirty=false。

现有镜像复验入口：`python scripts/recheck_draft_image.py --image <本地镜像ID或标签> --output <仓库外新目录>`。
它固定 inspect 返回的镜像 ID，检查两次运行、当前 fixture clean build 和容器工具信息；
不声称重建 Dockerfile 或再次验证 broken 镜像。首次完整基线仍见 2026-09-24 记录。

显式样本 PR #7 已有独立采集器；尚未合入本分支。包装命令只增加 command_exit，
不会自动把内部检查转换为逐项检查；各风格 summary.json 仍需保留并校验。
