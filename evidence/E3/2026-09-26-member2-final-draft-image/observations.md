# 运行证据

- 格式：B13 草案 0.1
- 结果：PASS
- 开始：2026-09-26T06:07:40.665224+00:00
- 结束：2026-09-26T06:07:43.488722+00:00
- HEAD：12d25b67f30c78ae1c9205f505799cf4ed0b6bb0
- dirty：False
- 未提交文件以 summary.json 的 file_sha256 绑定，HEAD 不代表全部运行源码。
- 环境、命令、退出码与原始输出见 summary.json、verify.log 和分流日志。

Existing local image recheck only; current fixture rebuilt in a fresh directory. Dockerfile rebuild and broken-image test are outside this recheck scope. No LLM or A13 EChecker executed; image is not published to a registry.

- PASS image_identity: sha256:18135e3075fd8211e4b2feeed0c972958835076339907782dc8c56e53940359b
- PASS hello_run_1: {'exit_code': 0, 'stdout': 'hello E3\n'}
- PASS hello_run_2: {'exit_code': 0, 'stdout': 'hello E3\n'}
- PASS current_fixture_clean_build: {'exit_code': 0, 'stdout': 'rm -f hello\ngcc -O2 -Wall -Wextra main.c -o hello\nhello E3\n'}
- PASS container_metadata: 0
