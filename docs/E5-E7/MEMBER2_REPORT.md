# 成员2 E5–E7 个人实验报告

## 1. 基本信息与记录阶段

- 执行人：成员2，学号 `241880091`。
- GitHub：`Lacrym1ra`。
- 实验日期：2026-10-24。
- 独立克隆：`/root/241880091/e5-e7-b13`。
- 实验目录：`labs/B-draft`。
- 个人工作分支：`member2/e6-evidence-validation`。
- 本报告记录阶段：两类E6独立执行及修复后保存证据复查完成，修改后服务重建与E7正式回归结果尚未确认。

本人承担E6独立复验、双候选比较、证据校验器扩展及测试，并参与公共基线审查。实验采用教学DRAFT参考实现和已保存候选回放。

## 2. 运行前环境与版本状态

### 2.1 宿主机环境

| 项目 | 实际记录 |
| --- | --- |
| 操作系统 | Ubuntu 22.04.5 LTS |
| 内核／架构 | 5.15.0-191-generic／x86_64 |
| CPU／可见内存 | 2核／3.5 GiB |
| 自检时可用磁盘 | 69.3 GiB |
| Docker server | 29.1.3 |
| Compose | 2.40.3+ds1-0ubuntu1~22.04.1 |
| buildx | 0.30.1 |
| Git／Make／Python | 2.34.1／4.3／3.10.12 |
| 自检时仓库级Git身份 | 241880091／241880091@localhost |
| Docker socket组号 | 121 |
| Docker镜像加速配置 | registry_mirrors为空 |
| 服务镜像标签 | `b13-draft:241880091-e567` |

首次doctor因可见内存3.5 GiB低于教学脚本最低4 GiB而退出1。另有CPU、可用磁盘低于建议值及未配置镜像加速的warnings。

本次环境适配针对课程小样例，沿用同仓库E4的3.5 GiB最低可见内存设置，保持8 GiB建议值和真实测量。服务器Git状态已显示doctor.py有修改；适配后的独立自检结果尚未纳入已核验记录。

### 2.2 源码状态

公共基线初审固定head为 `2228b193f023554d5b194dc2f400a67219d9128b`。该值是审查版本；本人首次E6实际运行SHA没有在已确认输出中记录。

修复后两套证据复查完成时，服务器Git状态为：

```text
 M scripts/doctor.py
 M scripts/verify_e6_b_evidence.py
?? tests/member2/
```

此状态表明当时服务器修改尚未提交。此次个人代码交付提交为 `9a6231f7a49e5cbc7372fe3283e69a15a7c0aab7`；该值不回填为历史E6运行SHA。服务器修改后正式回归SHA及服务镜像完整ID仍暂无已核验记录。

## 3. 双候选独立E6复验

两类候选来自 `fixtures/b13-candidates/`，来源见provenance.json。候选由成员1保存并经过教学环境适配；本人的工作为独立执行、比较及后续证据规则扩展。

### 3.1 已确认结果

| 项目 | error-driven | context-driven |
| --- | --- | --- |
| 成功运行目录 | `work/m2-e6-error-20261024-131210/` | `work/m2-e6-context-20261024-131605/` |
| trace_id | `e6-b-e44d95b1e9124b7584228d5ff8a26e70` | `e6-b-42da9e5017364d17ac0e6786e457c56b` |
| 候选SHA-256 | `db8fdf9a1e6377ae916494d5e1608a74d94be8ba1192c27e6db2c1a830d58e4a` | `16391e090c39fa363ff0a8c5562a9904ed5716d70e9568ee3c5d96f8b28c611b` |
| E6采集入口退出码 | 0 | 未单独核验 |
| 首轮构建 | 非零退出，分类MISSING_MAKE | 非零退出，分类MISSING_MAKE |
| 首轮具体退出码 | 尚未从原始result.json核验 | 尚未从原始result.json核验 |
| 第二轮构建退出码 | 0 | 0 |
| 最终程序退出码 | 0 | 0 |
| 验证输出 | hello E3 | hello E3 |
| 原校验器检查 | passed=true | passed=true |
| 修复后校验器检查 | passed=true | passed=true |

error-driven实际构建并验证的候选镜像ID：

```text
sha256:293f98fdffbcd1e258b7cf08534f721fc9434468c6e054edb121c9d0bbb83546
```

context-driven实际构建并验证的候选镜像ID：

```text
sha256:5a6af2458246b2dcb048abfb8e64e5591c16a7360fb46441c7d9f57c7894d55f
```

两套成功目录是在校验器扩展前生成的Docker实验记录；扩展后只重新读取保存证据进行检查，没有将其当作修改后新运行的Docker实验。

### 3.2 对照结论

error-driven候选显式安装build-essential；context-driven候选显式安装gcc、libc6-dev和make。两类候选均完成缺make基线到成功构建、输出hello E3的流程，候选哈希与来源记录一致。

最终包列表、镜像大小、workflow_elapsed_ms及缓存命中尚未完成实际数值核验。本报告据此仅确认功能结果一致，不作速度或模型质量排名。两个候选镜像ID不同属于本次实测差异。

## 4. 个人代码修改

