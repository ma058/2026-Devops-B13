# ADR：DRAFT不可变镜像贯通与报告消费边界

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

### 本次决策补充

保留两组同名测试文件，用明确的suite导入优先级修复测试驱动，不通过重命名成员3测试、删测试或接受跳过绕过问题。生产镜像执行实现不因这次导入问题而回退。

---

## 2026-11-11历史正文（原样保留）

编号：B13-M2-E11E12-001；日期：2026-11-11；作者：241880091（成员2）。

状态：教学样例范围内已实现并实测；实现提交`6b42abed45d8c2215de9b4a8ba3ad6445797c21a`。真实项目通用配置和A13实际镜像/报告交接尚未完成。

## 问题与依据

公共起点`c12a7342de6fd45d963c30d9cc60492545fee30a`可以构建DRAFT候选镜像，但pipeline的full、scan、validate及独立consumer仍在编排器环境运行。红阶段原件`image-before-fix-faXDTi/results`证明：同一候选镜像能读取专属标记并构建输出1，旧full/validate却缺标记。只填写draft_image_reused=true无法满足环境复用要求。

修复还必须保持mixed声明、旧回归、报告版本/类型/hash/job/trace拒绝和原始数据不变，并处理编排器使用宿主Docker socket时的路径差异。

## 候选方案与决定

|方案|评估|
|---|---|
|继续使用编排器工具，只传image ID字符串|不能证明候选环境实际执行，拒绝采用|
|直接把编排器/course路径传给宿主bind mount|Docker daemon解释的是宿主路径；没有明确映射时可能挂错目录，当前不采用|
|显式宿主路径映射并bind mount|可行，但增加跨环境配置和校验责任；留作有实际项目需要时评估|
|以不可变ID创建容器，docker cp传递输入与证据|采用；避开宿主路径猜测，每次操作独立，实际Image可检查|

`image_runtime.py`只接受`sha256:`加64位小写十六进制ID，先inspect确认本地镜像，再以该ID创建容器。容器无网络，以调用者非root UID/GID运行，设置CPU/内存/PID约束和SYS_PTRACE能力；不将Docker socket交给下游工作容器。编排器自身仍使用socket构建镜像和管理容器，属于课程环境既有信任边界。

通过docker cp -a复制项目、版本固定的lab/fullcheck和worker代码，记录代码SHA256；worker核对代码hash、工具版本并执行真实full/scan/validate。结果、stdout/stderr、退出码、前后inspect和execution.json均保留。清理仅针对本次创建的容器ID，不批量删除镜像或其他服务。

## 两个入口与版本语义

- pipeline的E11-B/E12在DRAFT成功后，使用成功尝试的不可变image ID运行下游。E12实际序列为full/scan/scan/full/validate/full，前两项针对base，其余针对target；E11-B继续消费target对应的固定MD。E11-A没有DRAFT阶段，保留原有编排器路径，不宣称其复用了不存在的候选镜像。
- consume_report新增`--image-id`，保留原始envelope/payload双hash、schema、kind、target、job/trace和artifact引用检查，随后在同一传入镜像中validate/recheck。缺镜像ID、tag、镜像不存在、缺工具或执行失败均明确拒绝，不隐式回退。
- 独立消费者接收的image ID来自调用方确认的交接；当前没有实现A13远端身份认证、镜像签名或跨机传输。双方还需提供实际报告与镜像取得方式，不能仅依据tag或字段字符串宣称已交接。

|接口/证据|约定|
|---|---|
|阶段封装|schema_version=e11e12-1；kind、commit、job_id、trace_id、status及artifact的uri/hash/bytes|
|增量payload|沿用e8e10-1；E12 repair引用本轮incremental-check文件，核对原始文件hash|
|执行环境|draft_image_id、image_operations中的image_id/actual_container_image/container_id、project_commit、退出码、工具版本、code_sha256|
|标记探针|仅验收时显式提供受限/opt/m2-draft-marker路径及对应token；容器观察与编排器缺标记对照保留|
|数据迁移|在独立目录添加git/strace，不改原C0/C1与fixed-md字节；迁移回执不是通用项目配置schema|

## 写回、失败与可追溯性

patch先在编排器生成精确候选，不修改原始数据仓库。validate在候选镜像的独立sandbox执行；仅接受全部验证通过且回传Makefile产生的diff与candidate.patch完全一致的内容。写回前检查工作副本没有并发变化；最终full失败时恢复工作副本原Makefile。报告拒绝保持原始字节，不通过改commit或重算hash将旧报告伪装成当前报告。

正式执行与各次重试使用独立OUT。HTTP服务将本轮独立jobs目录挂到/course/work/api-jobs，避免启动恢复逻辑改写旧任务；只绑定本人127.0.0.1:8082。停止服务不按端口批量杀进程，原失败和退出码保留。

候选缺git/strace时明确失败；当前教学候选模板与独立迁移目录增加工具安装，原候选hash保留。镜像中工具版本可能变化，故记录实际版本；现有报告不构成对任意编译器、任意GNU Make或恶意项目的保证。

## 验证与影响

完整证据索引见[个人报告](个人报告.md)。49项E11–E12、46项E8–E10无跳过；8组真实镜像正负例通过；正式E11-B/E12及本人HTTP通过。HTTP下载512产物三方hash一致，实际容器Image与DRAFT ID一致。原E7流程未修改，其新head远端CI另待核验。

保留原E8–E10 lab.py；新增7项mixed/拒绝测试在改造前已通过，个人贡献是独立验证。prepare和member1_cases只为新候选添加git/strace；verify_handoff显式传image ID。独立consumer调用者需更新参数；缺参拒绝是有意的接口变化。

代价是每次操作新建容器、复制项目与保存原始证据，时间/空间开销增加；本轮未做性能基准。实际维护项目的多目录、目标映射、构建命令、运行输出、故障触发与恢复策略仍需版本化配置和新测试，当前硬编码的课程profile不能冒称已支持这些需求。

## 后续条件

取得真实项目来源/许可、C0/C1和独立预期后扩展配置；取得A13原始报告及实际镜像后完成传输/加载校验与独立消费；对最终提交核验CI和实质Review。继续保持Draft及待办状态，不因教学样例通过自动合并或宣布整个E11–E12完成。


## 本人真实 tomlc99 适配与验收补充

决策：新增显式版本化的受限 tomlc99 release profile，教学逻辑继续使用原入口默认分支。只有已审计 Makefile 的 toml.o 依赖行允许加项，其余字节和配方必须不变；不引入通用 Makefile 重写器。两入口、worker 和报告绑定同一 canonical hash，拒绝未知字段、外部 flags 覆盖及错误版本。缓存键包含编译器身份/版本、有序有效 flags、profile、对象映射、源码与 Makefile 字节。代价：其他项目或 Makefile 布局须单独审计并版本化；当前真实项目全量残留仍明确开放。

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
