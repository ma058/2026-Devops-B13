# main 最终 CI 下载原件内部核验

结论：**PASS**。对已下载 run `46145327540` attempt2 的两份成功 artifact 做离线逐字节核验；没有运行收到的脚本、解包写入其路径、重跑实验或改动 attempt1 失败原件。源码固定 `fb4be620da9587ea3dc35581eeb2599ffe98fae7`。

## 归档结构和清单完整性

| 对象 | 实际核验 |
|---|---|
| `retry-success-four-services-15263562683.zip` | 两个 ZIP 文件（tar.gz+外层摘要）；内层 tar 736 个普通文件；原 tar SHA `8265c690ddbdfa143b2adc90b93fa2eca6f72fb3294494db777e52dccc8a2d69` 与旁附清单相符 |
| 四服务根 `MANIFEST.json` | **735/735**，字节数与 SHA 全匹配；清单排除自身；无缺失或额外文件，含12项隐藏文件 |
| 四服务 Job `MANIFEST.json` | **711/711**，字节数与 SHA 全匹配；同目录普通文件一一对应，含12项隐藏文件 |
| `retry-success-e13e14-evidence-15264165007.zip` | **914** 个普通文件，31个隐藏文件实际存在 |
| 成员一 `evidence-sha256.json` | **746/746**，SHA全匹配，清单排除自身；该目录无缺失或额外文件，含24项隐藏文件 |
| 源码前后快照 | before、after-C1/C2/C3/C8共5份清单，每份8项，**40/40**；每份均含`.gitignore`，前后摘要字典完全相同 |
| 四服务教学 result 的产物引用 | **162/162**，URI及SHA/字节数可解析且一致，五阶段身份与result一致 |
| 成员一 C1/C2/C3 产物 | local-A **85/85**，B消费 **227/227**，C2 **2/2**，C3 **2/2**；结果引用与独立检查清单均复算通过 |
| 成员一 C8 下载 | **85/85**，文件SHA/大小/HTTP头部摘要一致，下载文件与HTTP响应体逐字相同；**92/92** HTTP原始响应体符合对应metadata摘要 |

ZIP/tar 全量路径检查未发现绝对路径、`..`越界、Windows盘符、反斜杠、重复路径、大小写冲突、符号链接或特殊tar条目。未发现`.git`、`.env`、`token.secret`文件或私钥标记。此为指定结构/文件名/私钥模式核查，不声称能穷尽任意凭据形式。

教学 artifact 的另外四份外围日志（`ci-member1-logs/run.log`、服务 diagnostics 的capture-status/ps/services）不在上述实验清单范围内；已检查归档路径/读取内容并由整体ZIP摘要保护，不虚构成某个实验manifest已列出的条目。

## 实际成功的 b13-level-v1 链

- Job：`job-f3376ecdc60c4a8c8c78650eeef281a4`；Trace：`trace-b110a3cdd61a47e4afc20406852fa2c7`。
- 根source-commit、evidence/source-commit与summary implementation_sha均为`fb4be620`完整SHA。
- 6个runtime execution原件的容器ID各不相同，镜像均为`sha256:a7eb9611d7d7757001c5a7a78af72f41a6d2bda5ad698dd1788340acf59d0545`，记录退出码均0；36个worker代码/配置摘要与经Git blob核验的fb4be620源码ZIP逐一匹配。
- final-full原始findings状态SUCCEEDED、build exit0、无MISSING；保留`REDUNDANT(main.o, unused.h)`。summary写回仅Makefile，与正常链CI原日志一致。
- 本包只有normal一轮，不把它写成C4/C5故障矩阵或A13跨机运行。

## C1/C2/C3/C8 教学范围

成员一summary明确`LOCAL_SIMULATED_A`、`formal_cross_group_matrix=NOT_RUN`、`teacher_hidden_tests=NOT_RECEIVED`，course_source_commit为fb4be620。C1为本地A模拟报告及B消费；C2实际STALE_REPORT、C3实际ARTIFACT_HASH_MISMATCH，均在stages=[]时拒绝，前后源码快照相同。

C8为Runner本地既有异步API：Job `job-c55e0c4cd52d446fb06168bacb8de6b3`、Trace `trace-9357fecc2688465d923171253b822951`，原始HTTP为202/202/409，submit与duplicate返回同一Job；2阶段产物身份及85项下载原件已核。`a13_client_session=false`，不能将本轮写成A13真实客户端或正式tomlc99全项目验收。

两份artifact的GitHub API摘要已在上一轮核对，本轮补齐内部字节、引用、隐藏文件与执行范围核查。失败attempt1仍原样留存；此次成功不能消除其APT镜像站超时事实，也不等于组级正式RC验收。

复现：`python -X utf8 nov28-handoff/audit_final_ci.py`。脚本由本次负责人侧编写，仅使用标准库内存读取与哈希；完整计数及检查结果见`ci-final-audit.json`。