| 文件 | 实现内容 |
| --- | --- |
| `scripts/doctor.py` | 课程小样例的最低可见内存适配 |
| `scripts/verify_e6_b_evidence.py` | 输入清单完整性、路径、摘要、不可变镜像ID与最终运行禁网规则 |
| `tests/member2/test_e6_evidence_validation.py` | 19项保存证据一致性测试 |

校验器扩展包括：

1. input_sha256必须是非空映射，路径为规范相对路径，摘要为合法SHA-256。
2. 清单路径集合与project实际文件集合严格一致，并逐项检查内容哈希。
3. 拒绝遗漏、额外输入、路径逃逸及符号链接。
4. 最终验证命令必须为使用保存镜像ID的docker run，并明确设置--network none；拒绝参数删除、重复覆盖、别名绕过及未知选项。
5. 保留两轮顺序、缺make日志、候选哈希、程序退出码与输出校验。

代码与测试由助手协助编写，本人负责理解、服务器安装、运行和验证。测试在临时目录构造结构化证据，原始E6目录保持不变。

## 5. 修复前后验证结果

测试日志目录：`work/m2-code-20261024-140731-142857/`。

### 5.1 修复前

服务器实际运行19项测试。提供的输出包含12条FAIL和7条ERROR，其中含同一测试方法的多个子测试条目，因此不将两者相加作为失败测试方法数。

| 检查 | 旧实现实际表现 |
| --- | --- |
| 删除输入清单条目 | 未拒绝，负例FAIL |
| 增加额外project文件 | 未拒绝，负例FAIL |
| 空清单 | 未拒绝，负例FAIL |
| network改为bridge或删除禁网参数 | 未拒绝，负例FAIL |
| 重复网络参数及--net覆盖 | 未拒绝，负例FAIL |
| 可变镜像标签、错误命令、内部符号链接 | 存在未拒绝情况 |
| input_sha256为None、列表或字符串 | 抛出AttributeError |
| 非法路径 | 出现IsADirectoryError或FileNotFoundError |
| 大写摘要 | 旧实现按大小写比较，出现哈希不匹配 |

这些结果表明新增测试暴露了旧校验器的输入完整性与命令检查不足。

### 5.2 修复后

两套本人真实E6保存证据均经新校验器检查，返回passed=true；trace_id、候选哈希、镜像ID和验证输出与先前记录一致。

修复后19项服务器测试的最终通过数、跳过数及退出码尚未完成报告核验。本报告未以两套真实证据通过推定全部负例测试通过。

## 6. 核心流程字段说明

| 字段 | 产生位置与作用 |
| --- | --- |
| failure_class | classify_failure根据首轮实际日志区分MISSING_MAKE、INFRASTRUCTURE和其他构建错误 |
| candidate_sha256 | auto_build初始化报告时对读取的候选文本编码字节计算SHA-256 |
| input_sha256 | 复制并过滤fixture形成project后，记录相对路径与文件哈希 |
| image_id | 第二轮构建后通过docker image inspect取得，并用于最终程序运行 |
| verification | 记录运行命令、退出码、预期／实际输出与匹配结果 |
| status | 初始RUNNING；成功SUCCEEDED；执行错误FAILED；超时TIMED_OUT，最终写入result.json |

外层服务容器联网用于构建访问；最终程序验证的禁网规则检查verification.command。

## 7. 修改后正式回归与协作记录

| 项目 | 当前证据状态 |
| --- | --- |
| 修改后代码提交及运行SHA | 个人代码交付已提交；服务器正式回归运行版本尚未核验 |
| 服务重建、服务pytest及容器工具链 | 尚无已核验结果 |
| E7整体gate及五类场景 | 尚无已核验结果 |
| runtime-timeout容器清理 | 尚无已核验结果 |
| 工作区、历史与镜像扫描 | 尚无已核验结果 |
| PR #16同伴审查 | 已完成本地初审；正式远端Review链接未纳入记录 |
| 个人PR | [PR #18](https://github.com/ma058/2026-Devops-B13/pull/18)，Draft，依赖公共基线PR #16 |
| 成员3Review与CI交接 | 已请求yqy241880115 Review；实际审查和CI接入尚无完成记录 |

服务pytest与成员2新增证据测试分别统计。

## 8. 个人证据索引

| 证据 | 位置 |
| --- | --- |
| error-driven原始执行记录 | `work/m2-e6-error-20261024-131210/` |
| context-driven原始执行记录 | `work/m2-e6-context-20261024-131605/` |
| 修复前后测试日志目录 | `work/m2-code-20261024-140731-142857/` |
| 修改后正式构建、gate与扫描记录 | 尚未核验 |
| 原始证据包及SHA-256 | 尚未核验 |

## 9. 阶段结论

本阶段已确认两类保存候选E6执行成功，首轮均复现MISSING_MAKE，第二轮构建成功，程序退出0并输出hello E3。新增测试已在服务器暴露旧校验器缺陷；扩展后，两套真实保存证据仍能通过检查。

当前服务器证据记录位于修改后正式Docker回归前，个人代码已形成提交并创建Draft PR #18。服务器19项测试最终结尾、正式回归、镜像扫描及Review结果尚未核验，因此本报告不作全阶段完成判定。

本次个人PR暂以 `member1/e5-e7-bootstrap` 为base，仅提交成员2改动；PR #16合并后再核对差异并调整至main。当前不执行合并。
