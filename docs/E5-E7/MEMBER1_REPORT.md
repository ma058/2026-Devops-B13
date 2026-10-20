# 成员一 E5–E7 执行与交接报告

执行人：B13 成员1 ma058，学号 241880054。日期：2026-10-20。

## 完成范围

已完成公共实验目录接入、真实 E5 失败采集、网络排错、两类候选与来源记录、候选显式构建和镜像 ID 运行、服务构建、E6 接入验证和 E7 基线验证。两位成员仍需在自己的分支完成独立修改、测试、报告与 CI 闭环。

## 来源与自己的改动

教学参考实现、24 个服务测试、DeepSeek 回放候选来自教师实验包。B13 将其放入 labs/B-draft，保留 E2–E4 原目录和历史。

成员1实际改动：

1. 保留镜像摘要并适配 DaoCloud 镜像入口及阿里云 Debian 源，记录首次网络失败。
2. 编写 scripts/run_e5_manual.py，记录命令、退出码、输入和候选哈希，按实际构建镜像 ID 禁网运行并保存结果。
3. 新增 tests/member1/test_e5_recorder.py 四项验收测试，防止错镜像、错误输出或非零退出被误判成功。
4. 保存本次助手读取真实提示后输出的两份 Dockerfile 正文与原始回复，记录来源与选择理由。
5. 整理三人任务、报告、原始证据备份和公共基线。

本次候选由当前 Codex 助手会话辅助整理；助手已读取教师候选，且错误驱动候选与网络适配后的教师候选字节一致，不能作为独立模型生成效果的证据。两类提示也非独立盲测会话。E6 是保存候选的两轮执行，未在线调用模型；符合教学包允许的回放路线。

## 真实执行版本

| 内容 | 完整 SHA |
| --- | --- |
| E4 起点 | 7b231398e34e5e0935c77f7cea8aebefae5039d6 |
| 原始教学接入 | 7f099928ea7b0d083b6c426b404661aab76f7092 |
| E5 网络适配 | d2ee8fc265a9ce111df4c699fcd6111263e26c24 |
| 候选、脚本、正式构建及 E6/E7 基线运行 | e54b1adc9fe81e6c2537beb5f480baabd2ed4b0f |

后续来源说明、任务书和证据摘要提交没有重新冒充上述运行 SHA。服务器使用本人独立目录和镜像标签 b13-draft:241880054-e567。

## E5 复现

- 首次 work/member1-e5-20261020：Docker Hub 连接拒绝，未到达 RUN make。保留为 INFRASTRUCTURE 记录，不算目标失败成功复现。
- work/member1-e5-mirror-20261020：保留 sha256:70729b46… 的镜像摘要、替换访问入口后，实际在 RUN make 失败。Docker build 返回 1，内层提示 make: not found。
- 采集入口退出 0，表示日志和两类提示生成成功，与 Docker build 的退出码含义不同。
- 原始提示与定位 JSON 位于 iter-01；候选在 fixtures/b13-candidates；模型回复在 docs/E5-E7/model-responses。
- 最终选择 error-driven.Dockerfile，SHA-256 为 db8fdf9a1e6377ae916494d5e1608a74d94be8ba1192c27e6db2c1a830d58e4a。它使用 build-essential，保留 FROM/WORKDIR/COPY/RUN make/CMD。上下文候选显式安装 gcc、libc6-dev、make；其独立构建对比交成员2完成。
- 这是解释后的人工选择，不声称执行了论文三候选多数投票。

候选复建：

```bash
cd labs/B-draft
python3 scripts/run_e5_manual.py --candidate fixtures/b13-candidates/error-driven.Dockerfile --out work/member1-e5-manual-20261020 --timeout 600
```

结果：build=0，run=0，stdout 为 hello E3，passed=true。实际镜像：

`sha256:0488ca44a0c3f49afb245265b29d9c1fce3fc7ca43d3e3badfa69cfd20a0568a`

docker run 的最后一个参数为上述镜像 ID，并设置 --network none。--rm 已移除正常退出的容器，随后清理日志的 No such container 对应该已移除状态。

## E6 接入验证

服务镜像构建成功，容器内 pytest 为 24 passed。本机 unittest 只发现 21 个 unittest 用例，另 3 个 pytest 函数测试由服务器 pytest 执行，因此不能用本机 21 代替完整 24。

服务镜像 ID：

`sha256:fe8d2b74b2df7a62c0ccd0dda00a869cdc6bc05d38518c1c3dc4ee759f82bf5b`

work/member1-e6-smoke-20261020：status=SUCCEEDED；第一轮 build=1/failure_class=MISSING_MAKE，第二轮 build=0；运行 exit=0、actual_output=hello E3 换行、output_matches=true。证据校验器通过。

实际构建并验证的镜像 ID：

`sha256:a5a4d7af1e30a05a0a0c60a52452e0da09a01733a93f303cc5059db41476fa58`

trace_id：e6-b-7ed9bfc3ebcd4ef28219ec8e208a2b9c。

## E7 公共基线

work/member1-e7-baseline-20261020/gate/gate-result.json：

| 场景 | 实际状态 | 退出码 | gate 判定 |
| --- | --- | --- | --- |
| 服务测试 | 24 passed | 0 | PASS |
| success | SUCCEEDED | 0 | PASS |
| wrong-output | FAILED | 1 | PASS |
| invalid-candidate | FAILED，构建前拒绝 | 1 | PASS |
| build-failed | FAILED，第二轮失败 | 1 | PASS |
| runtime-timeout | TIMED_OUT，运行容器已移除 | 1 | PASS |

整体 gate 退出 0。工作区、历史和镜像扫描未发现问题。成员1新增的四项 E5 证据验收测试独立通过，不计入教学 24 项。

## 证据与备份

Git 摘要路径：evidence/E5-E7/member1/，保留原始目录结构，包含提示、关键 JSON、测试日志、程序输出和 gate 表。摘要文本统一行结束；原始字节以备份归档为准。

完整原始备份：b13-member1-e567-evidence-20261020.tar.gz。

SHA-256：593d090e7c0bb441bc7b8427382f0f019b5f21ba300a10eae8ea0d51b9dc5602。

该备份包含首次基础设施失败、修复后 E5、手工候选复建、服务构建、E6 和 E7 各场景的完整输入及日志；不含 .env、SSH 私钥、Git 凭据或 .git。

## 尚依赖队友的收口事项

- 成员2：Review 成员1基线；独立 E6、证据校验扩展和双候选对比。
- 成员3：独立 E7、门禁判定扩展、正式 CI、保护配置、失败 PR 拒绝和恢复。
- 成员1随后：Review 成员3、必要的仓库管理员配置、整合两人记录、主分支最终验收与提交包。

这些任务尚未完成，当前交付是成员一基线和工作交接，不能标成全组 E5–E7 最终完成。
