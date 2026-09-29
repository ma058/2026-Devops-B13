# REPAIR 任务与 MD 报告接口契约（成员3）

适用配对：B13（MDFixer）↔ A13（BuildChecker / EChecker）。
本文定义两类契约：(1) `contracts/schemas/md-report.schema.json` 描述的 MD/RD 检测报告；(2) REPAIR 任务的请求与响应。
配套样例：`contracts/examples/md-report.json`、`repair.request.json`、`repair.succeeded.json`、`repair.failed.json`，以及预期拒绝样例 `contracts/examples/invalid/md-report.invalid-short-sha.json`、`md-report.invalid-detector.json`。

## 1. 论文语义来源与课程工程化扩展

**论文原始语义（约束核心行为，不得曲解）：**

- MDFixer（ASE 2025）的输入是「项目仓库 + 依赖错误报告」，错误报告是若干 `(target, [缺失依赖...])` 对（论文中来自 EChecker）；输出是修复后的 Makefile / 补丁。论文只处理 **MISSING** 依赖，不处理 REDUNDANT。
- MDFixer 按声明风格修复：显式声明用风格保持的规则化转换（Target / Macro / Hybrid 转换），隐式声明用 LLM 生成项目特定补丁（`.d` 文件是推荐策略之一，不是唯一解）。
- EChecker（ISSTA'24）按文件路径排除 `project_root` 之外的系统依赖（如 `/usr/include/...`），MD/RD 报告只针对项目内文件。
- Hybrid 转换使用 wildcard 宏的前置条件（论文 III-D 节）：同目录被匹配的同类型文件全部是有效依赖，且不引入额外无关文件；无法满足时回退为显式枚举。

**课程工程化扩展（不是论文原始接口，禁止声称是论文内容）：**

- HTTP 异步 Job 模型（`POST /v1/repair-jobs` 返回 202，`GET /v1/jobs/{job_id}` 查询）。
- JSON Schema 契约、`artifact://` 产物 URI、`trace_id`、`schema_version`、错误码分类。
- `configuration_id`、环境字段（os/arch/image_ref）、功能验证命令。
- Git Patch 形式的修复交付物、`rejected_candidates` 无效候选拒绝记录、修复后重检入口。

以上差异须在 ADR 中记录（公共 ADR-001/002/003 由成员1负责；混合报告过滤策略建议新增 ADR-004，见第 8 节）。

## 2. MD 报告结构（md-report.schema.json）

顶层字段：

| 字段 | 必填 | 含义 |
|---|---|---|
| `schema_version` | 是 | 固定 `"1.0"`，与全组公共 Schema 版本风格一致 |
| `report_id` | 是 | 报告唯一标识 |
| `repository.url` / `repository.commit` | 是 | 被检测仓库与**完整 40 位 commit SHA**；报告必须绑定确切源码版本 |
| `configuration_id` | 是 | 构建配置标识；报告、baseline、Patch 与复检只在同一配置下可比 |
| `environment` | 是 | 至少含 `os`、`arch`；可含 `make_version`、`cc_version`、`image_ref` |
| `detector` | 是 | 报告**生成者/判断来源**，四值枚举见下 |
| `provenance` | 是 | **具体来源、版本与证据补充**（与 detector 不同义）：课程样例写明课程手册位置；B13 人工样例写明对应 fixture、commit 和人工判断依据；工具报告写明工具版本 |
| `producer_job_id` | 条件必填 | `detector` 为 `BUILDCHECKER`/`ECHECKER` 时必填且匹配 `^job-[A-Za-z0-9-]+$`；人工 Oracle（`INSTRUCTOR_ORACLE`/`B13_MANUAL_ORACLE`）允许省略或为 `null`，**不得编造 Job ID** |
| `findings[]` | 是 | 发现列表，可为空数组 |

**注意**：顶层不重复定义 `makefile_path`（成员1裁定，避免顶层与 finding 内不一致）；Makefile 位置只在 finding 内声明。

`detector` 枚举与使用规则（成员1裁定）：

| 取值 | 用途 |
|---|---|
| `BUILDCHECKER` / `ECHECKER` | 对应工具的真实输出，不得用于人工构造报告 |
| `INSTRUCTOR_ORACLE` | 仅课程提供固定答案的样本（须注明手册出处） |
| `B13_MANUAL_ORACLE` | B13 自建人工样本 |

每条 `finding`：

| 字段 | 必填 | 含义 |
|---|---|---|
| `type` | 是 | `MISSING`（实际依赖但未声明）或 `REDUNDANT`（声明了但本配置未使用） |
| `target` | 是 | 出错构建目标（项目内相对路径或目标名） |
| `dependency` | 是 | 缺失/冗余的依赖文件；使用相对 `project_root` 的 POSIX 路径，不包含 `/usr/include` 等项目外系统依赖 |
| `makefile_path` | 是 | 声明所在 Makefile 路径；同样相对 `project_root`。A13 `location.status=UNRESOLVED` 时由调用方显式提供默认路径，不伪造行号 |
| `location` | 否 | 结构化对象 `{line, declaration}`：声明行号（1 起）与原文；BuildChecker 可从 GNU Make 数据库注释获得 |
| `evidence` | 是 | 判定依据（构建追踪、预处理器分析或人工分析过程） |

