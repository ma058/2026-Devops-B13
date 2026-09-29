# A13 固定契约快照

本目录保存 B13 在 2026-09-29 实际读取的 A13 E2 Artifact 快照，用于 E3 的跨组输入兼容性验证。

- 来源仓库：`https://github.com/Dufunare/2026-Devops-A13`
- 来源提交：`bc1ed352dc0b8ff9e77a69222a69deb03e49a618`
- A13 合并 PR：`#2`
- 完整性信息：`manifest.json`

快照保留 A13 原始 JSON 的字段和值，仅调整排版和结尾换行；`manifest.json` 同时记录上游原始字节 SHA-256。A13 在每份 Artifact 的 `note` 中明确标记它们是 synthetic E2 examples，因此本目录只证明跨仓库读取、字段解析、图差分和 MDFixer 输入过滤可执行，不代表 BuildChecker/EChecker 已运行。

B13 接受并实现以下消费规则：

1. 项目内路径使用相对 `project_root` 的 POSIX 路径，不接受绝对路径、反斜杠或 `..` 越界。
2. MDFixer 只消费 `MISSING`；`REDUNDANT` 保留为跳过记录。
3. `location.status=RESOLVED` 时使用 `location.path`；`UNRESOLVED` 时由调用方提供明确的默认 Makefile 路径，不伪造行号。
4. `artifact://pair13/...` 通过 `repository_url + repository_ref/commit + repository_path` 定位；本快照以完整提交 SHA 覆盖可变分支名。
5. Patch 必须绑定 base commit 与 configuration；修复后再由检测方隔离应用和复检。

运行：

```bash
python scripts/verify_a13_interop.py
```
