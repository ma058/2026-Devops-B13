# B13 真实运行的接口样例

来源：成员一于 2026-11-10 从 Windows 经 SSH 隧道访问 B13 API 的任务。**这是 B13 控制样例自测，不是 A13 的交付，也不是实际维护项目。** 文件按收到的原始字节保存。

- 运行代码：`9cf6d26e0abba6477bd41e3fd9c54aaf19c54961`。
- job_id：`job-79988ea4e46546e4aed1a3a9a34e1dd7`。
- trace_id：`trace-4cf3ba8de7dd4c3482e72930ceac5aca`。
- C0：`0fa879f26fe8cab8c9466495fc5d2fb5afdf6a8e`。
- C1：`85c341465f2d6ec985de0bc8ef0575471fac83fd`。

|文件|用途|SHA-256|
|---|---|---|
|`E12-input.json`|裸 input；路径是已部署服务容器内路径，可供 API 客户端读取|`75bdd5f8d18135538fd95bc551cf6455d3d8d48e58852c447ccdc986510b17ee`|
|`incremental-check.json`|增量阶段信封原件|`1d743ce5125f0e77618ecfa4fa387b2c102984458b915e6183c49e2afb213c68`|
|`incremental-report.json`|对应增量 payload 原件|`ed843d893c0e9326330007ce562deaa9810a930b28ea603aa14d5e3da1927da4`|

如果 A13 先行访问 B13 托管 API，可在建立本人授权 SSH 隧道后，用 `api_probe.py --request docs/E11-E12/samples/E12-input.json` 并指定自己的新 key、新输出目录。不要将 `/course/` 路径当作 A13 本地路径；换托管方或换数据后必须更新请求并重新计算 hash。

独立报告消费需源码仓库含上述目标提交。生成样例的 Git bundle 在成员一原始 tar 的 `work/member1-records/integration-sample-cloud.bundle`，由组长提供给 Review 者；接收方在自己的实验目录 clone bundle。不能用外层学生源码仓库 HEAD 代替样例 C1。

A13 正式交付时请提供其独立运行原件、真实 job/trace、项目/代码版本及哈希；不能仅修改此样例中的组名或 commit 来冒充新的交付。