**合成值与真实值边界（成员1裁定）**：`contracts/examples/` 内允许 40 位合成 SHA（`contracts/examples/README.md` 已声明全部为合成示例），但合成 SHA 不得写入 E3 运行证据、不得声称对应真实 fixture；`fixtures/mdfixer/*/` 下的正式报告必须引用真实 Git Commit（两段式提交：先提交 fixture 内容，再把该提交的真实 SHA 写入报告；fixture 内容变更后必须换用新 SHA）。

## 3. REPAIR 请求（repair.request.json）

公共 Job 字段（`schema_version`、`trace_id`、`job_type`、`idempotency_key`、`input`）遵循 `contracts/schemas/create-job.schema.json`。`job_type = REPAIR` 时 `input` 字段：

| 字段 | 必填 | 含义 |
|---|---|---|
| `repository.url` / `repository.commit` | 是 | 与 MD 报告同源同版本；不一致时任务失败（见 `repair.failed.json` 示例） |
| `md_report_uri` | 是 | MD 报告的 `artifact://pair13/...` 地址 |
| `makefile_path` | 是 | 待修复 Makefile 路径，相对 `project_root` |
| `environment.configuration_id` | 是 | 构建配置 |
| `environment.os` / `arch` / `image_ref` | 建议 | 修复验证所用环境 |
| `build_command` | 是 | 构建命令（含清理，如 `make clean && make`） |
| `verify_command` | 是 | 功能验证命令（课程 E3 增加的成功判据，非论文原始输入） |
| `policy.consume` | 是 | 固定 `MISSING_ONLY`：REPAIR 只消费 MISSING |
| `policy.if_no_missing` | 是 | 报告中无 MISSING 时的行为，固定 `NOT_APPLICABLE` |

**混合报告处理（重要）：** 报告同时含 MISSING 与 REDUNDANT 时，过滤 REDUNDANT、只修复 MISSING；若没有 MISSING，则返回 `NOT_APPLICABLE`，不拒绝整份请求。A13 交付明确接受 MDFixer 只消费 MISSING；`verify_a13_interop.py` 已用 A13 FULL_CHECK 混合报告验证该行为。

## 4. REPAIR 响应

### 4.1 成功结果

`status = SUCCEEDED` 表示任务正常完成分析，包括接受补丁、没有有效候选和没有可修项三种结果。字段约束由 `repair_status` 决定：

| 字段 | `PATCH_ACCEPTED` | `NO_VALID_CANDIDATE` | `NOT_APPLICABLE` |
|---|---|---|---|
| `repair_status` | 必填 | 必填 | 必填 |
| `patch_uri` | 必填，真实 `artifact://pair13/...` 地址 | 必须为 `null` 或省略 | 必须为 `null` 或省略 |
| `remaining_md_count` | 必填且为 0 | 必填，按重检事实记录（≥0） | 必填且为 0 |
| `consumed_findings[]` | 允许 | 省略或空 | 省略或空 |
| `skipped_findings[]` | 允许 | 允许 | 允许 |
| `rejected_candidates[]` | 可选 | 必填非空，每条含候选、原因和证据 URI | 可选 |
| `recheck` | 必填且 MD=0 | 必填，数量与顶层一致 | 可选；执行时按事实记录 |

`declaration_style` 记录修复前后风格（`TARGET`/`MACRO`/`HYBRID`/`IMPLICIT`）并要求一致；`build`、`test`、`artifact_equivalence` 按实际验证结果记录。对应有效样例为 `repair.succeeded*.json`，两份字段冲突反例位于 `contracts/examples/invalid/repair.invalid-*.json`。

### 4.2 失败（repair.failed.json）

`status = FAILED` 仅用于**系统执行错误**（对应 `docs/E2/status-and-errors.md`：系统错误写入 `error`，正常分析发现写入 `output`）：

- `INPUT_1002`：MD 报告与请求的 commit 不一致（报告不属于当前源码版本，拒绝修复）。`INPUT_` 表示输入或版本校验失败；`ENV_3xxx`、`EXEC_4xxx`、`ANALYSIS_5xxx` 分别表示环境、执行和分析错误。
- `ENV_3xxx`：构建环境不可用。`EXEC_4xxx`：执行错误/超时类。

`error` 至少含 `code`、`message`，可含 `log_uri`（`artifact://` 地址）。

**边界规则：** 候选补丁验证失败（构建失败、行为不等价、重检仍有 MD）**不是** FAILED——它是正常分析结论，以 `SUCCEEDED + repair_status=NO_VALID_CANDIDATE + rejected_candidates[]` 表示。

