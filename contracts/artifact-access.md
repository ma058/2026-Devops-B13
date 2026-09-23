# Artifact 访问草案

建议 URI 形如 `artifact://pair13/<producer_job_id>/<filename>`。URI 是逻辑标识，本身不是可直接下载的网络地址。

每条记录应包含 `artifact_id`、`type`、`uri`、`media_type`、`producer_job_id`、完整源码 commit SHA 和 `configuration_id`；可选 `sha256`。

**待与 A13 对齐**：实际存储位置、下载方式、访问权限、保留期限、SHA-256 是否必需。E2 验收要求另一组能读取样例产物；未完成此约定前不得把 URI 标为已联通。

消费方读取前检查：产物存在、生产任务可追溯、源码 commit 与构建配置匹配；若提供 `sha256`，还需检查内容完整性。不要用本地绝对路径代替跨组访问规则。
