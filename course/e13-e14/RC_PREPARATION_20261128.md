# E14 候选发布准备（未发布）

负责人马宇航，2026-11-28。此文件补齐发布流程和已知限制，**不将当前main或预览profile宣布为已验收RC**。

## 固定清单

| 对象 | 已知身份 | 正式候选状态 |
|---|---|---|
| B13已合并基线 | fb4be620da9587ea3dc35581eeb2599ffe98fae7，4条实际main工作流成功 | 后续正式输入/变更合入后重新锁定 |
| A13观察到的集成候选 | 53140c96174a99aa9f7d66538bb8b975121bafdb | 待A13候选交付及组级验收，不代其批准 |
| 历史同步服务 | 7ddbd700ece7bedaa3a1d0c73cb6e8110fec9eb4；镜像cf313aa1a28bbff8e9727d7f5c8217819ec2da3d7cdffc9ab55553a2464b622a | 已验收个人五轮，不改写为新main |
| 全项目输入 | C0 592fc6f3d2463a58fe7f60b8d255ed242740bec0；C1 b2dda5513fe4a7d250493528800fe425cae459a5；preview canonical b051e316… | 待四原件书面签认或受影响新版本 |
| 标签/Release | v0.9-rc未创建 | NOT_RELEASED |

## 正式范围与已知限制

- tomlc99完整范围为六产物、五条缺失依赖；Makefile-only修复后全项目MISSING=0，单改toml.h后直接make all六产物均重建；独立toml_json空stdin、stdout=7b7d0a、stderr空、exit0。
- 原C8只修toml.o，范围外toml_json→toml.h一条MISSING保留，不能替代全项目。
- 预览修复使用`.EXTRA_PREREQS`避免把头文件作为CLI链接输入；当前分析器留下6条`.EXTRA_PREREQS/=`的REDUNDANT解析发现。保留完整findings，最终是否带入RC由课程验收口径判断，不擅自过滤。
- 现有header探针记录真实make输出和六产物mtime增长，未单独记录该探针execve；三组全量strace另存，不互相冒用。
- 国内APT源偶发连接失败可令构建exit100；本轮同SHA重试恢复，固定候选未改。今后先保留失败原件，不通过改候选后沿用旧摘要、放宽验证或复用旧成品伪造成功。
- 非root/Docker socket实际权限按实测登记，不能称整个服务完全无宿主权限影响。临时A13隧道已经撤权，此文不授权新访问。

## 复现准备

1. 在个人干净副本检出最终确认完整SHA，验证源码归档/manifest、profile raw及canonical、候选和配对baseline的摘要；不要在已运行服务的挂载源码目录中git pull。
2. 使用该主机实际已核验的服务镜像不可变ID；记录inspect、工具链和源码。不要用浮动latest或仅同名镜像代替。
3. 检查新项目名、端口及新OUT与他人不冲突。当前已有入口为`labs/e13e14/run_shared_member2.sh IMAGE START_PORT normal PROJECT_ID`。它创建独立Compose项目、保存失败日志、只清理所属项目。
4. 若最终接受现有四原件且保留当前ID，现有全项目路径需显式设置`E14_TOMLC99_FULL_PREVIEW=1`，PROJECT_ID为`b13-tomlc99-full-preview-v1`；签认与正式采用另记，开关不自动变默认开启。若改了ID/字段，先由成员二更新注册并正常审查，不能把未知ID直接填入现有命令。
5. 执行前固定请求/profile/candidate及双方真实源码。成功后收集六次HTTP、四角色日志、DRAFT及实际下游镜像、完整findings/patch/validation、header probe、源文件前后比较和清理记录。失败也留原件。
6. 同步故障与恢复按实际影响范围使用独立配置/新任务；旧跨机五轮继续作为既有固定版本证据，不仅为改文档重跑。

## 回退与发布

部署回退仅针对新建的本次Compose项目：先采日志/inspect和失败原件，再使用该任务生成的确切Compose参数执行down，核查所属ownership label下无残留；不操作共享Docker服务或其他人的容器。需要回到前版时从单独只读检出的旧SHA和原镜像/配置建立新项目，记录新job/trace及健康/业务结果。不得就地覆盖旧原件，不把旧成功目录当回退后的新实跑。

发布前核验：双方最终输入和候选SHA、E13实际矩阵、教师结果、必需CI/Review、四服务和故障恢复、扫描/清理/源码保持、可取阅原件和完整清单。然后只读查询`git ls-remote --tags origin refs/tags/v0.9-rc`；已有标签先核实，禁止强推或移动。全部条件满足后才按仓库正常流程创建标签、Release Notes及最终提交ZIP。

发布说明最终必须填明两个仓库的实际SHA/镜像、项目输入、对应job/trace、证据索引、已知问题及复现/回退路径。未满足前保持NOT_RELEASED。
