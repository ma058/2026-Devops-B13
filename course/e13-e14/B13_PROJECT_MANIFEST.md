# B13 交换项目 b13-level-v1

2026-11-23；提供者及本地执行者：成员2 / 241880091 / Lacrym1ra。A13 241870063 接收/新运行待回签；组内 Reviewer 为成员3。

基于公共 dd35a439f8fb67f5e4d8267cff54239a6ceaac54 的受控 C/Make mixed 样例，保留来源。独立增加 CLI 整数解析、负数归零、非法输入/溢出拒绝、self-test、make check；target 增加 extra.h 的 MAX_LEVEL=10 上限及测试。这是实际演进的课程衍生项目。

- base `cb6545b3e8eddda5bec89b12ee390ae5e930f822`：输入12输出13。
- target `5cfaf2014db78635b61d88b62760481834a344d5`：输入12输出11；负数输出1；非法参数退出2。
- 两版无参数均 stdout `1` + LF、退出0；`./app --self-test` 输出 `SELF_TEST=PASS` + LF。
- C0是C1祖先；`projects/b13-level-v1/project.bundle` 包含双提交，支持离线恢复。
- target预期缺失 main.o → config.h、helper.o → extra.h。保留 HEADERS=unused.h 与 $(HEADERS)，仅补对应目标、不改配方或冗余依赖。
- 命令：`make clean`、`make app`、`make check`、`./app`。flags `-O0`。
- 工具：Python3/Git/GCC/Make/strace/Docker。候选900秒；worker默认120秒、最大600秒，1 CPU/512 MiB/256 PID。
- candidate SHA `8b26c9034b1535b243b99cb43361ad2d44625473c902e0f5f7a78ffbb678fd4a`；bundle SHA `393bf653106c6c7d37fc64d6d4b8d6c37e9053a7ec7c31674599a7237161a267`。
- profile规范化SHA `f0367b454aff9cb0a5304e3e3330b61d4bbd01c3f19069eaf5930a1664d3733b`；算法：`json.dumps(profile, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')` 的SHA256，无BOM/末尾换行、保留数组顺序、包含id。文件字节哈希另算。

候选基于本项目 Dockerfile.broken，参考A13工具安装方式，固定Python基础镜像，COPY/构建/测试绑定B13新源码。完整 image_id 已由本人服务器实际构建产生，四个job各自绑定，详见成员2报告及image-source-bindings.json。worker检查镜像 /work 的target源码和复制到沙箱的base/target源码，记录实际image/container与哈希。

本地 Windows 两版 GCC 编译和12程序用例通过（stdout原件为CRLF）；Linux个人正式矩阵已在99f2c7abd1cad161cbfa4affe8d2109568d948ab通过：正常、C4、新job恢复、C5及76项测试；原件SHA为4157bd945a4fbd5bf3e87a935d0fb38a90fac77d478f97873e6101ef3f6e4707，详见成员2报告。闭集只支持登记目标、profile和Makefile模板；未知布局/配方/flags拒绝。B profile仅接入新member2-e14-1，旧E11/E12 pipeline未宣称通用兼容。

A13候选616字节 SHA eb506f89177da2eb5736b7a62336b0f2d156e81feca04de1ef5747ce27f7eb8a 已复核；v2ZIP、历史、result/信封原件均复核，保留shallow边界。旧tomlc99 profile仅toml.o范围；完整full findings仍保留toml_json→toml.h，不能据此宣称全项目MD0。A13三层result/信封/payload缺profile_sha256，需确认字段后由其新任务生成，不改旧字节。A13对B项目新运行/C5、字段冻结与时窗待回签。
