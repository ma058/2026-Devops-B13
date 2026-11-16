# 成员一复审补充：最终测试版本与证据

日期：2026-11-13。记录人：马宇航（241880054），Review 对象：成员三 PR #29，代码提交 `c0760c43204f4a784ca96125a4698e3bdd407547`。这是负责人复验，不冒充成员三本人重新执行。

## 版本与哈希更正

个人报告早期修复稿登记 `ff78b184ba4afb390a6fbba3a540c704eb8ca2965422e76f01a0269090755e2f`，该值与当前提交中的 `test_member3.py` 不同。本次未取得该旧字节文件用于版本映射，故不把旧值当作当前提交的运行证明，也不改写旧记录为后来SHA。

当前Git blob、LF文件及本次实际Linux运行文件均为：

```text
0ba19b2002dfeaf9bfc484521107c335c579975021d500bc029e3a73052d0054
```

可使用固定版本比较管线未变：`git diff 3abcc143d576b9a94f63ff2aa3acb6e3a48571eb c0760c43204f4a784ca96125a4698e3bdd407547 -- labs/e11e12/pipeline.py labs/e11e12/server.py`。不要再依赖已删除的 `student/241880115/e11-e12-fix` 分支名。

## 负责人独立复验

- 本机在临时ROOT执行新增12项，全通过；无关RUNNING状态字节不变，HTTP结束后监听关闭。
- 分别移除目录范围和.git防护的内存变体，均使对应拒绝用例失败，证明实际哨兵有判别力；未修改源码文件或真实API任务目录。
- 服务器隔离目录 `/root/241880054/pr29-review-20261113`，源码为上述c0760c4；镜像 `course-e11e12:241880054`，ID `sha256:bd6407d706b8a3174a5444e1363cb0432f3e2eae70dcb0a36a7d1c1e0cb5afad`。源码只读、禁网、无Docker socket，UID10001运行。
- 命令：`python3 -m unittest discover -s labs/e11e12 -p 'test_*.py' -v`，**50/50通过，无跳过，退出码0**。未重新运行成员三的旧E11/E12构建产物。
- 复验归档：`B13_PR29_reviewer_retest_20261113.tar.gz`，SHA-256 `4bef8b6c3a68b28d0b4f42a8db2b46d133041747fe22cf2f14b4281eef8aa853`；包含源码版本、测试文件hash、镜像ID、完整测试日志及退出码，随负责人2026-11-13复审交付包提供。
- CSV全部7行均10列；旧11/49项段落仅描述首轮版本，当前为12/50项。

## CI索引

以下均对应代码head c0760c4、当时base公共分支；改base/同步main后须重新核对最终检查，不能沿用旧base结果作最终合并依据。

- [E11–E12 PR run 42785855762](https://github.com/ma058/2026-Devops-B13/actions/runs/42785855762)
- [E7 PR run 42785855712](https://github.com/ma058/2026-Devops-B13/actions/runs/42785855712)
- [E8–E10 PR run 42785856042](https://github.com/ma058/2026-Devops-B13/actions/runs/42785856042)

首轮原件 `member3-241880115-e11e12-evidence-20261110.tar.gz` 及SHA `068f7b79f19724f216f7172ba4cefd99575626afd1e1e6918f331ddbc4b73e68` 继续保留。负责人本次测试归档与成员三首轮原件分别登记，不覆盖对方贡献或历史运行。
