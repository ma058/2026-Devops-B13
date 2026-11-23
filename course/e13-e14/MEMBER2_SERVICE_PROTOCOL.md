# 成员2四角色委托协议（待组内冻结）

显式 E14_PROTOCOL=member2-e14-1；默认仍调用原 teaching_service.py，保留模板CI/成员3入口，新协议错误不会回退旧模式。成员3 compose.yaml/orchestrate.py 未修改。

四角色同步 POST /v1/run，私有 X-E14-Token（至少32字符）。GET /health返回role/protocol。仅DRAFT提供 POST /v1/worker、挂socket；其余经HTTP委托。不是异步 /v1/jobs，不代替C8。

公共字段：protocol、project_id、job_id、trace_id、base/target完整SHA、profile对象/profile_sha256、candidate_sha256、project绝对路径和out新目录。仅本次RUN_ROOT/jobs/<job>/base或target，拒绝复用OUT/源码内输出/符号链接。member2_run.py生成并原样保存每次JSON。

1. DRAFT增加candidate/build_timeout；成功返回不可变image_id，私有状态冻结job/trace/profile/commits/candidate/image及两版源哈希。
2. BuildChecker增加image_id/timeout_seconds，委托full；基线对base、后续对target。
3. EChecker增加base_project、baseline_graph及其sha256、target_findings及其sha256；委托两次scan并核对full，返回report/payload路径和原字节SHA。完整full不删范围外发现。
4. MDFixer增加report/report_sha256、payload/payload_sha256；核验原件引用/schema/job/trace/commit/profile，生成受限补丁。DRAFT再次校验并委托validate，accepted且清理确认、全部源未变、精确补丁一致后才写回Makefile。

worker只允许full/scan/validate，不接受任意shell。uid为本人非root，network none、资源限额；docker cp避免socket宿主bind路径歧义。检查Python/Git/GCC/Make/strace，缺工具显式失败。保存实际image inspect、源/代码SHA、工具版本、退出码/stdout/stderr及清理时间。

普通部署四角色均设置 `E14_ENABLE_FAULTS=0`。C4 专用部署仅在 DRAFT 启用 `E14_ENABLE_FAULTS=1` 和 `E14_FAULT_SCENARIO=C4`，验证带本次 operation label 的 worker 超时、停止、删除，然后另起普通 job 核对恢复。C5 专用部署仅在 MDFixer 与 DRAFT 开启 C5，注入固定的不可应用补丁，保存 apply-check stderr、拒绝结果、源码和 Git 状态及正确补丁对照。

profile算法/字段见B13_PROJECT_MANIFEST与projects目录；信封沿用e11e12-1并绑定profile。外部A13仍需成员1三层result/信封/payload契约；内部生成报告不能冒充A13。

个人端口28081–28084，仅127.0.0.1；8081/8082不动。源码只读、个人work可写；token/env排除导出。共享work属于同一可信团队部署，不是互不信任租户隔离。

## 共享编排接入提案

协议版本为 `member2-e14-1`。供成员三确认的固定 DRAFT 请求示例在同目录 `member2-draft-request.example.json`。示例中的业务字段来自项目清单，路径、job 和 trace 用于说明格式。实际客户端每次创建全新目录和身份，逐次保存发送的 JSON 与对应响应。认证仅经私有 HTTP 头传入。

Linux 共享入口为 `bash labs/e13e14/run_shared_member2.sh IMAGE START_PORT normal`。脚本将成员三现有 `compose.yaml` 作为基础文件，叠加成员二协议的环境配置并调用 `member2_run.py`。四个角色的健康检查须匹配对应 role/protocol。成功退出前，脚本同时核对四角色同步请求、三次 full、两次 scan、一次 validate、DRAFT 镜像 ID、清理记录、工具版本、修复请求所用原件摘要与最终完整 findings。`smoke` 仅执行四角色健康检查。`C4`、`C5` 为独立专用部署；C4 后另起 `normal` 并记录新 job。

普通链路每个 POST 产生一条带 role、endpoint、stage、status、http_status、elapsed_ms、error_code、job_id、trace_id 的结构化日志。成功时 error_code 为 null。实际调用的请求/响应和服务日志分别位于本次运行的 `jobs/<job>/http/`、`diagnostics/`。证据导出指向本次配置，保留原始失败，并排除鉴权文件。

本入口只运行登记的 `b13-level-v1`。B13 与 A13、成员三确认 tomlc99 正式范围后再接入第二个项目。现有 toml.o profile canonical SHA-256 为 `0f2bc52c0e791b97a833c1c4a22c70d6cd72a97befc3959c578ccf5c85d40ee1`。全量检测保留范围外的 `MISSING(toml_json, toml.h)`；扩展规则须采用新版本和新摘要，并以补丁、编译、运行、头变更重建及最终完整检测验证。
