# A13 finding-report 2.0 候选固定快照

本目录保存 B13 在 2026-11-10 实际读取并复核的 A13 finding-report 2.0 候选快照。

- 来源仓库：`https://github.com/Dufunare/2026-Devops-A13`
- 来源提交：`c4364e96521a8729fe11695c030916e1746eca1b`（2026-10-10，v2 候选的引入提交：
  schema、正反样例、validator 与测试在该提交中一次性加入）
- 完整性：`manifest.json`（upstream 与 snapshot 哈希逐字节一致）
- 佐证文档：A13 `docs/E2/B13_REVIEW_RESPONSE_2026-10-10.md`（未复制入快照，按仓库原位引用）

## B13 复核结论（2026-11-10）

**接受该 2.0 候选**。`scripts/verify_a13_v2_interop.py` 用 B13 独立实现的
`scripts/validate_v2.py`（不 import A13 validator）完成机器复核：

1. 8 个固定文件 SHA-256 与 manifest 一致；
2. A13 有效样例通过 B13 独立语义校验；
3. A13 五个负例均被拒绝且理由与文档一致（producer_job_id 缺失、顶层未知字段、
   UNRESOLVED 携带 path、evidence 为空、依赖含 `..`）；
4. MDFixer 消费策略在 v2 输入上不变：只消费 MISSING，跳过 REDUNDANT。

A13 样例仍为 synthetic contract fixtures；本快照证明 v2 契约互读与消费链路，
不表示 BuildChecker/EChecker 已运行。

## 与 v1 快照的关系

`contracts/paired/a13/`（v1，固定 `bc1ed352…`）保持不动，v1 证据
`evidence/E3/2026-09-29-a13-interop/` 与 16/16 记录不被改写。v2 为新增候选，
冻结前不替代 v1。

## 运行

```bash
python scripts/verify_a13_v2_interop.py
```

证据输出：`evidence/E2/2026-11-10-a13-v2-interop/`。
