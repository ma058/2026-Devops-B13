# 运行证据

- 格式：B13 草案 0.1
- 结果：PASS
- 开始：2026-09-24T11:19:52.603923+00:00
- 结束：2026-09-24T11:21:18.253146+00:00
- HEAD：b6f47cdfb45665b1d0da184c64e52e4157245550
- dirty：True
- 未提交文件以 summary.json 的 file_sha256 绑定，HEAD 不代表全部运行源码。
- 环境、命令、退出码与原始输出见 summary.json、verify.log 和分流日志。

人工 DRAFT 基线；未调用 LLM 或 A13。预期 broken 构建失败按错误原因判定。镜像保留用于复验。

- PASS broken_missing_make: {'exit_code': 1, 'diagnostic_found': True}
- PASS reference_build: 0
- PASS image_identity: sha256:18135e3075fd8211e4b2feeed0c972958835076339907782dc8c56e53940359b
- PASS hello_run_1: {'exit_code': 0, 'stdout': 'hello E3\n'}
- PASS hello_run_2: {'exit_code': 0, 'stdout': 'hello E3\n'}
- PASS clean_build: {'exit_code': 0, 'stdout': 'rm -f hello\ngcc -O2 -Wall -Wextra main.c -o hello\nhello E3\n'}
- PASS container_metadata: 0
