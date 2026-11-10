# E11–E12 增量导入与复现说明

日期：2026-11-10。负责人：马宇航（241880054，B13）。公共 PR：[#26](https://github.com/ma058/2026-Devops-B13/pull/26)。

## 来源与边界

- 来源：本次发放的 `DevOps_E11_E12.zip` 中 `03_实验包`，对照课堂安排、操作手册、模板及两份 PPT。
- 原始 ZIP SHA-256：`019e693625b6d97923a8e8769fef87765913a306725e3da22029eda955348b3f`。
- 接入前 main：`a52062432ef3b1638eb1cbdf6f9cf73a98eb0c5d`。本次保留已合并的 E8–E10 修复和三人测试，增量导入 E11–E12 编排与环境，不用实验包中的旧文件覆盖它们。
- 导入 `run_e11e12.py`、`labs/e11e12/` 和独立 CI；不导入教师已有的 `data/`、`work/` 作为本人运行结果。
- 新样例的 C0/C1 是本轮生成项目内的真实 Git 提交，仍是课程控制样例，不是课程另行要求的实际维护项目。

## 本组新增内容

1. 环境镜像来源可配置并保留摘要；CI 使用官方源。国内服务器使用显式镜像变体，基线与候选的 FROM 来源配对，候选仍固定同一基础镜像摘要。该变体仅为构建源适配，不修改预期构建失败或补丁判定。
2. 宿主 root 调度时实验容器使用 UID/GID 10001；源码挂载只读，`data/`、`work/` 独立可写。Docker socket 仍授予容器调用宿主 Docker 的能力，不将这些设置描述为完整宿主隔离。
3. 成员一新增 28 项测试：`test_member1_e11e12.py` 5 项，`test_member1_handoff.py` 14 项。另有 `test_member1_api_client.py` 9 项客户端边界测试；与教师契约 10 项合计 38 项。
4. `course/e11-e12/member1_cases.py` 生成 macro 历史样例，执行 E11-B、真实旧 C0 报告拒绝、E12，验证宏定义修复位置、RD 保留、原始源码/报告不变及所有产物哈希。
5. `labs/e11e12/consume_report.py` 独立消费收到的增量报告原始字节，在生成补丁之前核对版本、类型、job/trace、两个文件的 SHA-256 和清单。不通过重新检测偷偷替换外部输入。
6. `course/e11-e12/api_probe.py` 走真实 HTTP 提交/轮询/下载，验证幂等、409 冲突及下载正文、清单与 `X-Content-SHA256` 三方一致。
7. CI 上传包含合法隐藏快照文件（例如 `.gitignore`），同时排除 `.git`、`.env`、私钥扩展名；验收必须下载 artifact 后再次复算，不能仅检查 Runner 上的文件。

## Linux 复现入口

在本人仓库配置本人数字学号 Git 身份，按材料构建个人环境镜像后执行：

```sh
python3 run_e11e12.py test
python3 run_e11e12.py prepare
python3 run_e11e12.py run --request data/integration-sample/e11-b.json --out work/my-e11-b
python3 run_e11e12.py run --request data/integration-sample/e12.json --out work/my-e12
```

输出目录及生成数据目录必须是新路径，不覆盖首次失败。macro 驱动和独立报告消费命令需要在同一课程 Linux 环境容器内运行，完整挂载方式见 `.github/workflows/e11e12.yml`，个人运行应使用个人镜像标签、身份和输出目录。CI 身份 `999999999` 不代表任何成员的服务器运行。

## 尚需协作的验收

教学编排器当前在自身工具链中进行检测与修复验证；成员二负责将它们真正放入 DRAFT 生成的镜像执行并补充配置。消费入口用 `execution_environment=orchestrator`、`draft_image_reused=false` 如实标记现状。成员三负责实际维护项目来源、完整 C0/C1 与 A13 分机联调。成员一本地回放收到报告的路径及自测 HTTP 成功均不能替代 A13 实际交付与参与。

## 国内服务器的已验证镜像源变体

成员一在该服务器上遇到官方源访问失败及 apt 下载超时，成功路线是同摘要镜像前缀配合 TUNA 软件源。成员二/三使用本人已有普通 Linux 账号时，可直接采用以下等价的显式来源配置，保留自己的构建日志和版本，不必重复成员一已经定位的网络失败：

```bash
sid=$(git config --local user.name)
image="course-e11e12:$sid"
docker build \
  --build-arg DOCKER_CLI_IMAGE=m.daocloud.io/docker.io/library/docker:28.5.1-cli@sha256:9190b0613792e658a7783cf14b2d5ace5941bb68ede7276922ea36ee457d76ad \
  -f labs/e11e12/environment/services/buildchecker/Dockerfile \
  -t "$image" labs/e11e12/environment
python3 run_e11e12.py test
mkdir -p data work
docker run --rm --network none --cap-add SYS_PTRACE \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e PYTHONPATH=/course/labs/e11e12:/course/labs/e8e10:/course/labs/e11e12/vendor:/app \
  -v "$PWD:/course:ro" -v "$PWD/data:/course/data:rw" -v "$PWD/work:/course/work:rw" \
  -w /course "$image" python3 labs/e11e12/prepare.py \
  --name integration-sample-cloud --registry-prefix m.daocloud.io/docker.io/library/
python3 run_e11e12.py run --request data/integration-sample-cloud/e11-b.json --out work/my-e11-b-cloud
python3 run_e11e12.py run --request data/integration-sample-cloud/e12.json --out work/my-e12-cloud
```

先确认本人 `user.name` 是数字学号、目录和 Docker 权限可用；此段普通账号命令不适用于把 root 直接当作实验用户。生成目录已存在时选择新 `--name`，后续请求路径同步修改。不要修改他人的目录权限，不运行全局 Docker prune。该路线保持课程生成数据标签，未解决另行要求的实际维护项目来源。
