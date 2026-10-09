# B13 E4 成员1脱敏运行记录

本记录只包含复现实验所需的脱敏信息。服务器地址、登录凭据、SSH 信息、`.env` 内容和任何真实密钥均未记录。

## 基本信息

- 执行人：成员1
- GitHub 身份：`ma058`
- 学号目录：`/root/241880054/draft`
- 执行日期：2026-10-09
- 源码完整 SHA：`519ca0fce2a5417e3f855a101bc5c938252a03d5`
- 成功证据目录：`work/20261009-224916/`
- 对应分支：`feature/e4-bootstrap-b13`
- 对应 PR：[#13](https://github.com/ma058/2026-Devops-B13/pull/13)

## 环境自检

- [x] `make doctor` 通过
- [x] `env.json` 的 `problems` 为空
- [x] 仓库级 Git 身份为本人学号
- [x] 服务器架构为 `x86_64`，Docker、Compose、buildx、Git、Make 与 Python 均可用
- 资源警告：服务器的 CPU、内存和磁盘低于手册建议值，且 Docker 未配置镜像加速；这些项目在 `warnings` 中记录，未影响本次验收。

## 构建结果

- [x] `make build` 通过
- [x] 两个基础镜像均按 Dockerfile 中的固定 digest 解析
- 镜像：`e4-draft:241880054`
- 镜像 ID 短标识：`96418e1d5ebf`
- 架构：`amd64`
- `toolchain.lock` 关键版本：Git `2.47.3`、Docker CLI `28.5.1`、Python `3.13.14`、pytest `8.4.2`
- 构建异常与处理：第一次构建因课程 ECS 到默认 Debian 软件源的连接失败而中止；随后将 Debian 镜像源改为可覆盖的构建参数，并保留仓库签名验证。提交 `519ca0f` 在同一服务器重新构建成功。

## 测试与冒烟

- [x] `test.log` 显示 `4 passed`
- [x] `smoke.json.docker_server` 为 `29.1.3`
- [x] `smoke.json.build_exit_code` 为非零值 `1`
- [x] `smoke.json.make_error_line` 含 `make: not found`
- [x] `smoke.json.passed` 为 `true`

冒烟测试中的内层 Dockerfile 构建失败是预期样例；`passed: true` 表示 DRAFT 正确识别并记录该失败。

## 密钥检查

- [x] 完整 `make all` 的 `secret-scan.txt` 通过
- [x] 扫描覆盖工作区、Git 历史和镜像
- [x] `git ls-files .env` 没有输出
- [x] 假 Key 第一次扫描被拒绝，退出码为 `2`
- [x] 删除假文件后第二次扫描通过，退出码为 `0`
- [x] 工作区没有残留 `leak-demo.txt`
- 负向扫描证据目录：`work/20261009-230014/`；清理后复检目录：`work/20261009-230016/`

## Git 状态

- [x] 正式运行固定在完整 SHA `519ca0fce2a5417e3f855a101bc5c938252a03d5`
- [x] `.env` 与 `work/` 仅显示为 Git 忽略文件
- [x] 负向验证结束后 `git status --short` 无输出
- [x] 原始 `work/` 保留在个人服务器克隆中，不提交到公开仓库

## 结论

- [x] 成员1本次独立运行满足 E4 验收标准
- [x] 报告未包含凭据、真实密钥或服务器连接信息
- [x] 本记录可供成员2 Review，并作为三人结果对照的成员1基线
