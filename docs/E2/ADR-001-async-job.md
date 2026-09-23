# ADR-001：耗时任务采用异步 Job

状态：草案，待 A13 确认。

## Context

Docker 构建、全量/增量检测和 Makefile 修复可能超过普通 HTTP 请求生命周期。跨组还需要查询进度和获取大日志。

## Decision

课程接口采用 `POST` 创建任务并返回 HTTP 202、`job_id` 和 `QUEUED`；执行过程通过 `GET /v1/jobs/{job_id}` 查询。结果中的大文件以 Artifact URI 引用。

## Alternatives

同步等待较简单，但容易超时，也会把客户端与长时间执行过程耦合。

## Consequences

需要持久化任务状态、记录终态错误，并约定查询和产物读取方式。E2 当前只提供契约和样例，不部署服务。
