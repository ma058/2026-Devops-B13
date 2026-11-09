# 成员1评审修复与证据索引（2026-11-08）

对应成员2对 [PR #22](https://github.com/ma058/2026-Devops-B13/pull/22) 的COMMENT。公共导入#21已合并，本PR已改base为main；最终Approve仍由成员2完成，不以COMMENT代替批准。

## 已修复与实际验证

修复代码SHA：`f1ecf9c08793779f4d1328a0633a30d108f07915`。

1. CI上传显式保留合法隐藏文件，同时排除.git目录、.env及凭据扩展名。已实际下载新artifact，核对**16份清单、114项文件、16个.gitignore全部存在且哈希匹配**，并确认无.git/.env/.pem/.key。旧产物114项仅98个文件的缺陷已修复，未修改旧证据掩盖问题。
2. `run_member1.sh`将`/course`挂载只读、本次OUT单独挂载可写；root及普通用户分支使用同一挂载策略。修正个人报告对11月3日旧运行的权限说明。
3. 11月8日在服务器实际执行修复SHA，`work/member1-20261108T080435Z`：13项测试全部通过、无skip；E8/E9/E10完整驱动通过；E10三行门禁通过、最终真实BuildChecker无MD并留10份trace。

## 可直接访问的CI

|代码SHA|类别|Run|结论/产物|
|---|---|---|---|
|f1ecf9c|E8–E10 PR|[42461361113](https://github.com/ma058/2026-Devops-B13/actions/runs/42461361113)|success；artifact ID `13610360221`，`e8e10-evidence-42461361113`；下载后114项全匹配|
|f1ecf9c|E7 PR|[42461361105](https://github.com/ma058/2026-Devops-B13/actions/runs/42461361105)|success|
|f1ecf9c|E8–E10 push|[42461357554](https://github.com/ma058/2026-Devops-B13/actions/runs/42461357554)|success|
|f1ecf9c|E7 push|[42461357547](https://github.com/ma058/2026-Devops-B13/actions/runs/42461357547)|success|

本文件之后的文档提交应在GitHub继续核对其最新检查；以上记录绑定修复代码SHA，不能冒充未来提交的结果。原始下载artifact与核验结果 `artifact-audit-42461361113.json` 已随11月8日材料包提供。

## 服务器归档的实际取阅位置

共享目录：`/srv/b13/e8-e10-evidence/`，目录755、归档644，已存在的个人Linux账号可通过SFTP/SCP读取；无需使用成员1/root认证。也可直接从本轮交给组长的本地材料包取得同名文件。

|文件|SHA-256|
|---|---|
|member1-e8-e10-evidence-20261103.tar.gz|`6564b011b75b3d068c9f1b58c64e3a956f03ac5ea611ac25e1f2a773bc49463f`|
|member1-e8-e10-evidence-20261108.tar.gz|`c62e3fc8c38e6932e351cc4ad2a3d159c864a75e55ec5b2fc9dc1e708053afda`|

例如使用本人已配置的服务器账号：

```bash
scp 本人Linux账号@47.110.38.55:/srv/b13/e8-e10-evidence/member1-e8-e10-evidence-20261108.tar.gz .
```

11月3日与11月8日归档分别绑定原执行SHA和修复SHA，不能混称同一次运行。已保留构建/环境、精确命令、退出码、快照、补丁、计划及动态重检。本人已于2026-11-09确认姓名/校区为马宇航／苏州校区，个人报告同步登记。
