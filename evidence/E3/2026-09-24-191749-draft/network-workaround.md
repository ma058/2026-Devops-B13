# 本次构建网络说明

宿主 Docker Desktop 的原有代理不可连接，直接 apt 下载失败；经官方源直连重试仍遇到超时。
最终本次运行向 Docker build 传入 HTTP_PROXY=http://host.docker.internal:18764。
附件 network-helper.py 只代理 archive.ubuntu.com/security.ubuntu.com 的 /ubuntu/ 请求，
通过宿主机直接 HTTPS 获取清华 Ubuntu 镜像站对应路径，再转交容器中的 apt。
apt 仍执行原有仓库签名与包完整性校验，未在 Dockerfile 中禁用验证。
该过程没有更改全局 Docker 或系统代理配置；任务结束后停止临时服务。

复现本次下载通道（仅在需要且该端口可用时）：
1. 在宿主机运行 python network-helper.py，保持该进程运行。
2. 在仓库根目录运行 python scripts/verify_draft.py --build-arg HTTP_PROXY=http://host.docker.internal:18764。
3. 构建结束后停止 helper。正常网络环境直接执行 verify_draft.py 即可。

这是本次环境修复附件，不是 A13 的容器启动参数或正式部署依赖。
