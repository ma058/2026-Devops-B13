# B13 E4 三人执行与交付清单

本文是 E4 的实际执行入口。三人均只提交脱敏 Markdown 记录；服务器密码、地址、SSH 信息、`.env`、Token、API Key 和原始 `work/` 不得进入 GitHub。

## 统一基线

- 仓库：<https://github.com/ma058/2026-Devops-B13>
- E4 运行基线完整 SHA：`519ca0fce2a5417e3f855a101bc5c938252a03d5`
- 成员1环境 PR：[#13](https://github.com/ma058/2026-Devops-B13/pull/13)
- 标准命令：`make doctor`、`make all`
- 每人独立目录：`/root/<本人学号>/draft`
- 三人不得并行构建；顺序为成员1、成员2、成员3。

运行基线固定为 `519ca0f…`，因为它是已在服务器完整通过 `make all` 的环境代码提交。运行记录等后续纯文档提交不会改变该基线；成员2和成员3必须检出同一 SHA，才能进行三人可重复性对照。

## 当前状态

| 人员 | 当前状态 | 下一项交付 | Review 负责人 |
| --- | --- | --- | --- |
| 成员1（ma058） | 环境初始化、模板集成、完整运行、负向密钥测试和脱敏记录均已完成 | PR #13 合并；最后复核成员2报告；三人完成后整合并创建最终标签 | 成员3已 Review PR #13 |
| 成员2（Lacrym1ra） | 待执行 | 独立重跑、版本对照、A13 README 互查、个人报告和 PR | 成员1 |
| 成员3（yqy241880115） | 已 Review PR #13，待独立运行 | 独立重跑、安全核验、三人汇总、个人报告和 PR | 成员2 |

每个 PR 至少由一名非作者成员 Review。现采用实际轮转：成员3审成员1、成员1审成员2、成员2审成员3。

## 成员1：ma058

### 已完成

- [x] 核对课程服务器环境并安装 Docker、Compose 与 buildx。
- [x] 修改初始密码并验证 SSH 公钥登录。
- [x] 确认 Docker API 端口 `2375/2376` 未开放。
- [x] 从 E3 固定标签接入 B 组 E4 模板，没有覆盖 E2/E3 内容。
- [x] 固定基础镜像 digest、依赖锁和工具版本记录。
- [x] 修复课程 ECS 到默认 Debian 源连接失败的问题。
- [x] 在个人目录执行完整 `make all`。
- [x] 验证 `4 passed`、DRAFT 预期失败冒烟和三层密钥扫描。
- [x] 完成假 Key 拒绝与清理后复检。
- [x] 提交[成员1脱敏运行记录](RUN_MEMBER1_MA058.md)。
- [x] 获得成员3对 PR #13 的非作者 Approve Review。

### 后续收口职责

- [ ] 合并 PR #13。
- [ ] Review 成员2的运行记录、版本对照和 A13 互查记录。
- [ ] Review 三人汇总中与成员1证据有关的字段。
- [ ] 三份报告合并后，在 `main` 运行仓库级回归检查。
- [ ] 更新 `CONTRIBUTIONS.md` 中成员2、成员3的 E4 PR、提交和报告链接。
- [ ] 创建并推送 `e4-complete-<日期>` 标签，作为 E5 起点。

创建最终标签前必须确认成员2和成员3的报告已合并，不能提前创建。

## 成员2：Lacrym1ra

### A. 在服务器独立运行

成员2在自己的学号目录执行；`<本人学号>` 必须替换，不能使用成员1目录：

```sh
mkdir -p /root/<本人学号>
cd /root/<本人学号>
git clone https://github.com/ma058/2026-Devops-B13.git draft
cd draft
git fetch origin feature/e4-bootstrap-b13
git switch --detach 519ca0fce2a5417e3f855a101bc5c938252a03d5
git config --local user.name '<本人学号>'
git config --local user.email '<本人学号>@localhost'
git rev-parse HEAD
git status --short
make doctor
make all
```

完成后核对：

```sh
RUN_DIR=$(ls -td work/* | head -n 1)
printf '证据目录：%s\n' "$RUN_DIR"
cat "$RUN_DIR/test.log"
cat "$RUN_DIR/smoke.json"
cat "$RUN_DIR/secret-scan.txt"
git ls-files .env
git status --short
```

必须得到：

- [ ] 完整 SHA 为 `519ca0fce2a5417e3f855a101bc5c938252a03d5`。
- [ ] `env.json.problems` 为空。
- [ ] `test.log` 为 `4 passed`。
- [ ] `smoke.json` 中 `build_exit_code` 非 0、`make_error_line` 含 `make: not found`、`passed` 为 `true`。
- [ ] `secret-scan.txt` 显示未发现问题。
- [ ] `.env` 未被 Git 跟踪。

### B. 版本和可重复性对照

- [ ] 将自己的 `toolchain.lock` 与成员1记录对照。
- [ ] 工具版本、测试结论和冒烟结论应一致。
- [ ] 镜像 ID、时间、耗时和日志行数允许不同。
- [ ] 在个人报告中写明差异是否属于允许差异。

### C. 联系 A13

- [ ] 使用 [A13 交流与互查文档](A13_EXCHANGE_CHECKLIST.md) 中的发送稿直接联系 A13。
- [ ] 核对 A13 README 的 BuildChecker 入口和预期结果。
- [ ] 取得 A13 的仓库 URL、完整 SHA 和五项脱敏结论。
- [ ] 不经成员1代传；成员2将原始回复的脱敏摘要写进自己的报告。

### D. GitHub 交付

- 分支：`test/e4-repro-member2`
- 报告：`docs/E4/RUN_MEMBER2_LACRYM1RA.md`
- 报告内容：完整 SHA、成功证据目录名、工具版本、测试/冒烟/扫描结论、与成员1对照、A13 互查结果。
- 禁止提交：`work/`、`.env`、服务器地址、凭据、完整原始环境日志。
- 由成员1 Review 后合并。

## 成员3：yqy241880115

### A. 在服务器独立运行

成员3使用自己的学号目录，重复成员2的克隆、固定 SHA、仓库级 Git 身份、`make doctor` 与 `make all` 流程。不得复制成员1或成员2的 `work/` 作为自己的运行证据。

- [ ] 完整 SHA 为 `519ca0fce2a5417e3f855a101bc5c938252a03d5`。
- [ ] `env.json.problems` 为空。
- [ ] `test.log` 为 `4 passed`。
- [ ] 冒烟测试正确识别预期的 `make: not found`。
- [ ] 最终密钥扫描通过。

### B. 安全核验

- [ ] 按教师手册使用假 Key 做一次拒绝测试。
- [ ] 删除假文件并再次扫描通过。
- [ ] `git status --short` 无假文件残留。
- [ ] 确认 `.env` 权限为 `600` 且没有被 Git 跟踪。
- [ ] 确认 Compose 只挂载 `/var/run/docker.sock`，没有开放 TCP Docker API。
- [ ] 确认容器以普通用户运行并设置 `no-new-privileges`。
- [ ] 在报告中说明 docker.sock 等价于宿主机高权限能力，只限课程服务器受控使用。

### C. 三人结果汇总

建立对照表，至少包含：

| 项目 | 成员1 | 成员2 | 成员3 | 结论 |
| --- | --- | --- | --- | --- |
| 完整源码 SHA |  |  |  | 必须一致 |
| Git/Docker CLI/Python/pytest |  |  |  | 关键版本应一致 |
| 单元测试 |  |  |  | 均为 `4 passed` |
| 冒烟测试 |  |  |  | 均为 `passed: true` |
| 最终密钥扫描 |  |  |  | 均通过 |

### D. GitHub 交付

- 分支：`test/e4-security-member3`
- 个人报告：`docs/E4/RUN_MEMBER3_YQY241880115.md`
- 汇总报告：`docs/E4/THREE_MEMBER_COMPARISON.md`
- 报告内容：个人运行、安全核验、假 Key 测试、三人对照结论。
- 由成员2 Review 后合并。

## 最终完成标准

- [ ] 三人的服务器运行均固定到同一完整 SHA。
- [ ] 三份脱敏运行记录均已合并。
- [ ] A13 互查有完整 SHA、README 入口和五项结论。
- [ ] 每个成员都有自己的 Commit、PR 和 Review 记录。
- [ ] `CONTRIBUTIONS.md` 已登记 E4 贡献。
- [ ] `main` 回归检查通过。
- [ ] `e4-complete-<日期>` 标签已推送。
