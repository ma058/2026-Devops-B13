# 成员3协调指令 R3 回复

- 日期：2026-09-24
- 回复人：成员1
- 对应材料：成员3协调指令 R3
- 状态：E2 校验器集成已完成；E3 跨平台复验问题待成员3修复

## 总体结论

R3 方案整体确认。E2 契约与 E3 显式修复样本继续使用两个独立 Draft PR，不合并成一个 PR，以便分别追溯契约贡献和实验实现贡献。

当前进度：

- E2 Draft PR：`#6 feature/e2-repair-contract-m3`
- E3 Draft PR：`#7 feature/e3-explicit-repair-m3`
- 成员1已向 E2 分支提交并推送 `c276f2c feat(e2): validate and route MD reports`
- E2 的 B13 本地验证已全部通过
- E3 三份报告兼容 E2 最终 Schema，但验证脚本仍需修复 Windows/WSL 换行符及权限复制问题

合并顺序固定为：

1. 完成并合并 `feature/e2-repair-contract-m3`
2. 将 `feature/e3-explicit-repair-m3` 同步到最新 `main`
3. 在最新契约与校验器基础上重新运行全部检查
4. Review 并合并 E3 PR

E2 Draft PR 已创建，成员1已使用自己的 Git 身份完成校验器路由、Schema 加固、单元测试及验证记录提交。两个 PR 在满足本文件的合并条件前继续保持 Draft。

## Schema 预审结论

### 已确认设计

- `schema_version` 固定为 `"1.0"`
- `detector` 使用四值枚举：`BUILDCHECKER`、`ECHECKER`、`INSTRUCTOR_ORACLE`、`B13_MANUAL_ORACLE`
- `producer_job_id` 根据 detector 条件必填
- `makefile_path` 只在每条 finding 中必填，顶层不重复定义
- `makefile_path` 的基准目录继续标记为 provisional，等待 A13 确认
- E2 契约样例可以使用已明确标注的合成 40 位 SHA
- E3 Fixture 报告必须引用真实 Git Commit SHA

### findings 允许为空

Schema 中的 `findings` 必须允许空数组。修复后 EChecker 可能返回 0 个 MD，如果强制 `minItems: 1`，将无法表达正常的修复后结果。

具体课程有效样例可以包含 finding，但 Schema 不应禁止：

```json
{
  "findings": []
}
```

### location

`location` 可以作为可选的结构化对象，当前版本建议限定为：

```json
{
  "line": 12,
  "declaration": "main.o: main.c"
}
```

约束：

- `line` 为正整数
- `declaration` 为非空字符串

若以后需要行号范围，应通过兼容版本增加字段，不在当前版本提前扩展。

### environment

`environment` 需要明确最小字段及含义，建议至少包含：

- `os`
- `arch`

工具版本可以作为可选字段或独立对象。不得只定义一个没有字段说明的完全开放对象。

### provenance

`provenance` 必须说明来源、版本或判断依据：

- 课程 Oracle：定位到课程手册或课件的具体位置
- B13 人工 Oracle：说明 Fixture、真实 Commit 和人工判断依据
- BuildChecker/EChecker：说明工具版本及对应生产 Job

`detector` 表示报告生成者或判断来源，`provenance` 用于补充该来源的可追溯信息，两者含义不得混用。

### producer_job_id

- `BUILDCHECKER`、`ECHECKER`：必须提供真实 `producer_job_id`，并匹配 `^job-[A-Za-z0-9-]+$`
- `INSTRUCTOR_ORACLE`、`B13_MANUAL_ORACLE`：允许省略或为 `null`

人工报告不得编造 Job ID。

## 无效样例要求

两个反例必须分别只有一个拒绝原因：

### 短 SHA

```text
contracts/examples/invalid/md-report.invalid-short-sha.json
```

除 `repository.commit` 不是 40 位十六进制外，其余字段全部有效。

### 未知 detector

```text
contracts/examples/invalid/md-report.invalid-detector.json
```

除 `detector` 不在四值枚举内，其余字段全部有效。

测试日志需要证明两个样例分别因预期字段被拒绝，不能只证明“存在某个 Schema 错误”。

## Implicit 模板要求

更新 `fixtures/mdfixer/implicit-style/md-report.template.json` 后，成员3还需检查 Fixture README 和证据说明，确保不再残留：

- 旧字段 `provenance: B13_MANUAL_ORACLE`
- 平铺的 `repository_commit`
- finding 中的旧字段 `makefile`

Implicit 报告只有在分析的源码和 Makefile 与下列提交一致时，才能引用：

```text
c65226b27043e0a688d1a4b41249cd7b0893f164
```

如果被分析的 Fixture 内容发生变化，必须引用新的真实 Fixture Commit。

## 校验器集成方式

成员1已在 `feature/e2-repair-contract-m3` 增加独立 Commit，修改：

- `scripts/validate.py`
- `scripts/check_jsonschema.py`
- `tests/test_contracts.py`

对应提交为：

```text
c276f2c feat(e2): validate and route MD reports
```

