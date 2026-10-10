# B13 E4 可重复工程环境：流程、分工与任务清单

## 1. 适用范围与材料结论

- 小组：B13，当前按课程调整后的 3 人名单执行。
- 服务：DRAFT。A 组手册只用于和 A13 互查，不作为 B13 的执行手册。
- E3 起点：Git 标签 `e3-complete-2026-09-29`，对应合并提交 `f0a93bf34518d7cab9a464854e71cca4852f1452`。
- E4 目标：让三名成员在同一服务器的独立学号目录中，从同一提交执行 `make all`，得到一致的测试与冒烟结论，并证明仓库、历史、镜像和日志没有密钥泄漏。
- 私有信息：服务器 IP、账号、当前密码、SSH 指纹、个人 `.env` 和 API Key 只在教师指定的私密渠道使用，不写入 GitHub、Issue、PR、日志、截图或 AI 使用记录。

服务器分配表仍包含 B13 的旧四人名单。本计划以课程调整后的三人名单为准，不给已退出本组的人员分配任务。

## 2. 与官方流程的差异

E4 手册只要求至少两名成员独立重跑，也不强制个人提交。B13 为保持三人工作量相近并保留 GitHub 贡献记录，采用以下补充规则：

1. 三名成员都在自己的学号目录独立克隆并执行一次完整 `make all`。
2. `work/` 仍保持忽略，不把含环境细节的完整个人目录直接提交。
3. 每名成员提交一份脱敏运行记录或核验报告，并通过独立分支和 PR 留痕。
4. 每个 PR 由另一名成员复核，原作者不批准自己的 PR。

这些规则只增加协作与审计记录，不改变 E4 的实验结论。

## 3. 三人分工

| 成员 | 主要职责 | GitHub 分支建议 | 必须交付 | Review |
| --- | --- | --- | --- | --- |
| 成员1（ma058） | 服务器与仓库初始化、B 模板安全导入、第一次完整运行、最终整合 | `feature/e4-bootstrap-b13` | E4 模板提交、README 入口、成员1脱敏运行记录、最终标签 | 成员3复核 |
| 成员2（Lacrym1ra） | 第二次独立重跑、依赖与构建可重复性核验、直接联系 A13 完成 README 互查 | `test/e4-repro-member2` | 成员2脱敏运行记录、版本/测试对照、A13 互查记录 | 成员1复核 |
| 成员3（yqy241880115） | 第三次独立重跑、密钥负例测试、docker.sock 安全核验、三份结果汇总 | `test/e4-security-member3` | 成员3脱敏运行记录、安全核验、三人对照结论 | 成员2复核 |

共同要求：三人都要使用自己的学号目录、只设置仓库级 Git 身份、记录完整 40 位源码 SHA，并确认 `.env` 未被 Git 跟踪。每个人的逐项命令与交付物见 [三人执行与交付清单](TEAM_TASKS.md)，跨组发送稿与回复表见 [A13 交流与互查文档](A13_EXCHANGE_CHECKLIST.md)。

## 4. 全部任务流程

### 阶段 0：开始前确认

- [ ] 三人确认当前小组成员与各自学号。
- [ ] 成员1从教师私发材料中核对 B13 的服务器信息，不在公开消息中转发密码。
- [ ] 首次登录后按教师要求轮换初始密码，并只通过安全渠道让当前三名成员获得新登录方式。
- [ ] 三人确认本机 `ssh -V` 可用。
- [ ] 确认 B13 远程仓库为 `https://github.com/ma058/2026-Devops-B13.git`。
- [ ] 确认远程 `main` 包含 E3 标签 `e3-complete-2026-09-29`。
- [ ] 确认所有人理解：禁止开放 Docker API 2375/2376，禁止删除其他成员的镜像、容器和缓存。

### 阶段 1：服务器环境检查，仅成员1执行一次

登录服务器后检查：

```sh
cat /etc/os-release | grep PRETTY_NAME
uname -m
docker --version
docker version
docker compose version
docker buildx version
git --version
make --version | head -n 1
```

验收：

- [ ] Ubuntu 版本符合课程环境要求。
- [ ] 架构为模板支持的 `x86_64` / `linux/amd64`。
- [ ] Docker 客户端和服务端都可用。
- [ ] Compose 与 buildx 可用。
- [ ] 若 Docker 缺失，只由有管理员权限的成员按实验包脚本初始化一次。

