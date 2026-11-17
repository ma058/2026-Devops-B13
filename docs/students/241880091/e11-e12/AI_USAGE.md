# AI_USAGE：E11–E12 AI辅助使用记录

## 2026-11-17 最新回包核对与当前结论

本节更新此前历史待办。本人 tomlc99 适配、版本化 profile、新 DRAFT、E11-B/E12 与本人8082验证继续沿用既有真实证据；PR #37 已建立，未自动合并。本轮只做原件审计和文档变更，不冒充新的服务器执行。

**教学跨机回签已完成。** A13 241830088 回包1614项外层文件清单及嵌套清单通过；522次HTTP交换、512个下载文件、同键幂等/409、6次镜像操作和12份inspect相符。job `job-a3c1043460ec4948ae659e5cf9fb5d62` / trace `trace-3fa471caa6314d80b0feb21a93bebf56`；五项checks全true，MD=0、RD=1，首次MISSING_MAKE失败保留。[成员2技术回签](https://github.com/Dufunare/2026-Devops-A13/pull/16#issuecomment-6935852744)仅确认收到的客户端和下载服务端原件，不代替成员一审批或独立SSH身份核验。此结论属于教学E12，不是tomlc99 HTTP。

**A13 real06已接收并完成离线复核，运行验收仍有缺口。** 新镜像`sha256:6907c50a74cfd623200abb7b6694f6bb64f086fec6230ff013e81d648b065cad`的外层SHA、14个OCI内容块/描述符及8层diffID一致，镜像内5份源码和构建上下文154文件与C1一致。real06的1192项工件引用、job/trace、候选SHA及scoped/full结果相符；仅toml.o清零，全量保留toml_json→toml.h。

不能关闭的实际差异：绑定记录dirty_count=4；所列27c7提交与PR17当前4f71提交均没有imgrunner.py，已发布pipeline/lab仍直接执行；缺下游容器命令/inspect/退出等原件；实际编译带-O2 -DNDEBUG而缓存键未包含；说明承诺的另外两份请求及旧运行目录未随包提供。[已向A13反馈并抄送成员一](https://github.com/Dufunare/2026-Devops-A13/pull/17#issuecomment-6935853721)，要求补执行源码/原始日志并修复真实flags绑定，不篡改旧run。

B13对A13原始envelope/payload双SHA、schema、C1、job/trace及引用检查通过，但版本化profile检查实际拒绝`PROFILE_HASH_MISMATCH`。保留原字节，没有手补profile hash或绕过保护；需双方明确跨组profile映射/新版本报告后再独立消费。A13新6907镜像和B13新2a9765镜像并列登记，不能相互替代签收。

本机Docker Linux引擎未运行，启动被执行策略拒绝；新镜像仅静态复核，未执行docker load/run。准备了独立、非root、只清理本人容器的接收探针，但未标记执行通过。

**剩余闭环：** A13补齐real06源码与容器证据、有效flags/cache绑定、缺失请求和profile契约；双方新镜像的实际接收/独立消费；成员三对最终head的Review、成员一tomlc99批准部署、A13本人tomlc99跨机HTTP及最终归档。旧教学工作和已通过本人实验无需重做。详细机器可读结果见[A13回包索引](A13_RECEIPTS_20261117.json)。

> **2026-11-17 发布核对：** 本文旧教学章节保留为历史快照；当前状态以文末“本人真实 tomlc99 适配与验收补充”和[本次证据索引](REAL_PROJECT_EVIDENCE_20261117.json)为准。本人真实项目、工具齐备的新DRAFT及8082 loopback已验收；此前“真实项目未接入”等描述只适用于旧阶段。A13接收本次新镜像/报告并完成新版跨机HTTP仍为待办。
> 服务器实测代码为 `c8ed0dcc92017e6ec8ecf4b2bb228c5b94cc6f2d`，服务器文档提交为 `0bb9c60888b15652edd0bfe6b51b66edfad535f0`。本地普通同步 main `6a98a4f0ad6d37f342ff4cefc08af923b797dee1` 后，运行代码、测试与profile相对实测版本没有变化；新增提交只包含文档及证据索引，不冒充另一次服务器实验。

## 2026-11-16续接：main同步、测试发现修复与复测

本节为后续状态；下方2026-11-11正文保留为历史快照，其中“待安装/未提交/待公共合并”等只描述当时状态。

- 原个人实现：`6b42abed45d8c2215de9b4a8ba3ad6445797c21a`；原文档提交：`e90ac670cd572ae5ba82492d98f1c61c298f9f09`。
- 合入公共main：`1d7f4839eff567aa7037d431df86952f24076c4d`；无冲突普通merge提交：`ad78f2cf5a864a844fd83b86e2eb7067fdef1ab7`。
- 本轮修复后实际执行源码：`dccc8fb0b6f78245b65a96eed1556bdae3dc6534`。本文更新将在其后单独提交，不能把未来文档HEAD写作实测版本。
- 本人PR26 [Approve](https://github.com/ma058/2026-Devops-B13/pull/26#pullrequestreview-5855731362)已完成，公共PR26/29已合并；个人Draft以main为base。
- 本轮证据目录：`work/m2-e11e12-20261111-134430-krozl6/delivery-20261116-w34xJr/retest`。源码/测试hash、summary、实际Docker inspect由更新脚本现场核对；本轮原始目录尚待归档下载，不冒称Windows已复核新包。

在ad78f2cf上，E11–E12先通过61项；随后E8–E10发现同名test_member3模块时错误导入e11e12目录，退出1。原日志`work/m2-e11e12-20261111-134430-krozl6/logs/main-retest-e8e10-zo60Nf.log`及退出码保留；该块当时因set -e停止，镜像复测没有执行。

修复回归驱动：将当前suite目录放到sys.path首位、另一suite作为后续依赖路径，并显式设置发现顶层目录。两个同名test_member3.py都保留；新增两个独立子进程的重名模块回归测试。

修复后真实结果：E11–E12 **63项PASS**、E8–E10 **46项PASS**，均无跳过/失败/错误；真实镜像8组PASS。数量从summary读取，不用预估值代替实测。

|本轮镜像用例|job|实际DRAFT image ID|
|---|---|---|
|e12|`job-b13738ae97bd4a9eac4dcbd5d9f68be1`|`sha256:c2e79b20c4f8019b6ca2cf98f8eaa57502cc246ff90b002edc298f3285a187d0`|
|e11-b|`job-85b11dcb2d7b467284db6c7a53dae71e`|`sha256:c5a156263b51909f48030a3a1ea75c36588a55d65dd46fe50c562b28ddec297d`|
|consumer|`job-b13738ae97bd4a9eac4dcbd5d9f68be1`|`sha256:c2e79b20c4f8019b6ca2cf98f8eaa57502cc246ff90b002edc298f3285a187d0`|

两入口正例实际容器Image匹配不可变ID，消费者收到的envelope/payload与本地E12原件字节一致；负例及原红阶段保留。该8组属于课程控制样例，不能算A13实际交接或真实维护项目验收。

本次新增证据不包含新的独立正式请求复测或8082实测；11月11日正式/HTTP512文件结果继续绑定旧执行SHA，不改写为本轮新head结果。测试中的HTTP边界用例也不等同8082完整联调。

版本化真实项目配置、真实项目输入/执行、本人A13三包及镜像贯通、必要的新head正式/HTTP实测和最终远端CI/成员3Review仍为待办。此文档阶段可交付Draft，不能宣布全部完成。

### 本次AI辅助补充

AI定位并修复自己此前生成的回归驱动路径顺序问题，准备两个重名模块回归用例和文档更新脚本；本地受控复现/修复检查与本人服务器实测分开记录。服务器修复、提交和复测由本人执行。脚本核验实际summary/source/inspect后更新三文档，未凭“前四步完成”推定全部通过；没有代发布或代合并PR。

---

## 2026-11-11历史正文（原样保留）

学号/小组：241880091 / B13成员2；日期：2026-11-11。实现版本：`6b42abed45d8c2215de9b4a8ba3ad6445797c21a`。

## 使用方式与责任划分

使用Codex对话助手协助理解任务、生成代码/命令/文档并复核文件。未另存精确模型版本日志，因此不补写模型版本、调用次数、token消耗或未记录的提示词全文。

AI在本地Windows工作目录读取交接材料、固定源码和下载证据，生成补丁、安装器、探针、回归/迁移/提交/HTTP/归档命令及三份文档。本人使用既有Linux账号m2_241880091，在Xshell执行服务器操作，通过Xftp传输文件并回传结果；Git作者/提交者为241880091。AI没有代登录服务器执行实验，也没有代发布GitHub Review、push或合并PR。

## 参与范围

|任务|AI提供|实际验证与边界|
|---|---|---|
|聊天交接与步骤整理|承接E11–E12范围、生成完整可复制命令、身份与路径检查|保留旧E8–E10与历史聊天，不把迁移扩展为外部写操作授权|
|基线与首批测试|核验脚本、7项mixed/拒绝集成用例、证据保留驱动|本人执行；7项原先就通过，未包装成失败后修复|
|定位环境缺口|专属镜像标记红阶段探针及正对照|真实Docker构建/运行；候选有标记、编排器无标记，两入口失败；不使用mock冒充复用|
|镜像贯通实现|image_runtime/image_worker、pipeline/consumer适配与工具依赖调整|本人安装并运行49/46回归及8组真实正负例；参数与实际接口一致|
|请求迁移与实现提交|新目录候选迁移、hash检查、精确12文件本地提交脚本|原数据/失败证据保留，提交源码与绿色工作区文件字节核对一致|
|正式与HTTP|固定实现SHA、新OUT、独立8082任务目录、客户端及真实Image检查|本人执行；HTTP实际下载512文件，不拿成员1/3或CI日志替代|
|资料核对|只读提取PR #29/#27的当前固定head文档与字段|教学样例、E2合成契约与真实维护项目严格区分；未联系他人或发送消息|
|文档交付|基于下载原件生成个人报告、ADR、本记录及安全安装器|本人仍需审阅文档、安装并提交；未完成项明确保留|

主要约束包括：直接提供文件修改与完整命令，不要求nano手工改；保留失败日志和退出码；独立OUT/session恢复；不重复prepare覆盖数据；不使用root代跑、不force push/reset --hard、不覆盖其他成员、不自动合并。

## AI建议的核验与修正

1. 首批7项测试全部通过后，承认mixed现有能力已满足用例；另用真实标记实验定位尚未满足的镜像复用需求。
2. 红阶段必须同时具备候选镜像正对照、两个入口缺标记和源字节不变，才记EXPECTED_RED；环境/网络/工具错误不自动计为有效红阶段。
3. 独立消费者最初没有image-id参数，先实现接口再提供调用；没有虚构旧接口参数或仅修改draft_image_reused标志。
4. 本地Windows验证有19项通过，成员1原28项中25项通过、3项因符号链接权限跳过；这些记录没有写成服务器全量通过。后续服务器49/46项无跳过才记录对应PASS。
5. 正式归档显示HTTP服务停止退出137，修正文档口径，保留原值；客户端、镜像检查、停止命令退出0分别记录，不沿用先前说明中“可能143”作为实测值。
6. 请求迁移脚本最初未上传造成No such file；补传后核验hash并成功执行，没有重建账号、重跑prepare或覆盖原数据。

## 证据依据与AI能力边界

本地已对收到的归档逐项检查SHA256，并复核正式阶段报告、被消费报告hash、容器inspect和HTTP服务端/客户端下载原件。归档SHA256为：

```text
063bd61361cd917275bfcb2925aef05146d72bff820891f7ab0445903de5b335
```

`source.tar`与已交付实现/测试包匹配。核验依据为真实文件，未凭聊天里的PASS推算job/trace、512文件数或image ID。三份文档中的执行SHA是6b42abed实现提交；此前回归在提交前工作区运行，随后证明源码字节一致；不宣称其在后来文档提交上重跑。

DRAFT原结果的candidate_source为保存候选回放，且明确本次命令没有模型/API调用。AI参与编写适配代码和准备候选修改，不等于DRAFT运行时在线调用了AI。

AI生成代码仍可能存在缺陷；本次实测覆盖课程两源文件显式Make profile及列出的拒绝场景，不证明支持所有项目或攻击输入。未以mock替代真实镜像验收，也不将单元测试中的受控API调度替身称为真实Docker任务。

## 保留的待办

真实项目来源、版本化通用配置、A13原始报告及镜像交接暂缓；本人未做服务重启恢复试验。当前没有该个人提交的远端CI、Draft PR和最终head实质Review交付证据。后续如补充这些工作，应以新原件更新文档并追加提交，不回写旧归档或伪造已完成状态。

原归档不含后来生成的三份文档和Docker镜像二进制；文档通过单独安装包交付，镜像跨机传递仍待实际需要及授权。报告/ADR的最终审核和提交责任由本人承担。


## 本人真实 tomlc99 适配与验收补充

AI 协助分析收到的材料、实现 profile/执行驱动/测试、编写可复制命令。本地 Windows 契约测试和服务器实际容器实验分别记账；Windows 符号链接用例曾跳过，未当成正式门禁通过。本节由脚本读取本人实际 summary、校验当前源码与报告工件后生成；收到的成员一、成员三、A13 日志不计成本人执行。仍须人工核对范围、执行 SHA、镜像 ID、原始证据与本次最终提交；未授权自动合并。

本次执行代码 SHA：`c8ed0dcc92017e6ec8ecf4b2bb228c5b94cc6f2d`。profile canonical SHA256：`0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1`。

E11–E12 回归 74 项、E8–E10 回归 46 项，均无跳过/失败/错误。本人真实 E11-B、E12、独立消费及 8 类拒绝检查通过。E11-B 固定报告由本人依据已核验 C1 建立，明确不冒充 A13 原始 incremental 报告；独立消费保留本次 E12 两份原始报告字节及其 SHA256。

E12 DRAFT：`sha256:2a9765dff295ddb466b9679122c289937c70e65ab90bd011f8805af23bebc651`；HTTP DRAFT：`sha256:42ff007e5dd1b8c7e63ed2d9ac79b730119fa698a0fe078ecce76794b3594841`。full/scan/validate/recheck 的真实容器镜像、工具版本、worker代码哈希和退出码见原始 execution.json。新镜像包含 git/strace，不是原 A13 de2ea79e 镜像；没有静默回退编排器。

本人 loopback 8082 job：`job-4771c494abce47bc84392034397bcbf3`，完成 POST、轮询、原始工件下载/哈希核对、同键幂等及 409 冲突。此结果不是 A13 客户端正式跨机联调，也不代表共享 8081 已部署本次代码。

**验收范围仅 toml.o。** 保留全量 findings 中的 `MISSING(toml_json,toml.h)`；不能写成全项目零缺失。头文件注释变更通过真实编译器 exec/argv 与对象更新时间证明重编译，不要求对象哈希改变。

证据路径：formal `/home/m2_241880091/241880091/2026-Devops-B13-e11-e12-tomlc99/work/member2-profile-install-OXkxen/formal-attempt-H7jhIV/results`；HTTP `/home/m2_241880091/241880091/2026-Devops-B13-e11-e12-tomlc99/work/member2-profile-install-OXkxen/http-attempt-ASe6ie/results`；回归 `/home/m2_241880091/241880091/2026-Devops-B13-e11-e12-tomlc99/work/member2-profile-install-OXkxen/regressions-9dMRGt`。


## 历史快照：2026-11-17 回包前的跨组交付进展

已发布[真实项目交接预发布包](https://github.com/ma058/2026-Devops-B13/releases/tag/member2-tomlc99-handoff-20261117-d47ac126)，含新DRAFT镜像、小型白名单交接ZIP及SHA256SUMS。小包保留原始incremental envelope/payload字节，提供profile、源码恢复材料、公开代码bundle、接收独立消费和正式HTTP客户端脚本。已直接通知A13 241870063并抄送成员一，见[A13交付登记](https://github.com/Dufunare/2026-Devops-A13/pull/17#issuecomment-6922793749)；已向成员三登记轮转审阅与独立验证，见[B13协作记录](https://github.com/ma058/2026-Devops-B13/pull/37#issuecomment-6922794985)。

本次交付代码固定d47ac126f58046406c86c35fc3eecb100e3cc535；本人实测代码与镜像证据仍沿用前节，不因发送材料而生成新的运行结论。客户端输入校验5项及恢复C1的154文件复算通过；这些是交付脚本本地检查，不是A13本人实跑。

**该历史快照当时仅“发布、直接交付通知、抄送”完成；最新结论以前述回包核对为准。** A13签收/实际load与独立消费原件、成员三最终Review、成员一按正常流程批准的tomlc99部署回执、A13本人正式跨机HTTP及服务端关联原件仍待收到。新任务单称教学API已上线，但不能由此认定tomlc99已部署。部署模板明确PENDING，客户端会拒绝缺少批准及源码绑定的记录。最终三文档与归档只能在收到这些真实原件后收口。范围仍限toml.o，保留toml_json相关全量finding。

字段与状态见[跨组交付索引](CROSS_GROUP_HANDOFF_20261117.json)。

本轮AI辅助：读取并独立复算A13原件、审核公开固定源码、真实调用B13只读传输/profile校验、发出技术回签和补证请求。审计器开发中修正了嵌套清单范围、OCI index/config与压缩层diffID识别、Dockerfile仅复制5文件的假设；未改收到的字节，也未把这些本地审计器修正当成服务器实验失败或通过。未代跑A13身份、未自动合并、未绕过profile拒绝。
