# A13 → B13 E3 互操作验证

- A13 仓库：`https://github.com/Dufunare/2026-Devops-A13`
- A13 固定提交：`bc1ed352dc0b8ff9e77a69222a69deb03e49a618`
- 输入：A13 FULL_CHECK/INCREMENTAL_CHECK Artifact 与 finding Schema 固定快照
- 结果：16 / 16 检查通过

本次验证实际读取了 A13 仓库提交中的 JSON，并核对来源、上游 SHA-256、本地快照 SHA-256、报告结构、Artifact locator、图差分、MISSING-only 消费规则和路径安全规则。`normalized-full.json` 与 `normalized-incremental.json` 是 MDFixer 消费视图。

A13 原始文件明确标记为 synthetic E2 examples，因此本证据只证明跨组契约与消费链路可执行，不声称 BuildChecker/EChecker 已运行。真实检测器接入后可以复用同一验证入口替换输入。
