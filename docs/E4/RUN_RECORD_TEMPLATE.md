# B13 E4 个人运行记录模板

> 每名成员复制一份并以 GitHub 身份或成员编号命名。只填脱敏信息，不填写公网 IP、账号密码、SSH 指纹、`.env` 内容、Token 或 API Key。

## 基本信息

- 执行人：
- GitHub 身份：
- 学号目录：`/root/<学号>/draft`
- 执行日期：
- 源码完整 SHA：
- 成功证据目录：`work/<时间>/`
- 对应分支：
- 对应 PR：

## 环境自检

- [ ] `make doctor` 通过
- [ ] `env.json` 的 `problems` 为空
- [ ] Git 身份为本人学号
- [ ] 资源警告：无 / 有，说明：

## 构建结果

- [ ] `make build` 通过
- 基础镜像 digest 核验：一致 / 不一致
- 镜像 ID：只记录必要的短标识，不附带私密环境信息
- `toolchain.lock` 关键版本：
- 构建异常与处理：

## 测试与冒烟

- [ ] `test.log` 显示 `4 passed`
- [ ] `smoke.json.docker_server` 有版本值
- [ ] `smoke.json.build_exit_code` 非 0
- [ ] `smoke.json.make_error_line` 含 `make: not found`
- [ ] `smoke.json.passed` 为 `true`
- 说明：失败的内层构建是预期样例，`passed: true` 表示 DRAFT 正确识别并记录该失败。

## 密钥检查

- [ ] 完整 `make all` 的 `secret-scan.txt` 通过
- [ ] `git ls-files .env` 没有输出
- [ ] 假 Key 第一次扫描被拒绝
- [ ] 删除假文件后第二次扫描通过
- [ ] 工作区没有残留 `leak-demo.txt`

## 与其他成员对照

- 对照成员：
- 源码 SHA：一致 / 不一致
- 工具版本：一致 / 不一致
- 单元测试结论：一致 / 不一致
- 冒烟结论：一致 / 不一致
- 密钥扫描结论：一致 / 不一致
- 允许差异：镜像 ID / 耗时 / 日志行数 / 其他
- 非预期差异及处理：

## 最终结论

- [ ] 本次运行满足 E4 验收标准
- [ ] 报告未包含任何凭据或真实密钥
- [ ] 原始 `work/` 仍保持 Git 忽略
