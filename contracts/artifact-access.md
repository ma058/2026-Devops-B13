# Artifact 访问约定

逻辑 URI 使用：

```text
artifact://pair13/<producer_job_id>/<filename>
```

逻辑 URI 不直接承担下载功能。跨组样例采用 repository-backed locator：

```json
{
  "uri": "artifact://pair13/job-full-a13-001/md-report.json",
  "repository_url": "https://github.com/Dufunare/2026-Devops-A13",
  "repository_ref": "bc1ed352dc0b8ff9e77a69222a69deb03e49a618",
  "repository_path": "contracts/artifacts/job-full-a13-001/md-report.json"
}
```

## 解析步骤

1. 只接受允许的 Git 仓库 URL，并把可变分支名解析为完整 40 位 commit SHA。
2. 在隔离目录检出该 commit，不使用发送方本机绝对路径。
3. `repository_path` 必须是仓库内 POSIX 相对路径；拒绝绝对路径、反斜杠、`..` 和 `./` 前缀。
4. 检查 Artifact 的 `producer_job_id`、repository commit 与 configuration 是否和任务一致。
5. 若交付提供 SHA-256，则在解析 JSON 或应用 Patch 前校验原始字节。
6. Patch 额外绑定 base commit 与 configuration，只在隔离工作区应用。

每条 Artifact 元数据至少包含 `artifact_id`、`type`、`uri`、`media_type`、`producer_job_id`、完整源码 commit SHA 和 `configuration_id`；建议提供 `sha256`。

## 已执行的跨组读取

B13 已读取 A13 `bc1ed352dc0b8ff9e77a69222a69deb03e49a618` 中的 actual graph、declared graph、FULL/INCREMENTAL MD report 与 finding Schema。固定来源、上游 SHA-256 和本地快照见：

- `contracts/paired/a13/manifest.json`
- `contracts/paired/a13/artifacts/`
- `evidence/E3/2026-09-29-a13-interop/`

共享对象存储或 HTTP 下载端点可以在后续实现中替换 repository-backed locator，但逻辑 URI、版本绑定和完整性检查保持不变。
