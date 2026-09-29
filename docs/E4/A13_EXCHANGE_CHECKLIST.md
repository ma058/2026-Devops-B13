# B13 与 A13 的 E4 互查清单

## 负责人

成员2（Lacrym1ra）直接联系 A13，并把脱敏结果提交到自己的 E4 PR。成员1不作为唯一传话渠道。

## 交换前双方保持一致的内容

- [ ] 仓库 URL
- [ ] E4 使用的完整 40 位提交 SHA
- [ ] README 中的运行入口
- [ ] 服务类型：A13 为 BuildChecker，B13 为 DRAFT
- [ ] 标准命令：`make doctor` 与 `make all`
- [ ] 结论格式：环境、构建、测试、冒烟、密钥扫描
- [ ] 允许差异：镜像 ID、运行时间、日志行数

## B13 请 A13 检查

- [ ] 只看 B13 README，能找到服务器前提与依赖说明。
- [ ] 能找到独立克隆、仓库级 Git 身份和 `make doctor` 步骤。
- [ ] 能理解 DRAFT 冒烟测试中的内层构建失败属于预期结果。
- [ ] 能找到 `make_error_line` 与 `passed: true` 的解释。
- [ ] 能确认 `.env`、`work/` 和真实密钥不会进入仓库或镜像。
- [ ] 若实际重跑，记录所测 SHA 与脱敏结论。

## B13 检查 A13

- [ ] 只看 A13 README，能找到 BuildChecker 的 `make all` 入口。
- [ ] 能找到 A 组 `strace`、`SYS_PTRACE` 和无网络运行约束。
- [ ] 能理解 A 组冒烟预期：`make_exit_code: 0`、`app_output: "1"`、`config_h_opened` 非空、`passed: true`。
- [ ] 能确认 A13 的 `.env`、`work/` 和密钥不会进入仓库。
- [ ] 若实际重跑，记录所测 SHA 与脱敏结论。

## 禁止交换

- 服务器密码、SSH 私钥或完整服务器分配表
- 个人 `.env`、API Key、GitHub Token
- 含凭据的终端截图或日志
- 未脱敏的 `env.json`、镜像历史或错误输出

## 回复模板

```text
A13 同学好，我们开始 E4 README 互查。

B13 仓库：https://github.com/ma058/2026-Devops-B13
E4 提交 SHA：<合并后填写完整 40 位 SHA>
入口：README 中的 E4 章节，标准命令为 make doctor 和 make all。

请只依据 README 检查能否理解并重跑流程，并回复环境、构建、测试、冒烟、密钥扫描五项脱敏结论。请不要发送服务器密码、.env、Token、API Key 或完整 IP 表。

请同时发来 A13 的仓库 URL、E4 完整 SHA 和 README 入口，成员2会直接完成对等检查并把结果写入 B13 的 E4 PR。
```
