# ADR-002：产物通过元数据引用交接

状态：草案，待 A13 确认。

## Context

依赖图、构建日志、Dockerfile 和 Patch 可能较大，不适合全部塞进 Job 状态响应。A13 与 B13 需要读取彼此生成的文件。

## Decision

Job 响应只携带 Artifact 元数据，包括 ID、类型、URI、媒体类型、生产任务及源码/配置关联。暂以 `artifact://pair13/<job_id>/<name>` 作为逻辑 URI。实际映射方式仍需 A13 确认；在未确认前，不得声称产物可跨组读取。

## Alternatives

直接嵌入响应会使状态接口过大；仅给本机绝对路径无法跨机器访问。

## Consequences

需要定义 URI 到仓库文件、共享存储或下载端点的解析方式。发生版本不匹配时应拒绝消费产物。必要时用 SHA-256 校验文件完整性。
