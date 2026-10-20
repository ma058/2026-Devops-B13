# 发给成员二：E5–E7 工作安排

你负责 E6 的实现审查、证据校验扩展、独立复验及双候选对照。请使用自己的 GitHub 身份提交代码、报告和 PR，不只交文字总结。

## 已经准备好的内容

- 仓库：<https://github.com/ma058/2026-Devops-B13>
- 成员1基线分支：`member1/e5-e7-bootstrap`。先 Review 该分支 PR，确认来源、网络适配与 E5 证据后 Approve；由成员1合并。
- 实验目录：`labs/B-draft`，不要在仓库根目录执行 E4 的旧 Makefile。
- 教学基线已通过 24 项服务测试；成员1已验证 E5 修复、E6 两轮构建与 E7 全部场景。
- 公共实际运行代码 SHA：`e54b1adc9fe81e6c2537beb5f480baabd2ed4b0f`；后续文档提交不改变该次运行证据。
- 你的工作分支：`member2/e6-evidence-validation`；报告：`docs/E5-E7/MEMBER2_REPORT.md`。

## 1. 独立准备

以下在课程 Linux 服务器运行，先与成员3约好时段，避免同时构建。目录已存在时先检查，不能覆盖已有实验。

```bash
mkdir -p /root/241880091
cd /root/241880091
git clone https://github.com/ma058/2026-Devops-B13.git e5-e7-b13
cd e5-e7-b13
git config --local user.name 241880091
git config --local user.email '241880091@localhost'
git fetch origin
# 基线 PR 已合并时从 origin/main 创建；若尚未合并，将起点改为 origin/member1/e5-e7-bootstrap
git switch -c member2/e6-evidence-validation origin/main
git rev-parse HEAD
git status --short
cd labs/B-draft
python3 scripts/lab_cloud.py doctor
python3 scripts/lab_cloud.py build --image b13-draft:241880091-e567 --out work/m2-build-01 --build-timeout 1200
```

预期构建和 pytest 成功，未修改服务测试前为 24 passed。镜像名必须使用自己的学号。若网络错误尚未到达 RUN make，保存原日志并处理网络，不写成缺 make 复现成功。

## 2. E6 独立复验与双候选对照

```bash
python3 scripts/lab_cloud.py e6 --image b13-draft:241880091-e567 --candidate fixtures/b13-candidates/error-driven.Dockerfile --out work/m2-e6-error-01 --build-timeout 600
python3 scripts/verify_e6_b_evidence.py --run-dir work/m2-e6-error-01/evidence
python3 scripts/lab_cloud.py e6 --image b13-draft:241880091-e567 --candidate fixtures/b13-candidates/context-driven.Dockerfile --out work/m2-e6-context-01 --build-timeout 600
python3 scripts/verify_e6_b_evidence.py --run-dir work/m2-e6-context-01/evidence
```

每次退出后立即记录实际退出码。预期两轮分别为 MISSING_MAKE / 构建成功，第二轮镜像 ID 必须等于运行命令最后一个参数，运行退出 0、输出 hello E3。对比安装包、构建耗时和镜像大小时如实说明缓存命中，不能用两次样例运行推断模型优劣或论文成功率。

候选和原始回复已由成员1保存，来源见 provenance.json。你的贡献是独立构建、比较和审查，不把这些候选署名为你新生成的模型回复。若另取候选，要另存自己的提示、完整回复、日期和选择原因。

## 3. 必须完成的自主代码修改

阅读 `services/draft/draft/autobuild.py`，解释以下字段的产生位置：failure_class、candidate_sha256、input_sha256、image_id、verification、status。

负责增强 `scripts/verify_e6_b_evidence.py`。当前实现只逐项核对已列出的 input_sha256，缺少“清单完整性”核对：空清单或删掉某个条目可能避开完整输入校验。请先写能暴露该问题的测试，再实现修复：

1. input_sha256 必须是非空映射，拒绝非法路径和非法摘要。
2. 记录的路径集合必须与 project 内实际文件集合一致，拒绝遗漏条目与额外文件。
3. 验证命令必须按保存的镜像 ID 禁网运行，拒绝删除或更改 --network none 的证据。

在 `labs/B-draft/tests/member2/` 新增至少 3 个独立测试：删除一个输入清单条目、添加额外输入文件、篡改运行网络参数。保留一份合法证据能通过的测试，避免校验器变成“一律拒绝”。

测试可在临时目录复制最小结构化证据；不得修改原始 work 证据。说明这些测试属于保存证据一致性测试，真实 Docker 执行另有日志。

## 4. 修改后复验

```bash
python3 -m unittest discover -s tests/member2 -v
python3 scripts/verify_e6_b_evidence.py --run-dir work/m2-e6-error-01/evidence
python3 scripts/verify_e6_b_evidence.py --run-dir work/m2-e6-context-01/evidence
python3 scripts/lab_cloud.py build --image b13-draft:241880091-e567 --out work/m2-build-02 --build-timeout 1200
python3 scripts/lab_cloud.py gate --image b13-draft:241880091-e567 --candidate fixtures/b13-candidates/error-driven.Dockerfile --out work/m2-e7-regression-01 --build-timeout 600
python3 scripts/secret_scan.py . --history --image b13-draft:241880091-e567
```

tests/member2 位于服务镜像之外，其测试数应单独报告，不自动加到“24 passed”。把测试命令发给成员3，由其加入 CI。实际新增服务测试时以实际数量为准。

## 5. 你的报告与 GitHub 提交

报告至少包含：本人身份、运行 SHA、服务镜像 ID、两类候选哈希、两轮退出码、程序输出、三个篡改负例、合法证据通过、gate 结果、源码字段说明、允许差异、原始证据目录。

代码与报告提交到自己的分支，PR 目标为 main，由成员3 Review：

```bash
cd ../..
git status --short
git add labs/B-draft/scripts/verify_e6_b_evidence.py labs/B-draft/tests/member2 docs/E5-E7/MEMBER2_REPORT.md
git diff --cached --check
git commit -m "feat(e6): validate complete input evidence and runtime isolation"
git push -u origin member2/e6-evidence-validation
```

请创建 PR，不要直接推 main。不要把 work 全部 git add；把原始证据打包下载，单独提供给成员1作为最终交付附件。每次实验用新 --out 目录。

## 6. 必须交流的事项

- **与成员1一致**：使用的基线 SHA、候选文件与来源、预计输出。遇到 FROM 或候选约束变化先说明。
- **与成员3交流**：新增校验器测试入口、门禁回归结果、文件修改范围和 CI 接入顺序。由你直接联系，不由成员1代传。
- **与 A13**：如做跨组互查，由你直接联系，交换仓库/实际 SHA/脱敏结果即可。本轮没有 A13 数据依赖；对方未回复不妨碍你的 E6 完成。

完成后回复成员1：PR 链接、最终提交 SHA、测试数量及结果、E6/gate 证据目录、原始证据压缩包、需要成员1处理的具体问题。
