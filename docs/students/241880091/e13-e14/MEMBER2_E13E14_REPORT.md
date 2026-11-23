# 成员2 E13–E14 个人报告

更新日期：2026-11-23；241880091 / Lacrym1ra。本人服务器四角色链路、C4、C5已执行并完成下载原件复核；A13跨组验收及最终CI/Review仍待收口。

## 执行身份、版本与原件

本人Linux账号m2_241880091，uid/gid 1001，执行前干净仓库。执行源码为 `99f2c7abd1cad161cbfa4affe8d2109568d948ab`；后续文档/证据及变量改名提交不冒充新的服务器执行SHA；本轮协调改名后的head未重新运行个人服务器矩阵。项目b13-level-v1基线/目标、候选和profile见B13_PROJECT_MANIFEST.md。运行目录work/m2-e14-396e048fe158，四角色端口28081–28084；仅DRAFT挂socket，未使用8081/8082。

实际执行下发包run-server.sh，核心命令为 `python3 labs/e13e14/member2_run.py --config "$M2_E14_CONFIG" --scenario all`。构建、设置、服务启动、76项测试及矩阵的COMMAND_EXIT/TEE_EXIT均为0；诊断、日志收集及本次Compose down均为0。

完整原件：`member2-e13e14-m2-e14-396e048fe158.tar.gz`，SHA-256 `4157bd945a4fbd5bf3e87a935d0fb38a90fac77d478f97873e6101ef3f6e4707`。下载位置E11-E12/证据归档/e13e14-export-20261123-uLgBFI/payload/，由本人提供取阅。外层SHA、内部2387项清单（总2388成员）、原件源码bundle与独立bundle一致，均已核对。

仓库证据摘录：`evidence/20261123-personal-matrix/`，含矩阵、19份镜像/源码绑定、C4原始inspect/停止命令/退出码、C5完整源字节与stderr，附排除自身的MANIFEST。完整包保留，摘录不替换原件。

## 本人真实矩阵

| 场景 | job | trace | 状态 |
|---|---|---|---|
| normal | `job-aa20b0af94524337ba35ecf951823a2c` | `trace-3fa369e8ee694087a57379c2b408d276` | PASS |
| C4 | `job-7cb2ad1fc6984ae289be793f69758727` | `trace-3be602c6488a46208ef2e14e85bcee80` | EXPECTED_TIMEOUT_VERIFIED |
| 恢复正常 | `job-cffaec1e0cbf4f9c9f911a485ae63f6a` | `trace-debc02b3d2a94b1dbb57df972eaf9490` | PASS |
| C5 | `job-9dded64c61b54ca4b381031ba6dd9d45` | `trace-9014e5cd22b448868845ed535218df6d` | PASS |

正常链路：基线full无MISSING，target full检出main.o→config.h、helper.o→extra.h；incremental原payload/信封哈希与MDFixer请求一致。只在两个目标补依赖；HEADERS = unused.h、$(HEADERS)、所有配方及其他源文件字节保留。正确patch五项检查全部通过，最终full无MISSING。

C4：真实docker start --attach预算1秒超时；daemon inspect由Running=true变为false，按唯一label核验后仅停止/删除本任务容器，ps原件为空。清理观察时间2026-11-23T06:49:45.557635+00:00（北京时间14:49:45）；恢复正常任务是另一个job，容器创建时间晚于清理，最终通过。验证范围是worker超时，不代表BuildKit构建取消或当前实时服务器状态。

C5：原始git apply stderr为No valid patches in input；accepted=false、rollback=true。全部10份源文件前后原字节及Git状态一致；同job正确patch对照通过，只改变Makefile，最终无MISSING。错误patch拒绝属于预期负例。

## 镜像实际贯通

编排镜像 `sha256:cf313aa1a28bbff8e9727d7f5c8217819ec2da3d7cdffc9ab55553a2464b622a`。DRAFT成功镜像分别为：

- normal：`sha256:3549cee8177407e632992d01cf3c3768790e850b8d36d07f9a7b34fdfdc840fe`
- C4：`sha256:ee16ed51726898a29bba6328c569751152cdf494617d5ecc2d1ac8ab0be9158c`
- 恢复正常：`sha256:c254b91f01a214ecb20965edbfacc52074fa9875b4b7a52093c9b5b2bbb50d6b`
- C5：`sha256:f0a0f28f3a24daeb6e24377a0d285bdf17a94023dc2acf026cbf632a831ba0bd`

19次正常返回的worker执行（包含C5有效拒绝响应）及另1次真实超时均有原件。逐条核对实际container.Image、容器退出码、执行代码哈希、复制源码及镜像/work内源码哈希；full/scan/validate均在对应不可变镜像中执行，缺工具不回退编排器。

## 验证、历史与边界

本人服务器Linux 76项测试全部通过、无skip。本地此前Windows76项中75通过/1平台skip、双版本GCC/12功能用例和6项扫描回归原件保留，不混记为服务器用例。下载复核5240个断言包含路径/逐文件哈希与业务证据，不称为5240个独立实验。

早期Windows测试隔离/换行问题、CI动态表达式误报及快照属性问题均保留失败记录和修复历史。PR40固定dd35a439f8fb67f5e4d8267cff54239a6ceaac54已Approve：https://github.com/ma058/2026-Devops-B13/pull/40#pullrequestreview-6017306734 。本PR保持Draft：https://github.com/ma058/2026-Devops-B13/pull/42 。

A13 v2原件恢复、候选及源历史哈希已核验；三层profile绑定的新报告、A13对B项目的新运行/C5、双方字段与时窗待回签。tomlc99旧toml.o范围不等于全项目MD0。本轮是本人B13项目E13–E14验证，不重做E11–E12，不替代跨组验收。

历史CI曾因全分支--history扫描命中测试假密钥字面量而失败，失败原件保留。证据提交5e697e2a3f519fb03dde933321bd22440e6151d4的10项CI已全部通过。收到成员3协调意见后，又将四处动态表达式改名/拆行：导出blob、容器nonce、认证expected_auth、配置auth_file与分离env格式化；保持认证、清理标签、私有文件权限和导出拦截语义。四个文件使用未经AST豁免的原始正则也无命中。已保留精确AST历史识别；单纯删除当前表达式不能消除旧667bc445历史命中，没有force push或关闭门禁。新head需核对CI及成员3Review，不能以旧head或个人PASS替代。

AI协助实现、原件复核、可重放核验脚本与报告；服务器实际执行者为本人，AI本轮仅读取下载原件，没有连接或重跑服务器。
