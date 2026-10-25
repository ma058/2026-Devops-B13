# 成员2 E5–E7 个人实验报告

## 1. 基本信息与完成范围

- 执行人：成员2，学号 `241880091`，GitHub `Lacrym1ra`。
- 实验日期：2026-10-24；报告更新日期：2026-10-25。
- 个人PR：[PR #18](https://github.com/ma058/2026-Devops-B13/pull/18)。
- 交付分支：`member2/e6-evidence-validation`。
- 本人完成：E6独立复验、双候选对照、证据校验器扩展、19项测试、课程服务器doctor适配及修改后正式回归。

本报告依据本人Linux服务器保存的命令、完整日志、退出码、输入与镜像记录。原始归档已下载并核对SHA-256；本次整理还在本机校验了包内545个文件摘要、正式源码快照及四套保存证据的一致性，没有在本机重新运行Docker构建。

## 2. 源码版本与实验环境

### 2.1 版本追溯

| 版本用途 | 完整SHA或状态 |
| --- | --- |
| 公共基线审查head | `2228b193f023554d5b194dc2f400a67219d9128b` |
| 本人校验器、测试与doctor代码提交 | `9a6231f7a49e5cbc7372fe3283e69a15a7c0aab7` |
| 本轮正式回归及新双候选运行版本 | `4be43e5021545604f0df27bfe0df3b84d061630e` |
| 正式运行前及回归后工作区 | 两份git status记录均为空，工作区干净 |
| 首次13时段E6历史运行SHA | 没有同期已确认记录，保留为无法确认，不用后续SHA回填 |

正式回归使用独立工作树 `/root/241880091/e5-e7-b13-m2-closeout-20261024-225625-148713`，实验入口为 `labs/B-draft`。旧克隆和旧work保留。

正式证据根目录为 `work/m2-closeout-20261024-225625-148713/`，下文简称“本轮证据目录”。`audit/formal-run-sha.txt`、运行前后状态和三份源码快照均已归档；源码快照逐字节匹配上述正式提交。当前报告更新晚于实验运行，实验版本仍取上述SHA。

归档脚本另存的archive-head属于旧克隆归档时的状态，与本轮正式回归版本分开使用。

### 2.2 宿主机与doctor适配

| 项目 | 实际记录 |
| --- | --- |
| 系统 | Ubuntu 22.04.5 LTS，内核5.15.0-191-generic，x86_64 |
| CPU／可见内存 | 2核／3.5 GiB |
| 正式自检可用磁盘 | 68.9 GiB |
| Docker server | 29.1.3 |
| Compose／buildx | 2.40.3+ds1-0ubuntu1~22.04.1／0.30.1 |
| 宿主Git／Make／Python | 2.34.1／4.3／3.10.12 |
| Docker socket组号 | 121 |
| registry_mirrors | 空列表 |
| 正式doctor结果 | problems为空，退出0 |

首次doctor因可见内存3.5 GiB低于教学脚本最低4 GiB而退出1。本人针对课程小样例沿用E4的3.5 GiB最低可见内存适配，建议值仍为8 GiB。正式自检保留CPU低于4核、内存低于8 GiB、可用磁盘低于100 GiB及未配置镜像加速四项warnings，不把阈值适配表述为实际内存达到4 GiB。

正式自检原始记录：`audit/doctor-after.json`、`audit/doctor.log`和`audit/doctor.exit.txt`。

### 2.3 正式服务镜像与容器工具链

服务标签：`b13-draft:241880091-closeout-20261024-225625-148713`。

服务镜像完整ID：

```text
sha256:ebae854ab0662b23d84534098b014c92b7b9afc3e8ff6d9d6975574e55340825
```

服务镜像通过 `lab_cloud.py build` 重建，入口退出0；构建日志保留实际缓存命中。容器内服务pytest为24 passed、退出0。服务镜像ID来自本次docker image inspect，后续gate与工具链采集均使用该ID。

| 容器工具 | 实际版本 |
| --- | --- |
| Git | 1:2.47.3-0+deb13u1 |
| Docker CLI | 28.5.1，build e180ab8 |
| Python | 3.13.14 |
| pytest | 8.4.2 |
| 架构 | amd64 |

宿主机Docker server与服务容器Docker CLI分别记录。证据位于 `service-build/` 和 `audit/service-toolchain.log`。

## 3. 个人代码贡献与先失败后通过验证

| 文件 | 本人交付内容 |
| --- | --- |
| `scripts/verify_e6_b_evidence.py` | 完整输入集合、规范路径、摘要、不可变镜像ID及最终运行禁网检查 |
| `tests/member2/test_e6_evidence_validation.py` | 19项合法和篡改证据测试，独立使用临时目录 |
| `scripts/doctor.py` | 课程小样例的3.5 GiB最低可见内存适配，保留真实测量及建议值 |

输入清单必须是非空映射；键为规范相对POSIX路径，值为合法SHA-256。实际普通文件集合须与清单完全相同，逐文件核对内容，拒绝遗漏、额外输入、路径逃逸、符号链接和非常规文件。

最终命令必须为字符串数组形式的docker run，绑定保存的完整镜像ID，运行选项明确为 `--network none`；拒绝未知选项、重复覆盖、--net别名及镜像后附加参数。已有双轮顺序、缺make日志、候选摘要、镜像绑定、退出码与输出检查保留，合法证据仍通过。

| 验证阶段 | Linux实际记录 | 退出码 |
| --- | --- | --- |
| 修复前 | Ran 19 tests；FAILED (failures=12, errors=7) | 1 |
| 安装修复后 | Ran 19 tests；OK，无跳过 | 0 |
| 本轮正式提交回归 | Ran 19 tests in 0.018s；OK，19通过、0失败、0错误、0跳过 | 0 |

12条失败和7条错误包含子测试统计，不将其相加作为失败测试方法数。旧实现会接受遗漏、额外文件、空清单、bridge或删除禁网参数等篡改；错误结构和路径还会导致AttributeError、IsADirectoryError或FileNotFoundError。

修复前后记录保存在 `work/m2-code-20261024-140731-142857/{before-tests.log,before-tests.exit.txt,after-tests.log,after-tests.exit.txt}`；正式19项结果保存在本轮 `audit/member2-tests.*`。Linux符号链接用例实际执行成功，无Windows权限跳过情况。

测试为合成证据规则测试，不运行Docker；真实Docker实验由后面的独立E6和gate记录支持。代码与测试由助手协作编写，本人负责理解、服务器执行与结果核对。

## 4. 两类候选独立E6与实测对照

### 4.1 来源与本轮运行

候选来自 `fixtures/b13-candidates/`，保留成员1provenance：助手读取实际提示后整理保存，已接触教学候选并进行网络适配；error-driven与适配后的教学候选字节一致。本人贡献是独立执行、比较和证据规则扩展，不署为本人新生成模型回复，不声称独立盲测或论文成功率。

| 项目 | error-driven | context-driven |
| --- | --- | --- |
| 本轮目录 | `e6-error/evidence/` | `e6-context/evidence/` |
| trace_id | `e6-b-d6d3458f747f452281b7d68da3df844c` | `e6-b-602bad8bb9944381bd55b8ea3391914d` |
| 候选SHA-256 | `db8fdf9a1e6377ae916494d5e1608a74d94be8ba1192c27e6db2c1a830d58e4a` | `16391e090c39fa363ff0a8c5562a9904ed5716d70e9568ee3c5d96f8b28c611b` |
| E6采集入口退出码 | 0 | 0 |
| 首轮构建退出码／分类 | 1／MISSING_MAKE | 1／MISSING_MAKE |
| 次轮构建退出码 | 0 | 0 |
| 最终程序退出码／输出 | 0／hello E3 | 0／hello E3 |
| 最终状态 | SUCCEEDED | SUCCEEDED |
| 新校验器检查 | passed=true，退出0 | passed=true，退出0 |
| 镜像Size字节数 | 149200868 | 116554385 |
| workflow_elapsed_ms | 789 | 835 |
| 首轮／次轮CACHED行数 | 2／4 | 2／4 |
| 实际已安装包条目数 | 139 | 124 |

本轮error-driven候选镜像：

```text
sha256:af0a2cf022d77d5a4980dc6ab7b0f880c1f5c01cf2e497a4d901ce7caf22fe73
```

本轮context-driven候选镜像：

```text
sha256:ed9c059346ce7969a7cf079468e9a32b2555162462a5a7040559332fb61f473d
```

两个镜像ID分别与iter-02/image-inspect.json、attempts[1].image_id和verification.command最后参数一致，最终程序均按保存的镜像ID使用--network none运行。

### 4.2 实际包列表与测量口径

包列表通过最终不可变镜像ID、禁网启动dpkg-query采集，采集时间为 `2026-10-24T14:59:03Z`。两次查询均退出0；139和124是完整dpkg-query输出条目数，包含基础镜像已有包，不等于本次新增包数。

| 实际包 | error-driven | context-driven |
| --- | --- | --- |
| build-essential | 12.12 | 未安装 |
| gcc | 4:14.2.0-1 | 4:14.2.0-1 |
| g++ | 4:14.2.0-1 | 未安装 |
| make | 4.4.1-2 | 4.4.1-2 |
| libc6-dev:amd64 | 2.41-12+deb13u4 | 2.41-12+deb13u4 |
| dpkg-dev | 1.22.22 | 未安装 |

完整记录为 `audit/error-packages.log` 和 `audit/context-packages.log`。候选、来源和对照记录为 `audit/candidate-files-sha256.txt`、`audit/candidate-provenance.json`、`audit/candidate-comparison.json`。

error-driven安装build-essential及其依赖，context-driven显式使用gcc、libc6-dev、make；本轮context镜像Size较小，但两者功能结果一致。镜像Size来自inspect，表示该字段的镜像大小，不是压缩传输大小。workflow_elapsed_ms覆盖两轮构建、验证和清理，未单独采集单轮纯构建时间。

执行顺序为error-driven后context-driven，两者均复用已有构建缓存；不能将789与835毫秒的差异解释为模型能力、普遍速度排名或冷构建差异。缓存原始行保留在两轮build日志及对照JSON中。

### 4.3 历史成功记录复查

较早的两套成功记录独立保留：

| 历史记录 | 目录／trace_id | 已核对结果 |
| --- | --- | --- |
| error-driven | `work/m2-e6-error-20261024-131210/`；`e6-b-e44d95b1e9124b7584228d5ff8a26e70` | 入口0、两轮1/0、MISSING_MAKE、输出hello E3，新校验器通过 |
| context-driven | `work/m2-e6-context-20261024-131605/`；`e6-b-42da9e5017364d17ac0e6786e457c56b` | 入口0、两轮1/0、MISSING_MAKE、输出hello E3，新校验器通过 |

本轮 `audit/verify-historical-*.log` 只检查保存证据一致性；`e6-error/`、`e6-context/`是正式SHA下新执行的Docker流程。历史与本轮trace、镜像ID、时间分别记录。

## 5. 修改后正式回归与E7清理证据

| 检查入口 | 本人Linux服务器实际结果 |
| --- | --- |
| 成员2证据规则测试 | 19通过，0跳过，退出0 |
| 服务镜像pytest | 24通过，退出0 |
| 根目录unittest | 33通过，退出0 |
| 历史两套及本轮两套E6证据复查 | 四套均passed=true，退出0 |
| E7完整gate | 六行全部passed=true，整体退出0 |
| 源码、Git历史及服务镜像扫描 | 671个跟踪文件，未发现问题，退出0 |

成员2测试、服务测试及根回归分别统计，不相加为一个测试入口。15组audit命令的实际退出码及tee日志保存退出码均为0。回归后工作区仍干净。

### 5.1 六项gate

| 场景 | 实际状态 | 流程退出码 | gate判定 |
| --- | --- | --- | --- |
| unit-tests | 24 passed | 0 | PASS |
| success | SUCCEEDED | 0 | PASS |
| wrong-output | FAILED | 1 | PASS |
| invalid-candidate | FAILED，构建前拒绝 | 1 | PASS |
| build-failed | FAILED，第二轮构建失败 | 1 | PASS |
| runtime-timeout | TIMED_OUT，第二轮构建成功后运行超时 | 1 | PASS |

保存目录为 `e7-gate/gate/`；gate-result.json与results.csv一致。故障场景流程退出1属于预期，不等于gate失败。

### 5.2 运行超时与容器清理

runtime-timeout的第二轮 `build_exit_code=0`，终态TIMED_OUT，运行容器ID为：

```text
36554474fae28fe193d4c82d9e1fbfd40309fb3d65f5ca71b8993b04effd25f7
```

gate实际执行docker container inspect检查，stderr为No such container，确认该运行容器已移除。保留的证据包括：

- `e7-gate/gate/runtime-timeout/evidence/result.json`
- `e7-gate/gate/runtime-timeout/evidence/verify-container-id.txt`
- `e7-gate/gate/runtime-timeout/evidence/cleanup-check/command.json`及stderr.log
- `audit/gate-cleanup-summary.json`

运行超时通过发生在候选构建成功之后，不用构建超时替代。源码和镜像扫描日志位于 `audit/secret-scan.log`；镜像扫描范围为镜像history及环境配置，不声称扫描了镜像内所有文件。

## 6. 核心字段说明

| 字段 | 产生位置与作用 |
| --- | --- |
| failure_class | classify_failure根据首轮实际日志区分MISSING_MAKE、INFRASTRUCTURE和其他构建错误 |
| candidate_sha256 | auto_build初始化报告时对读取候选文本的编码字节计算SHA-256 |
| input_sha256 | 复制并过滤fixture形成project后，记录每个相对文件路径与内容摘要 |
| image_id | 次轮构建后通过docker image inspect取得，并用于最终程序运行 |
| verification | 保存最终运行命令、退出码、预期／实际输出及匹配结果 |
| status | RUNNING开始，终态为SUCCEEDED、FAILED或TIMED_OUT，并写入result.json |

外层服务容器联网用于构建访问；最终程序的禁网要求对应verification.command。保存证据校验器检查一致性，不独立重跑构建。

## 7. 原始归档与证据索引

原始包：`b13-member2-e567-20261024-231428-389131852-151827.tar.gz`。

SHA-256：

```text
e021c6ea7ffc8e948d7ea7b3d274a6596e100ef8f1416c418e3f2fd378bee55b
```

归档已通过压缩完整性、内部文件集合与摘要检查，正式文件SHA-256校验通过；下载后本机复算与服务器一致。内部file-manifest.json记录545个文件条目，清单自身不计入这545项。归档将旧work和本轮复制目录一起保存，含输入、两轮构建、镜像inspect、输出、测试、gate、扫描及源码快照。原始包保存在本人本地document目录，未提交Git，供审查时通过受控渠道提供。

| 证据 | 包内位置 |
| --- | --- |
| 正式回归、服务重建、gate、新双候选 | `work/m2-closeout-20261024-225625-148713/` |
| 正式SHA、状态、源码快照、命令／日志／退出码 | 上述目录的`audit/` |
| 历史error-driven | `work/m2-e6-error-20261024-131210/` |
| 历史context-driven | `work/m2-e6-context-20261024-131605/` |
| 修复前后红绿测试 | `work/m2-code-20261024-140731-142857/` |
| 归档文件清单与逐文件摘要 | `work/m2-archive-meta-20261024-231428-389131852-151827/file-manifest.json` |

## 8. 审查、CI与交付状态

| 项目 | 截至2026-10-25报告更新时的状态 |
| --- | --- |
| 本人审查公共基线#16 | [正式APPROVED](https://github.com/ma058/2026-Devops-B13/pull/16#pullrequestreview-5638672646)，对应2228b193…；#16仍未合并 |
| 成员3对#18代码审查 | [COMMENTED审查](https://github.com/ma058/2026-Devops-B13/pull/18#pullrequestreview-5638363989)，对应4be43e5…；校验器、19项测试和doctor适配通过，最终Approve尚待补齐材料后复核 |
| 本人服务器及归档待补项 | 本报告已补齐Linux19项、doctor、服务重建、工具链、完整gate与清理、双候选数值、扫描及归档哈希 |
| PR #18 | 继续为Draft，base为member1/e5-e7-bootstrap，依赖#16；当前更新仅补报告 |
| 根CI接入 | 成员3的PR #17含tests/member2目录存在时执行的入口，尚未合并；入口存在不等于已实际执行 |
| main的19项CI实跑 | 待#18和根CI工作进入main后核对实际日志，不能以其他CI绿色或skipped代替 |

成员2已完成本人的实现与正式服务器验证，公共基线合并、个人PR最终Approve及main CI实跑验收继续按协作顺序推进。本报告不把成员3的Comment记成Approve，也不把个人实验完成等同于全组E5–E7最终验收完成。
