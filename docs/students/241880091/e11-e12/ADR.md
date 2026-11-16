# ADR：DRAFT不可变镜像贯通与报告消费边界

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
