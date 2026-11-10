# ADR：成员3——异步 API 幂等、重启恢复与 HTTP 产物边界的验证策略

编号、日期、作者：ADR-E1112-M3 / 2026-11-10 / 于泉宇（241880115，yqy241880115）

问题：E12 的共享编排 API 承载跨组联调，必须在三个维度上可信：①并发下的幂等语义（同键同请求不产生重复构建）；②服务崩溃/重启后的状态与证据处理；③产物下载的路径边界（不允许越界读取 API 主机文件）。教师契约已有 10 项、成员1 已有 28 项测试，如何以独立预期补充而非重复覆盖？

候选方案：

- A. 只复跑 api_probe 端到端：覆盖真实 HTTP 但每次都要执行完整 E12 管线（分钟级），无法快速回归；且 api_probe 不制造真并发窗口。
- B. 直接对 server.py 源码做静态走查：无行为证据，不满足"测试方向"要求。
- C. 分层测试：并发幂等与重启恢复在 Store 层用 RecordingPool 替换线程池（毫秒级、不触发 Docker）；HTTP 边界在真实 socket 上验证（手工在磁盘 staging 证据，不执行管线）；端到端另有 api_probe 实测补足。

采用方案与原因：C。三个方向各有最合适的层——幂等并发是 Store.submit 的锁内逻辑，重启恢复是 Store.__init__ 的磁盘重放，二者都不依赖网络与管线；HTTP 边界必须过真实 socket（URL 解码、unquote、resolve、.git 拒绝都发生在 Handler 内）；端到端行为由 api_probe 的 156 文件核验提供。分层使 11 项新增测试在 0.1 秒内完成，可随 CI 高频回归。

输入输出字段：

- 并发幂等断言面：`job_id` 唯一性、`pool.submit` 调用次数、任务目录数、`store.keys` 大小。
- 重启恢复断言面：内存与 `state.json` 磁盘双写一致（FAILED/SERVER_RESTARTED）、已完成任务状态保持、幂等键映射恢复后同键命中旧 job 不再入队、旧证据目录保留。
- HTTP 边界断言面：200 时 body/`X-Content-SHA256`/清单三方 SHA 一致；404 时返回 `{"error":"NOT_FOUND"}` 且不携带 X-Content-SHA256；RUNNING 任务 artifacts 为 409 `RESULT_NOT_READY`。

兼容性与测试：

- 与已有 38 项的差异化：`test_contract.test_same_key_same_request_same_job` 为串行两次 submit，本 ADR 的并发用例是 8 线程 barrier 同时进入（覆盖锁竞争窗口）；`test_member1_api_client.py` 测客户端 `safe_download_target`，本文件测服务端 Handler（%2e%2e 编码、.git、RESULT_NOT_READY）。
- RecordingPool 只替换 executor，不修改 Store 业务代码；真实服务重启另有 kill/重启实测（156 产物重下载 SHA 一致）佐证单测语义。
- 首版 HTTP 断言曾误设"错误响应体为空"，实测服务端返回 JSON 错误体后修正断言——按"保留失败、修正预期"原则记录，不放宽服务端行为。
