# ADR：DRAFT不可变镜像贯通与报告消费边界

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