### 阶段 2：将 B 组模板接入现有仓库，仅成员1执行

B13 仓库已经包含 E2/E3 内容，因此不能直接运行手册中面向空仓库的整目录覆盖命令。成员1在本地从教师提供的 `E4实验包/B-draft` 比较并选择性合入，服务器随后只克隆合并后的远程仓库。

建议顺序：

1. 从 `e3-complete-2026-09-29` 或最新 `main` 创建 `feature/e4-bootstrap-b13`。
2. 把 B 模板展开到单独临时目录，先比较目录与文件差异。
3. 合入 `services/draft/`、`compose.yaml`、`Makefile`、依赖锁文件和 E4 脚本。
4. 对 `.gitignore`、`.dockerignore`、`README.md` 做合并，不直接覆盖已有 E2/E3 说明。
5. 将官方 E4 版 `fixtures/draft/` 作为当前冒烟样例，同时保留 `expected.json` 与 `verify.sh` 供既有 E3 复验入口使用。
6. 调整 `scripts/verify_draft.py` 的工作目录、固定基础镜像和工具清单，使旧验证入口兼容 E4 样例。
7. 确认没有 `.env`、`work/`、真实密钥、缓存或本机构建产物进入暂存区。
8. 提交并创建 PR，由成员2复核后合并。

提交前检查：

```sh
git status --short
git diff --cached --check
git ls-files .env
git diff --cached --name-only
```

- [ ] `git ls-files .env` 没有输出。
- [ ] 暂存文件中没有 `work/`、密码、Token 或 API Key。
- [ ] README 已包含 E4 的 `make doctor`、`make all`、证据位置和预期结果。
- [ ] 模板 PR 合并后，三人记录同一个完整提交 SHA。
- [ ] 服务器上的个人克隆来自远程仓库，不直接从 `/root/E4实验包/B-draft` 开展正式运行。

### 阶段 3：三人分别建立独立克隆

三人按顺序执行，`<学号>` 必须替换为本人学号：

```sh
mkdir -p /root/<学号>
cd /root/<学号>
git clone https://github.com/ma058/2026-Devops-B13.git draft
cd draft
git config --local user.name '<学号>'
git config --local user.email '<学号>@localhost'
git rev-parse HEAD
git status --short
make doctor
```

- [ ] 三人使用不同学号目录。
- [ ] 没有人设置 `git config --global`。
- [ ] `make doctor` 显示环境自检通过。
- [ ] `env.json` 中 `problems` 为空。
- [ ] 低于建议资源只记为 `warnings`，不把警告误写成失败。

### 阶段 4：三人分别完整运行

共享服务器上不要并行构建。成员1完成后成员2执行，成员2完成后成员3执行：

```sh
git pull --ff-only
git status --short
make all
```

`make all` 应依次运行 `doctor → build → test → smoke → scan`。

每人记录：

```sh
RUN_DIR=$(ls -td work/* | head -n 1)
printf '证据目录：%s\n' "$RUN_DIR"
ls -lh "$RUN_DIR"
cat "$RUN_DIR/test.log"
cat "$RUN_DIR/smoke.json"
cat "$RUN_DIR/secret-scan.txt"
git rev-parse HEAD
git ls-files .env
git status --short
```

每人的验收标准：

- [ ] `env.json`：`problems` 为空，Git 身份是本人学号。
- [ ] `build.log`：镜像构建成功，包含固定 digest 的解析记录。
- [ ] `image.json`：记录本次镜像 ID 和元信息。
- [ ] `toolchain.lock`：记录 Docker CLI 等实际工具版本。
- [ ] `test.log`：B 组当前模板为 `4 passed`。
- [ ] `smoke.json`：`docker_server` 有版本值。
- [ ] `smoke.json`：`build_exit_code` 非 0。
- [ ] `smoke.json`：`make_error_line` 含 `make: not found`。
- [ ] `smoke.json`：`passed` 为 `true`。这里表示正确识别预期构建失败。
- [ ] `secret-scan.txt`：显示“密钥检查：未发现问题”。
- [ ] `git ls-files .env` 没有输出。
- [ ] 记录完整 40 位 `git rev-parse HEAD` 与成功的 `work/<时间>/`。

