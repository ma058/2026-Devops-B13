# 成员2四角色委托协议（待组内冻结）

显式 E14_PROTOCOL=member2-e14-1；默认仍调用原 teaching_service.py，保留模板CI/成员3入口，新协议错误不会回退旧模式。成员3 compose.yaml/orchestrate.py 未修改。

四角色同步 POST /v1/run，私有 X-E14-Token（至少32字符）。GET /health返回role/protocol。仅DRAFT提供 POST /v1/worker、挂socket；其余经HTTP委托。不是异步 /v1/jobs，不代替C8。

公共字段：protocol、project_id、job_id、trace_id、base/target完整SHA、profile对象/profile_sha256、candidate_sha256、project绝对路径和out新目录。仅本次RUN_ROOT/jobs/<job>/base或target，拒绝复用OUT/源码内输出/符号链接。member2_run.py生成并原样保存每次JSON。

1. DRAFT增加candidate/build_timeout；成功返回不可变image_id，私有状态冻结job/trace/profile/commits/candidate/image及两版源哈希。
2. BuildChecker增加image_id/timeout_seconds，委托full；基线对base、后续对target。
3. EChecker增加base_project、baseline_graph及其sha256、target_findings及其sha256；委托两次scan并核对full，返回report/payload路径和原字节SHA。完整full不删范围外发现。
4. MDFixer增加report/report_sha256、payload/payload_sha256；核验原件引用/schema/job/trace/commit/profile，生成受限补丁。DRAFT再次校验并委托validate，accepted且清理确认、全部源未变、精确补丁一致后才写回Makefile。

worker只允许full/scan/validate，不接受任意shell。uid为本人非root，network none、资源限额；docker cp避免socket宿主bind路径歧义。检查Python/Git/GCC/Make/strace，缺工具显式失败。保存实际image inspect、源/代码SHA、工具版本、退出码/stdout/stderr及清理时间。

个人E14_ENABLE_FAULTS=1时C4注入sleep，核验唯一operation label容器已停止/删除，再新job恢复。仅验证worker超时，不声称BuildKit构建取消。C5固定不可应用patch，保存git apply stderr、accepted=false、所有tracked和C/H源哈希/Git状态、正确patch对照。生产集成关闭故障开关。

profile算法/字段见B13_PROJECT_MANIFEST与projects目录；信封沿用e11e12-1并绑定profile。外部A13仍需成员1三层result/信封/payload契约；内部生成报告不能冒充A13。

个人端口28081–28084，仅127.0.0.1；8081/8082不动。源码只读、个人work可写；token/env排除导出。共享work属于同一可信团队部署，不是互不信任租户隔离。
