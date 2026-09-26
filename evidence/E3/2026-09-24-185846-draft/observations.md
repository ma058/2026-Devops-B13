# 运行证据

- 格式：B13 草案 0.1
- 结果：FAIL
- 开始：2026-09-24T10:58:47.007676+00:00
- 结束：2026-09-24T10:58:53.273255+00:00
- HEAD：b6f47cdfb45665b1d0da184c64e52e4157245550
- dirty：True
- 未提交文件以 summary.json 的 file_sha256 绑定，HEAD 不代表全部运行源码。
- 环境、命令、退出码与原始输出见 summary.json、verify.log 和分流日志。

人工 DRAFT 基线；未调用 LLM 或 A13。预期 broken 构建失败按错误原因判定。镜像保留用于复验。

- PASS broken_missing_make: {'exit_code': 1, 'diagnostic_found': True}
- FAIL reference_build: 1
- NOT_RUN container_checks: reference build unavailable
