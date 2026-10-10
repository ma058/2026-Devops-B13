# B13 E4 成员3脱敏运行记录

本记录只包含复现实验所需的脱敏信息。服务器地址、登录凭据、SSH 信息、`.env` 内容和任何真实密钥均未记录。

## 基本信息

- 执行人：成员3
- GitHub 身份：`yqy241880115`
- 学号目录：`/root/241880115/draft`
- 执行日期：2026-10-10
- 源码完整 SHA：`519ca0fce2a5417e3f855a101bc5c938252a03d5`（与成员1基线一致）
- 成功证据目录：`work/20261010-140139/`
- 对应分支：`test/e4-security-member3`
- 对应 PR：[#14](https://github.com/ma058/2026-Devops-B13/pull/14)（Review 负责人：成员2，按 TEAM_TASKS 轮转）

## 环境自检

- [x] `make doctor` 通过
- [x] `env.json` 的 `problems` 为空
- [x] 仓库级 Git 身份为本人学号（`user.name=241880115`，`user.email=241880115@localhost`，未设置 `--global`）
- 资源警告：有——内存 `3.5 GiB` 低于手册建议值 `8 GiB`；Docker 未配置镜像加速（`registry_mirrors` 为空）。与成员1记录一致，均在 `warnings` 中，未影响验收。

## 构建结果

- [x] `make build` 通过
- 基础镜像 digest 核验：一致——`build.log` 中两个 resolve 行均按 Dockerfile 固定 digest 解析（python `sha256:f82c9645…`、docker-cli `sha256:9190b061…`）
- 镜像：`e4-draft:241880115`（镜像名带学号，与组内其他成员互不覆盖）
- 镜像 ID 短标识：`0d9a9a21023b`（amd64）
- `toolchain.lock` 关键版本：Git `2.47.3`、Docker CLI `28.5.1`、Python `3.13.14`、pytest `8.4.2`
- 构建异常与处理：构建本身无异常。获取源码时，ECS 直连 GitHub 的大数据量克隆出现 HTTP/2 断流；改用成员1提供的 `e4-pr13-519ca0f.bundle` 在服务器完成同一提交的检出（`git clone -b feature/e4-bootstrap-b13`，HEAD 即 `519ca0f`），随后经 `git fetch` 与远程分支核对一致，不影响运行基线。

## 测试与冒烟

- [x] `test.log` 显示 `4 passed`
- [x] `smoke.json.docker_server` 为 `29.1.3`（宿主机引擎版本，经挂载的 docker.sock 取得）
- [x] `smoke.json.build_exit_code` 为非零值 `1`
- [x] `smoke.json.make_error_line` 为 `#8 0.115 /bin/sh: 1: make: not found`
- [x] `smoke.json.passed` 为 `true`

说明：冒烟中 `Dockerfile.broken` 的内层构建失败是预期样例；`passed: true` 表示 DRAFT 以默认 `app` 用户正确执行构建、取得完整失败日志并识别关键错误行。

## 密钥检查

- [x] 完整 `make all` 的 `secret-scan.txt` 通过（文件 597 个，含 Git 历史，含镜像 `e4-draft:241880115`）
- [x] `git ls-files .env` 没有输出；`.env` 权限为 `600` 且未被 Git 跟踪
- [x] 假 Key 第一次扫描被拒绝：`FOUND leak-demo.txt:1 …`（命中"LLM/API Key"与"密钥赋值"两种模式共 2 处，输出仅显示前 4 位），`make scan` 非零退出；负例证据目录 `work/20261010-140726/`
- [x] 删除假文件后第二次扫描通过：`密钥检查：未发现问题`（文件 597 个），复检目录 `work/20261010-140759/`
- [x] 工作区没有残留 `leak-demo.txt`；负例结束后 `git status --short` 无输出；假文件未提交、未推送

负例测试说明：按教师 B 组手册第 6 节由成员3本人在服务器手动执行（假 Key 仅使用手册给定示例值，未复制进任何仓库文件或提交历史）。

## docker.sock 安全核验（成员3专职）

- [x] `/var/run/docker.sock` 权限为 `srw-rw---- root:docker`（组号 121，与 `env.json` 的 `docker_sock_gid=121` 一致），仅 root 与 docker 组可访问
- [x] 宿主机监听端口仅 SSH 等必要项，**未开放 Docker API 端口 2375/2376**
- [x] `compose.yaml` 仅挂载 `/var/run/docker.sock`；容器内 `app` 用户所需组号由 Makefile 运行时注入 `DOCKER_GID`（`group_add`），未写死；`security_opt: no-new-privileges:true` 生效；`cpus/mem_limit/pids_limit` 限制生效于服务容器本身
- [x] 服务镜像以非 root 用户 `app`（uid 10001）运行（Dockerfile `USER app`）；冒烟以默认 `app` 用户经 sock 成功调用宿主机引擎（`docker_server: 29.1.3` 即运行时证据）
- [x] 镜像按学号隔离：本机存在 `e4-draft:241880115` 与 `e4-draft:241880054` 两个镜像，互不覆盖

风险声明：能访问 `docker.sock` 等价于宿主机高权限能力（可启动特权容器、挂载宿主机任意目录、删除任意镜像与容器）；容器上的资源限制管不到它发起的宿主机构建。本挂载仅限课程专用服务器受控使用：只构建课程指定项目、构建设置超时（Makefile `TIMEOUT=600`）、不开放 Docker API 端口。与论文中 DRAFT 直接运行在 Ubuntu 主机的方式不同，此差异按分工要求写入 E5 差异记录。

## 与其他成员对照

- 对照成员：成员1（ma058）
- 源码 SHA：一致（`519ca0f…`）
- 工具版本：一致（Git `2.47.3`、Docker CLI `28.5.1`、Python `3.13.14`、pytest `8.4.2`）
- 单元测试结论：一致（`4 passed`）
- 冒烟结论：一致（`docker_server 29.1.3`、`build_exit_code 1`、`make_error_line` 含 `make: not found`、`passed: true`）
- 密钥扫描结论：一致（正式扫描通过；假 Key 均被拦截且清理后复检通过）
- 允许差异：镜像 ID（成员1 `96418e1d5ebf` / 成员3 `0d9a9a21023b`）、证据目录时间戳、构建耗时（成员3 复用组内构建缓存，`make all` 约 75 秒）
- 成员2：截至 2026-10-10 尚未完成独立运行；三人对照详见 [THREE_MEMBER_COMPARISON.md](THREE_MEMBER_COMPARISON.md)，待其完成后补齐
- 非预期差异及处理：无

## 最终结论

- [x] 本次运行满足 E4 验收标准
- [x] 报告未包含任何凭据或真实密钥
- [x] 原始 `work/` 仍保持 Git 忽略，未提交到公开仓库
