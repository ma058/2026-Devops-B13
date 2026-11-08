# 决策记录

背景与约束：B 轨道复现 MDFixer 受限教学机制，输入为本人 `scan()` 生成的固定 MD 报告（commit 绑定样例内部 HEAD）；实现仅支持显式 C/Make 规则、白名单 CFLAGS 与三种声明风格（direct/macro/mixed）。本人负责边界：异常输入明确拒绝（E8）、受限声明不支持时的明确拒绝（E9）、"能构建但仍有 MD"的候选必须拒绝且源文件受保护（E10）。约束：不修改教学实现即可完成证明时，不为了产生 diff 而改正确实现；不宣称完整论文能力。

选择与替代方案：
B：共享变量怎样处理、失败怎样保证原 Makefile 不变——`patch()` 读取源 Makefile，在内存中生成 diff；`validate()` 将补丁应用、构建和测试放在 sandbox 副本内，全部检查通过才把 sandbox 的 Makefile 写回源目录（lab.py 第 97–122 行）。失败路径以 `source_unchanged` + `rollback` 记录，并对源 Makefile 比较字节。替代方案“直接在源项目上应用再回退”依赖回退逻辑完整性，故本教学流程使用副本。共享变量影响范围：`macro` 风格修改 DEPS 定义会作用于所有引用该变量的目标；受限 fixture 中仅 main.o 引用 DEPS，当前实现无按目标拆分共享变量的能力。本人 E9 测试覆盖未定义变量的声明解析拒绝与无定义行的候选生成拒绝，不证明任意共享变量都被拒绝；完整方案需扩展变量级影响分析。

1. 异常输入拒绝（E8）：`patch()` 先读取源 Makefile，随后逐条检查依赖字符串是否匹配 `[\w./-]+`、是否为绝对路径或含 `..` 路径分量（UNSAFE_PATH），再以 `(p/dependency).is_file()` 检查文件是否存在（MISSING_INPUT）。本次用例验证确定错误和 Makefile 字节保持；哨兵内容相同只能证明内容未变化，不能证明未读取或未访问。替代方案“容忍后由应用阶段报错”会使输入错误被延迟发现，故保留明确的前置拒绝。
2. 受限声明拒绝（E9）：不支持的表达式（展开后残留 `$`、`%`、`|`，或宏引用无定义）以确定错误拒绝；替代方案"静默跳过该目标或放宽为任意异常"被放弃——前者会漏修复并留下误导性候选，后者使测试无法区分错误类别，且与任务书"确定错误断言、不把受限支持误写成完整 Make 支持"冲突。
3. 候选接受与源文件保护（E10）：接受条件为 patch_applies+build+test+header_change+no_missing 五项全部为真（构建成功本身不足以接受）；"仅改注释"候选证明该判据必要：构建与功能均通过，但 header_change/no_missing 揭示 MD 未修复，故拒绝并保持源字节。

代价与覆盖范围：仅支持教学 fixture 同构的受限显式 C/Make 项目，不覆盖论文完整声明图/DIS。声明解析对残留 `$`、`%`、`|` 的表达式明确拒绝；本次测试覆盖其中的未定义变量路径，不证明所有隐式规则、模式规则或多级包含都能被识别并拒绝。宏展开最多 8 轮，不是完整 Make 求值。复制项目和重新构建带来开销；本次实证结论是所测拒绝路径保持源 Makefile 字节，不能扩张为任意输入下“源文件零风险”。手工基线的 reject-test/reject-patch 产物被归档；自主 unittest 使用临时目录，其原始 sandbox 随测试结束删除。

验证命令与实际证据：
- 三阶段基线：`work/e8-B-manual.mjxNgN`、`work/e9-B-manual.3IoSfl`、`work/e10-B-manual.dSh1pJ`；保存的 Python 步骤日志分别为 6、4、7 份，全部 STEP_EXIT_CODE=0，E10 B_GATE_PASS 三行。手册章节数与 Python 日志数不同。
- 自主测试：容器内 `python3 -m unittest discover -s labs/e8e10 -p 'test_*.py' -v` → `Ran 14 tests / OK`（`work/member3-tests-20261103-114036.log`），本人 7 项覆盖上述三个决策点。
- 源文件保护：E10 `source-before.Makefile`/`source-after-accept.Makefile`、validation 中的源字节判定及 E8/E9 拒绝用例的字节断言。原包未保存两次 shell `cmp` 的独立输出；成员1复核了原包最终 Makefile 与 source-after-accept 字节一致，且接受前后仅增加所需依赖。

2026-11-08 成员1审核修订：更正原报告超出证据的读取与支持范围结论，未改教学实现或成员3测试执行逻辑。成员3原始执行、成员1独立复现以及两份归档的路径、SHA-256 见 [REVIEW_FOLLOWUP.md](REVIEW_FOLLOWUP.md)。
