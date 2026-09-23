# Job 状态与错误约定（待 A13 确认）

状态：`QUEUED`（已受理）、`RUNNING`（执行中）、`SUCCEEDED`（正常完成）、`FAILED`（执行失败）、`TIMED_OUT`（超时）、`CANCELLED`（取消）。后四者为终态。

- `QUEUED`、`RUNNING`：`output` 与 `error` 均为 `null`。
- `SUCCEEDED`：`output` 必须是对象，`error` 为 `null`。输出可能包含 `MISSING`、`REDUNDANT` findings；发现依赖问题不改变 Job 的成功状态。
- `FAILED`、`TIMED_OUT`、`CANCELLED`：`error` 必须是对象，`output` 为 `null`。如需保留部分产物，在 `error.log_uri` 或另行约定的 Artifact 记录中引用。

错误对象至少包含 `code`、`message`，可选 `log_uri`。课程示例中的 `ENV_3002`（镜像构建失败）、`EXEC_4002`（超时）、`ANALYSIS_5001`（分析器失败）先作为草案，最终错误码需与 A13 对齐。

创建耗时任务时的 HTTP `202 Accepted` 仅表示已受理，响应返回服务端生成的 `job_id` 和 `QUEUED`；不表示构建或检测已经成功。`GET /v1/jobs/{job_id}` 查询进度与最终结果。E2 只定义契约，不要求部署 API。
