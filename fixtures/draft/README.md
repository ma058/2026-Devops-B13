# DRAFT 人工测试基线

此处验证人工参考 Dockerfile，不执行 DRAFT 的 LLM 迭代算法。
在仓库根目录执行 `python scripts/verify_draft.py`；Linux 也可执行
`sh fixtures/draft/verify.sh`。需要可用的 Docker Linux engine 和镜像/软件源网络。

验证 broken 构建因缺少 make 失败、reference 构建成功、两次独立容器均输出
`hello E3`、clean build 与程序运行成功。网络/镜像拉取失败不算预期失败。
证据自动存入 evidence/E3/，含 Dockerfile diff、镜像 ID、环境和完整输出。
基础镜像 tag 与软件源可能变化，因此证据记录实际基础镜像 digest 和软件版本；
本基线保证功能验证可重复，不承诺跨日期镜像或二进制字节完全一致。

源码在容器 `/workspace/project`，clean build 为 `make clean && make`，
功能验证为 `./hello`。镜像只包含本目录的 main.c 和 Makefile。
Git/Python 用于同一 Linux 环境下验证全组证据接入；它们不是 hello 的编译依赖。
本镜像尚未经过 A13 跟踪权限与 BuildChecker 兼容性确认。
