# E13 A→B 报告接入约定（B13 实现）

版本日期：2026-11-22。此文说明本组已实现的接收边界；A13 本轮项目和字段回签仍需单独登记。

## 正式交付输入

1. A 成功任务的 `result.json`，`schema_version=e11e12-1`，`status=SUCCEEDED`，`target_commit` 为约定完整小写40位SHA。
2. 唯一 `incremental-check` 阶段引用，指向 `artifact://<job>/incremental-check.json`。
3. 该阶段恰好一个 `artifact://<job>/incremental-report.json` payload 引用；`data` 与其 JSON 内容严格一致。payload 为 `e8e10-1`，commit 与 target 一致；findings 使用 MISSING/REDUNDANT、非空 target/dependency。
4. 全部被引用文件原字节、大小、SHA-256。路径为本任务目录内的普通相对 POSIX 路径，不允许跨目录、反斜杠、重复URI或符号链接。
5. 独立交付记录中的 result SHA-256、job_id、trace_id；B13 将其与收到的内容核对。哈希用于与约定记录比对，不等同于发送者数字签名。
6. 使用真实项目 profile 时，result、incremental envelope 和 payload 的 `profile_sha256` 三层一致，并另交 profile 内容/构建和修复范围。缺失字段应由 A 生成端按确认版本重发，B 不改写原件凑字段。

## 转换命令

在已配置 E11–E12 依赖的环境中，以实际值替换占位符，使用新的输出路径：

```bash
python3 labs/e13e14/handoff_a_to_b.py \
  --a-result /course/work/received-A/result.json \
  --target-sha <40位目标SHA> \
  --result-sha256 <独立交付记录中的64位SHA256> \
  --expected-job-id <A源job> \
  --expected-trace-id <A源trace> \
  --out /course/work/derived-A/fixed-md.json
```

校验使用读取到的同一份字节缓存；payload 的旧消费器规则复用到新适配器，拒绝重复 JSON key、非法/非有限数值和身份/内容冲突。输出保存 A 源任务/trace、阶段/payload/result hash 以及各项外部绑定是否已核验。源报告文件保持不变。

两参数 `make_handoff(result,target)` 仍支持教学调用；未提供独立记录的字段标为未核验，不能据此宣称已取得 A13 确认。

## B 的 E11-B 请求

沿用现有 `mode/repo/base/target/candidate/expected_output/build_timeout`，增加：

```json
{
  "fixed_report": "/course/work/derived-A/fixed-md.json",
  "fixed_report_sha256": "<派生文件实际64位小写SHA256>"
}
```

这是请求片段，不是可独立运行的完整请求。profile、profile_sha256、image_probe 等仍遵循现有约定。

`fixed_report_sha256` 可选以保持旧请求兼容；一旦给出，空/null/错误类型/错误格式都明确拒绝。本轮正式交接应提供该字段。B 只读解析目标提交后，在任何 clone/DRAFT/修复之前校验 hash、固定信封、payload 和 profile，再消费同一份缓存字节。

收到的派生文件原字节保存在 `fixed-md-input.json`，result 的 `fixed_report_binding` 登记实际 hash、大小、是否核对外部 hash 和 source_report。旧报告拒绝现在发生在构建前，`stages=[]`，这是加强后的行为；不再为了拒绝旧报告先运行 DRAFT。

## 接口边界与后续共同确认

- 以上适用于 E11/E12 风格 A result → B fixed-md；E14 `e14-compose-1` 有独立的产物格式，成员二/三实现服务时需要明确映射。
- 新四角色 `/v1/run` 是同步接口。C8 在旧异步 `/v1/jobs` 上验收，不将两者能力混为一谈。
- 成员二负责实际项目、profile 与服务执行；成员三负责角色编排/产物下载/日志；成员一负责交接与验收。
- A13 的实际项目清单、当次报告、独立 hash/源任务信息未收到前，本方生成样例只作准备验证。
