# 决策记录

背景与约束：B 轨道复现 MDFixer 受限教学机制，输入为本人 `scan()` 生成的固定 MD 报告（commit 绑定样例内部 HEAD）；实现仅支持显式 C/Make 规则、白名单 CFLAGS 与三种声明风格（direct/macro/mixed）。本人负责边界：异常输入明确拒绝（E8）、受限声明不支持时的明确拒绝（E9）、"能构建但仍有 MD"的候选必须拒绝且源文件受保护（E10）。约束：不修改教学实现即可完成证明时，不为了产生 diff 而改正确实现；不宣称完整论文能力。

选择与替代方案：
B：共享变量怎样处理、失败怎样保证原目录不变——本实现候选生成与验证全部在内存/沙箱副本上进行：`patch()` 只读源 Makefile 生成 diff，任何写回都发生在 `validate()` 的 sandbox 副本内，全部检查通过才写回源文件（lab.py 第 97–122 行）；失败路径以 `source_unchanged` + `rollback` 显式记录并以字节比较证实。替代方案"直接在源项目上应用再回退"被放弃：回退依赖清理逻辑完整性，失败残留风险高于副本策略。共享变量影响范围：`macro` 风格修改 DEPS 定义会作用于所有引用该变量的目标；受限 fixture 中仅 main.o 引用 DEPS，若出现多目标共享同一变量且仅需修复其一，当前受限实现无按目标拆分能力——本人 E9 用例选择"明确拒绝/如实声明影响范围"路线（UNSUPPORTED_DECLARATION/UNSUPPORTED_MACRO 均为确定错误，不静默扩大作用域），完整方案需按论文 DIS 扩展变量级影响分析。

1. 异常输入拒绝（E8）：依赖字符串必须匹配 `[\w./-]+` 且非绝对路径、不含 `..`（UNSAFE_PATH），且必须存在于项目内（MISSING_INPUT）后才允许任何 Makefile 处理；替代方案"容忍后由应用阶段报错"被放弃——那会让不安全输入进入后续流程并在拒绝前后产生不可预测的读取行为。哨兵文件用例证明拒绝发生在访问之前。
2. 受限声明拒绝（E9）：不支持的表达式（展开后残留 `$`、`%`、`|`，或宏引用无定义）以确定错误拒绝；替代方案"静默跳过该目标或放宽为任意异常"被放弃——前者会漏修复并留下误导性候选，后者使测试无法区分错误类别，且与任务书"确定错误断言、不把受限支持误写成完整 Make 支持"冲突。
3. 候选接受与源文件保护（E10）：接受条件为 patch_applies+build+test+header_change+no_missing 五项全部为真（构建成功本身不足以接受）；"仅改注释"候选证明该判据必要：构建与功能均通过，但 header_change/no_missing 揭示 MD 未修复，故拒绝并保持源字节。

代价与覆盖范围：白名单校验使实现无法处理复杂 Make 语法（隐式规则、模式规则、多级包含等），这些输入被明确拒绝而非部分处理；每次验证复制完整项目到沙箱并重新构建，换取"源文件零风险"与"失败证据完整保留"（reject-test/reject-patch 目录保留全部日志）；宏展开上限 8 轮，防御性截断而非完整求值。覆盖范围如实声明：仅教学 fixture 同构的受限项目，不覆盖论文完整声明图/DIS。

验证命令与实际证据：
- 三阶段基线：`work/e8-B-manual.mjxNgN`、`work/e9-B-manual.3IoSfl`、`work/e10-B-manual.dSh1pJ`（各步 STEP_EXIT_CODE=0，B_GATE_PASS 三行）。
- 自主测试：容器内 `python3 -m unittest discover -s labs/e8e10 -p 'test_*.py' -v` → `Ran 14 tests / OK`（`work/member3-tests-20261103-114036.log`），本人 7 项覆盖上述三个决策点。
- 源文件保护：E10 `source-before.Makefile`/`source-after-accept.Makefile` 与两次 `cmp` 退出码 0；E8/E9 各拒绝用例的 Makefile 前后字节断言。