## 5. 无效候选的拒绝理由

每个被拒绝的候选必须记录：

1. `candidate_id` 与候选内容摘要；
2. `rejection_reason`：明确的验证失败点（如"修复后修改 config.h 仍不触发 main.o 重编译，重检 MD=1"），不接受空泛理由；
3. `evidence_uri`：验证日志地址；
4. 恢复证明：拒绝后恢复原 Makefile，项目重新构建成功（E3 的拒绝-恢复样本由成员1在 implicit-style 目录实现，共用本节约定）。

## 6. 版本绑定与可追溯性

- 报告、修复请求、Makefile、源码必须绑定**同一完整 commit SHA**（Schema 有正则约束）。
- E3 fixture 报告的真实 SHA 通过两段式提交产生：第一个 commit 提交 fixture 内容，第二个 commit 把该 commit 的 SHA 写入报告。当前 implicit fixture 引用 `c65226b27043e0a688d1a4b41249cd7b0893f164`。
- `artifact://pair13/<producer_job_id>/<filename>` 按 `contracts/artifact-access.md` 的 repository-backed locator 解析，并固定完整仓库 commit 与文件 SHA-256。

## 7. 声明风格分类规则（课程级简化）与版本政策

MDFixer 论文用声明图上的 DIS（Declaration Distance Score）分类：DIS=1 → Target 风格；DIS≥2 → Macro 风格；两者兼有 → Hybrid；其余 → 隐式声明。E3 单目标样本采用简化判定（针对 `main.o` 声明行右侧）：只有普通文件 → `TARGET`；只有 `$(宏)` → `MACRO`；两者兼有 → `HYBRID`。该简化是论文式(6)在受控样本上的等价特化，由 `scripts/verify_mdfixer_explicit.py` 在修复前后各执行一次，要求分类一致。

**Hybrid wildcard 守卫（论文前置条件，强制执行）：** 使用 `$(wildcard *.h)` 等 wildcard 宏前，必须证明 (1) 同目录被匹配的同类型文件全部是有效依赖，(2) 不引入额外无关文件。无法证明时回退为显式列举缺失依赖。守卫证明写入各 fixture 的 `expected.json.hybrid_guard`，并由验证脚本实际检查。

**版本政策：** `schema_version` 当前固定 `"1.0"`。兼容变更（新增可选字段）须同步更新 Schema 与样例；破坏性变更（字段删除/改名/改语义、枚举收缩、`required` 收紧）须先开 Issue、注明受影响的生产者/消费者、两组确认后更新版本号并记录到 ADR。

## 8. 与 A13 对齐事项映射（成员3牵头）

| 编号 | 事项 | 本契约中的位置 | 状态 |
|---|---|---|---|
| A-03 | MD/RD 与系统错误的区别 | 第 4 节（findings vs error） | 已接受并写入契约 |
| A-08 | MD 报告格式 | 第 2 节 + A13 固定快照 | 已完成实际互读与归一化 |
| A-09 | 报告与 commit/config 绑定 | 第 6 节 | 已接受并由校验器检查 |
| A-10 | REPAIR 结果与重检 | 第 4 节 `recheck`/`rejected_candidates` | 已接受 base commit + candidate patch 流程 |
| A-11 | Artifact URI 读取 | 第 6 节 | 已采用 repository-backed locator 并完成读取 |
| A-15 | 项目根目录、系统依赖过滤、Makefile 路径 | 第 2 节 | 已统一为相对 project_root 的 POSIX 路径 |
| A-17 | 修复后重检入口 | 第 4 节 `recheck.tool` | 接口已定义；课程 Oracle 已验证，真实 EChecker 接入由其实现提供 |

## 9. 自检命令

```powershell
# 公共校验器与单测（md-report 路由由成员1补充后生效）
python scripts/validate.py
python -m unittest discover -s tests -v

# 具备 jsonschema 包的环境
python3 scripts/check_jsonschema.py
```

在成员1完成校验器路由前，可用以下命令单独验证 MD 报告样例：

```bash
python3 - <<'EOF'
import json
from jsonschema import Draft202012Validator
s = json.load(open('contracts/schemas/md-report.schema.json', encoding='utf-8'))
Draft202012Validator.check_schema(s)
v = Draft202012Validator(s)
ok = json.load(open('contracts/examples/md-report.json', encoding='utf-8'))
assert not list(v.iter_errors(ok)), 'valid sample must pass'
for name in ('md-report.invalid-short-sha.json', 'md-report.invalid-detector.json'):
    bad = json.load(open('contracts/examples/invalid/' + name, encoding='utf-8'))
    errs = list(v.iter_errors(bad))
    assert errs, name + ' must be rejected'
    print(name, 'rejected as expected:', errs[0].message)
print('md-report schema self-check OK')
EOF
```
