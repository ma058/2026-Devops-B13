# DRAFT 接口契约（B13 草案，待成员1审查及 A13 确认）

## 范围与成功判据

按分工计划区分论文语义与课程扩展：DRAFT 核心输出是使项目能够构建的 Dockerfile，
最多两个上下文文件；HTTP Job、镜像身份、资源上限、功能验证与产物访问属于课程工程化约定。
E2/E3 只交付契约和人工基线，未实现 LLM 提示交替、候选排序及自动迭代算法。

## 请求

沿用 schema_version=1.0、trace_id、job_type=DRAFT、idempotency_key。
input.repository 为仓库 URL 和完整 40 位 commit；context_files 为最多两个仓库相对路径。
input.build 包含 command、verify_command、expected_stdout、clean_command、working_directory、
正整数 timeout_seconds。max_iterations 为正整数；configuration_id 标识构建配置。
timeout_seconds 暂定义为单次构建/验证命令上限；任务总时限策略待公共契约确认。

## 状态和响应

沿用 ADR-001：POST 创建任务后返回 HTTP 202 和 QUEUED 快照，
通过 `GET /v1/jobs/{job_id}` 查询进度。创建路径与部署地址随公共契约冻结；本次没有部署 HTTP 服务。

- draft.accepted.json 表示 QUEUED，不新增 ACCEPTED 枚举。
- QUEUED/RUNNING 的 output 和 error 均为 null。
- SUCCEEDED 要求 build_exit_code=0、verify_exit_code=0，verify_stdout 与 expected_stdout 精确一致（含换行）。
- FAILED 的 output=null，error 必须有 code、message，可附 log_uri；超时沿用 TIMED_OUT。
- 错误示例 DRAFT_BUILD_FAILED 仅为 B13 草案错误码。

成功响应保留 image_ref，新增 image_id（sha256）作为实际本地镜像身份。
跨机器访问另需 registry digest 或镜像导出及读取规则，不能只靠本地 image_id。
environment 包含 Linux OS、arch、project_root、working_directory、clean_build_command、
configuration_id、repository_commit 和 tracking。tracking.status=PENDING_A13 时权限数组可为 null；
CONFIRMED 时必须填写数组（不需要附加权限则为空数组），并在 pair-review 留实际确认链接。
源码 SHA 和 configuration_id 必须与请求和 artifacts 一致。

iterations 保存每轮编号、退出码、日志 URI、修改说明；artifacts 包含 Dockerfile、日志和 diff。
示例中的两轮迭代是合成演示，不代表已运行自动迭代服务。

## 基线与接口的关系

fixtures/draft 在容器内使用 /workspace/project，make clean && make 完整构建，./hello 输出 hello E3。
代码来自 fixtures/draft 子目录；真实集成时需在工作区说明中保持这一映射。
evidence 下保存的 summary.json 是本地运行证据，不冒充 HTTP Job 成功响应。
现有 examples 中 URL、SHA、镜像 ID 和 URI 仍是合成数据，不是可下载产物。

## 校验与兼容

公共 JSON Schema 新增 DRAFT 专有条件，不改变其他 job_type 的字段。
validate.py 额外校验跨字段一致性（标准 JSON Schema 不负责比较两个字段的值）。
本次加严草案 DRAFT 字段会拒绝旧的精简 DRAFT 示例；需成员1审查，再由 A13 确认后冻结。
当前 1.0 仍为未冻结草案，不能据此宣布生产兼容性承诺。

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
python scripts/check_jsonschema.py
```

最后一项需要项目虚拟环境中的 requirements-dev.txt。

## A13 待确认

1. image_ref、本地 ID 与 registry digest/镜像导出的交接方式。
2. Linux 架构、跟踪工具、ptrace capabilities 与安全配置；未默认开启 privileged。
3. project_root、working_directory、clean 命令和项目外依赖过滤。
4. configuration_id 与源码 SHA/镜像/报告绑定。
5. artifact:// 的实际共享位置及每轮日志是否足够。

上述事项需要真实 Issue/Review/会议结论，当前未发送跨组消息，未获得 A13 确认。
