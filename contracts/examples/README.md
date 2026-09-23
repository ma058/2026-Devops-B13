# E2 示例状态

这里的 URL、40 位十六进制 SHA、镜像名和 `artifact://` URI 都是**合成示例**，不是实际仓库提交、构建镜像或已可下载产物。不能将其计入 E3 真实运行证据。

- `draft.*`、`repair.*` 由 B13 维护。
- `full-check.*`、`incremental-check.*` 仅为便于校验公共字段的临时结构；必须由 A13 提供真实服务专有字段并确认后才能冻结。
- `invalid/` 中的样例必须因预期原因被拒绝。

E2 课程要求缺少 baseline 的增量请求被拒绝；该接口策略与 EChecker 论文在没有历史图时先 clean build 的回退机制不同，见 `docs/E2/ADR-003-baseline-policy.md`。

`scripts/validate.py` 是无需外部包的课程字段校验器，不是通用 JSON Schema 引擎。在具备 `jsonschema` 包的环境中，还应运行 `scripts/check_jsonschema.py` 验证 Schema 文件及样例。
