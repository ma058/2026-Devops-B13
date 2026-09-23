# E2 公共契约校验记录

- 日期：2026-09-22
- 范围：3 份 JSON Schema、8 份有效任务样例、3 份无效任务样例
- 状态：B13 本地草案已通过；A13 尚未确认专有字段与产物读取方式

## 检查 1：标准库校验器

命令：`python scripts/validate.py`（Windows Python 3.12.14）

结果：退出码 0；8 份有效样例通过；未知 `job_type`、缺 baseline、失败终态缺 `error` 分别被拒绝。

## 检查 2：单元测试

命令：`python -m unittest discover -s tests -v`（Windows Python 3.12.14）

结果：退出码 0，9 项测试全部通过。包含四类请求/结果、未知任务类型、baseline 缺失/版本不符、状态错误、MD finding 与 Artifact 生产任务匹配等检查。

## 检查 3：正式 JSON Schema 校验器

命令：`python3 scripts/check_jsonschema.py`（WSL Ubuntu Python 3.12.3，已安装 `jsonschema`）

结果：退出码 0；3 份 Schema 的 Draft 2020-12 结构检查通过；8 份有效实例通过；3 份无效实例均被拒绝。缺 baseline 样例的拒绝原因是缺少必填 `baseline`。

## 限制

示例中的 URL、commit、镜像和 Artifact URI 均为合成值，不代表真实构建或跨组访问成功。FULL_CHECK、INCREMENTAL_CHECK 的专有字段由 B13 暂拟，须在 A13 互审后替换或确认。成员1工作已登记到 GitHub Issue #1；E2 实现提交为 `af194c40ffd1394fb56cc9f5b2367b7feffb5a3b`。功能分支尚未推送，PR 尚未创建。

## 2026-09-23 复验

在 Windows 重新执行标准库校验器和 9 项单元测试，在 WSL Ubuntu 重新执行正式 JSON Schema 校验，退出码均为 0。当前 WSL 使用的 `jsonschema` 版本为 4.10.3。复验仍只证明 B13 本地契约草案自洽，不代表 A13 已接受专有字段或成功读取产物。
