# B13 与 A13 的 E4 交流与互查文档

## 负责人

成员2（Lacrym1ra）直接联系 A13，并把脱敏结果提交到自己的 E4 PR。成员1不作为唯一传话渠道。

## 2026-10-10 公开信息快照

- A13 仓库：<https://github.com/Dufunare/2026-Devops-A13>
- A13 当时的 `main`：`9bafaf8ef2dd7397631fd80d6b8c021f88ca6116`
- A13 E4 入口：`docs/E4/README.md`
- A13 服务：BuildChecker
- A13 README 标准命令：`make doctor`、`make all`
- A13 README 公开预期：测试通过；冒烟结果 `passed: true`，能够观察到 `config.h` 被打开，程序输出为 `1`；密钥扫描未发现问题。

上述 SHA 只是互查开始时的快照。A13 回复时应重新给出其实际用于 E4 的完整 SHA，B13 不把旧 SHA 当作最终结果。

## B13 对外提供的信息

- B13 仓库：<https://github.com/ma058/2026-Devops-B13>
- B13 E4 运行基线：`519ca0fce2a5417e3f855a101bc5c938252a03d5`
- B13 E4 入口：根目录 `README.md` 的“E4 工程骨架”以及 `docs/E4/README.md`
- B13 服务：DRAFT
- B13 标准命令：`make doctor`、`make all`
- B13 已验证结论：`4 passed`；冒烟中的内层构建按预期失败，`make_error_line` 含 `make: not found` 且最终 `passed: true`；密钥扫描通过。

## 可直接发送给 A13 的消息

```text
A13 同学好，我们开始 E4 README 对等互查。

B13 仓库：https://github.com/ma058/2026-Devops-B13
B13 E4 运行基线：519ca0fce2a5417e3f855a101bc5c938252a03d5
B13 入口：根 README 的“E4 工程骨架”和 docs/E4/README.md
B13 标准命令：make doctor、make all

请只依据 README 检查流程是否足够复现，并按“环境、构建、测试、冒烟、密钥扫描”五项回复接受／建议修改／待定。B13 的 DRAFT 冒烟样例会让内层 Dockerfile 因缺少 make 而失败；smoke.json 的 passed=true 表示工具正确识别了这个预期失败，并不表示内层构建成功。

也请提供 A13 实际用于 E4 的完整 40 位 SHA、README 入口和五项脱敏结论。请不要发送服务器地址或密码、SSH 信息、.env、Token、API Key、完整服务器分配表或未脱敏日志。

本轮由 B13 成员2直接对接和记录，不需要经成员1转发。
```

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

## A13 回复记录模板

成员2收到回复后复制本节到自己的运行报告中填写，不保存私人聊天截图。

| 项目 | A13 回复 | B13 判定 |
| --- | --- | --- |
| 仓库 URL |  | 接受／建议修改／待定 |
| E4 完整 40 位 SHA |  | 接受／建议修改／待定 |
| README 入口 |  | 接受／建议修改／待定 |
| 环境自检 |  | 接受／建议修改／待定 |
| 镜像构建 |  | 接受／建议修改／待定 |
| 单元测试 |  | 接受／建议修改／待定 |
| 冒烟测试 |  | 接受／建议修改／待定 |
| 密钥扫描 |  | 接受／建议修改／待定 |
| A13 对 B13 的建议 |  | 已处理／需跟进／不适用 |

### B13 对 A13 README 的初步检查

根据 2026-10-10 的公开 README：

- [x] 能找到按学号建立独立目录和设置仓库级 Git 身份的步骤。
- [x] 能找到 `make all` 入口及各证据文件的对应关系。
- [x] 能理解 BuildChecker 冒烟测试的预期结果。
- [x] 能找到固定基础镜像 digest、依赖锁和密钥管理约定。
- [x] 能确认 `.env` 和 `work/` 不应提交。
- [ ] 待 A13 提供其最终运行 SHA 和实际五项运行结论。

A13 README 表示 E4 不强制个人 PR；B13 额外要求三名成员用各自 PR 留痕。这是组内审计方式差异，不影响双方的环境、构建、测试、冒烟和密钥扫描结论互查。

## 禁止交换

- 服务器密码、SSH 私钥或完整服务器分配表
- 个人 `.env`、API Key、GitHub Token
- 含凭据的终端截图或日志
- 未脱敏的 `env.json`、镜像历史或错误输出

## B13 完成互查后的回复模板

```text
A13 同学好，B13 已完成本轮 E4 README 互查。

你们提供的仓库、完整 SHA 和 README 入口：接受／建议修改／待定。
环境：接受／建议修改／待定。
构建：接受／建议修改／待定。
测试：接受／建议修改／待定。
冒烟：接受／建议修改／待定。
密钥扫描：接受／建议修改／待定。

B13 对需要修改的项目会写明文件、章节和原因；没有问题的项目不会要求双方使用相同镜像 ID、耗时或日志行数。互查记录将以脱敏 Markdown 形式进入 B13 成员2的 E4 PR。
```