该提交已直接推送到成员3的 E2 分支，因此不需要重定向基底或 Cherry-pick。

## 实际复验结果

### E2 PR #6

以下检查已经通过：

```powershell
python scripts/validate.py
python -m unittest discover -s tests -v
```

```bash
python3 scripts/check_jsonschema.py
python3 scripts/verify_implicit.py
```

结果：

- 轻量契约校验全部通过
- 16 项单元测试全部通过
- 4 份 Schema 均通过 Draft 2020-12 结构检查
- 有效样例及 implicit 模板通过正式 Schema 校验
- 无效样例全部按预期被拒绝
- E3 implicit 基线回归通过

### E3 PR #7

Target、Macro 和 Hybrid 三份 `md-report.json` 均通过 #6 最终 Schema，且引用各自真实的 Fixture 提交：

- Target：`84f6e9df0ec021ed4e5fb41239aab4657b6f96ef`
- Macro：`5f599d2592fbf4a678950b7f7b2886b6844ad9e4`
- Hybrid：`2810e238b99f3989120d58593eb5328282f38d41`

但是，原版 `scripts/verify_mdfixer_explicit.py` 在 Windows 检出、WSL 执行时不能全绿。根因是：

1. `.gitattributes` 中的精确规则 `Makefile text eol=lf` 不匹配 `Makefile.before`，后者可能以 CRLF 检出。
2. `shutil.copy2()` 会将 Windows/WSL 映射出的可执行权限复制到 Linux 临时目录，使临时 `Makefile` 成为 `100755`。
3. `reference.patch` 按 LF、`100644` 生成，因此三个样本均在 `git apply --check` 阶段失败，后续增量重编译与 Oracle 重检连锁失败。

建议成员3将临时 Makefile 的创建逻辑改为：

```python
if name == "Makefile.before":
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(makefile_before)
    os.chmod(dst, 0o644)
else:
    shutil.copy2(src, dst)
```

同时建议在 `.gitattributes` 中增加：

```gitattributes
Makefile.* text eol=lf
```

成员1已在隔离副本中验证上述脚本修正：

- Target：16 PASS，0 FAIL
- Macro：16 PASS，0 FAIL
- Hybrid：17 PASS，0 FAIL

此临时修正仅用于确认根因，未直接提交到 #7。成员3应在自己的 E3 分支完成正式修改并重新生成证据。

## 运行环境与证据

PR 描述必须注明各命令真实运行的环境：

- Windows：Python 版本、`jsonschema` 版本
- WSL：发行版、内核、GNU Make、GCC 和 Python 版本

必须实际运行：

```powershell
python scripts/validate.py
python -m unittest discover -s tests -v
```

```bash
python3 scripts/check_jsonschema.py
python3 scripts/verify_implicit.py
```

不同环境的命令不得写成同一次运行。若成员3的 WSL 无法运行 `verify_implicit.py`，应保存原始错误并联系成员1复验。

## A13 对齐

成员3继续直接联系 A13，确认：

- `makefile_path` 的基准目录
- 路径规范化规则
- 系统头文件及项目外依赖的过滤规则
- Patch 的读取和应用方式
- EChecker 修复后复检步骤
- 复检返回字段

确认前，上述内容继续标记为 provisional。成员3应把原始回复或可访问链接同步到 B13 共享渠道，并更新 `docs/E2/pair-review.md`。

## 合并条件

### E2 Draft PR

- [x] MD Report Schema 通过 Draft 2020-12 自检
- [x] 有效 MD Report 样例通过
- [x] 短 SHA 样例因 SHA 原因被拒绝
- [x] 未知 detector 样例因枚举原因被拒绝
- [x] 两个校验器均支持 MD Report 路由
- [x] 原有 Job、请求和 Artifact 校验没有回归
- [x] Implicit 模板与正式 Schema 一致
- [ ] A13 未确认字段标记为 provisional
- [ ] 非 PR 作者完成有效 Review

### E3 Draft PR

- [x] 三个显式 Fixture 独立可运行
- [x] Fixture 报告引用真实 Commit SHA
- [ ] 参考 Patch 可以应用
- [ ] 修复后增量构建行为正确
- [x] clean build 行为未被破坏
- [ ] 无效候选能够拒绝并恢复
- [x] 证据目录包含 observations、原始日志和机器可读摘要
- [ ] 分支已同步包含 E2 Schema 和校验器的最新 `main`
- [ ] 非 PR 作者完成有效 Review

## 当前下一步

1. 成员3在 `feature/e3-explicit-repair-m3` 修复临时 Makefile 的换行符和权限处理。
2. 成员3重新运行 `python3 scripts/verify_mdfixer_explicit.py`，更新 observations、原始日志和机器可读摘要。
3. 成员3补充无效修复候选的拒绝与恢复验证。
4. B13 对 E2 PR #6 完成非作者 Review；A13 未确认字段继续保留 provisional 标记。
5. E2 合并后，成员3将最新 `main` 同步到 E3 分支并再次执行完整复验。
6. E3 全绿且完成 Review 后方可解除 Draft 并合并。