### 阶段 5：三人分别验证密钥扫描负例

只使用 B 组命令手册第 6 节给出的假 Key，不使用真实 Key。不要把该示例值复制进仓库文档或提交历史：

```sh
# 先按教师手册在自己的服务器克隆中创建 leak-demo.txt
git add leak-demo.txt
make scan
git rm --cached -q leak-demo.txt
rm leak-demo.txt
make scan
git status --short
```

- [ ] 第一次扫描识别假 Key 并返回失败。
- [ ] 删除假文件后第二次扫描通过。
- [ ] `leak-demo.txt` 未提交、未推送。
- [ ] 没有把这两个扫描目录误当成完整 `make all` 的证据目录。
- [ ] 成员3核对仓库、Git 历史和镜像历史均没有真实密钥。

### 阶段 6：三份运行结果对照

成员3汇总，成员2复核：

- [ ] 三人的源码 SHA 完全相同。
- [ ] 三人的 `toolchain.lock` 关键版本一致。
- [ ] 三人的 `test.log` 都是 `4 passed`。
- [ ] 三人的 `smoke.json` 都正确识别 `make: not found`，且 `passed: true`。
- [ ] 三人的最终密钥扫描都通过。
- [ ] 镜像 ID、运行时间、日志行数如有不同，明确记录为允许差异。
- [ ] 任何非预期差异都有原因、复现步骤和处理结果。

### 阶段 7：与 A13 相互检查

成员2直接联系 A13，不需要由成员1代传。执行要求见 [A13 互查清单](A13_EXCHANGE_CHECKLIST.md)。双方只交换：

- 仓库 URL
- 用于 E4 的完整提交 SHA
- README 复现入口
- 脱敏后的成功或失败结论

禁止交换服务器密码、私有 `.env`、API Key、Token 或完整 IP 分配表。

### 阶段 8：GitHub 留痕与最终收口

- [ ] 成员1提交模板与本人的脱敏运行记录，成员3 Review。
- [ ] 成员2提交独立重跑、依赖对照和 A13 互查记录，成员1 Review。
- [ ] 成员3提交安全核验和三人对照报告，成员2 Review。
- [ ] 三个 PR 的作者不同，提交作者与实际执行人一致。
- [ ] 更新 `CONTRIBUTIONS.md`，登记三个 PR、代表性提交和报告路径。
- [ ] `main` 上重新检查 README 命令、Schema/旧测试和 E4 文档没有被破坏。
- [ ] 创建 `e4-complete-<日期>` 标签，作为 E5 起点。

## 5. E4 最终交付清单

仓库内容：

- [ ] `services/draft/` 服务骨架与 Dockerfile
- [ ] `fixtures/draft/` 冒烟测试样例
- [ ] `compose.yaml`
- [ ] `Makefile`
- [ ] `requirements-dev.in`
- [ ] `requirements-dev.lock`
- [ ] `.env.example`
- [ ] `.gitignore` 与 `.dockerignore`
- [ ] `scripts/doctor.py`
- [ ] `scripts/secret_scan.py`
- [ ] README 中的一键复现说明

运行记录：

- [ ] 三名成员各自的脱敏运行记录
- [ ] 三份完整源码 SHA 与成功证据目录名称
- [ ] 三人版本、测试、冒烟和密钥扫描对照
- [ ] A13 README 互查记录
- [ ] GitHub Issue、Commit、PR、Review 与贡献登记

提交给课程平台时，以教师最新要求为准。若平台只能上传一个文件，使用 `e4-complete-<日期>` 标签生成仓库 ZIP；若允许填写链接，同时提交 GitHub 仓库 URL、标签或完整提交 SHA。

## 6. 进入 E5 前的固定边界

- E4 的 `smoke.json` 只证明执行链路正常，不是 E5 的完整论文复现证据。
- E5 要在同一环境重新执行 `docker build --progress=plain`，保存完整标准输出、标准错误和退出码。
- B 组将 docker.sock 挂入容器属于课程容器化要求，与论文中直接在 Ubuntu 主机运行 DRAFT 的做法不同。成员2和成员3应把这一点写入 E5 差异记录。
