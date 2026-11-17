"""Append verified real-project results, preserving prior personal documents."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from run_member2_real_project import ROOT, PHASH, git, require, verify_result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('formal', 'http', 'regressions', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    require(not git('status', '--porcelain'), 'Save code changes before updating documents')
    head = git('rev-parse', 'HEAD')
    formal = json.loads((a.formal / 'summary.json').read_bytes())
    http = json.loads((a.http / 'summary.json').read_bytes())
    require(formal['status'] == http['status'] == 'PASS' and formal['source_commit'] == http['source_commit'] == head, 'Passed current-source evidence required')
    require(not (a.formal / 'failure.json').exists() and not (a.http / 'failure.json').exists(), 'A run has a retained failure')
    require(json.loads((a.http / 'server-stopped.json').read_bytes())['returncode'] is not None, 'Own HTTP server not stopped')
    for mode, ops in [('e11-b', ['validate', 'full']), ('e12', ['full', 'scan', 'scan', 'full', 'validate', 'full']), ('consumer', ['validate', 'full'])]:
        verify_result(a.formal / mode, ops)
    verify_result(Path(http['evidence']), ['full', 'scan', 'scan', 'full', 'validate', 'full'])
    require((a.regressions / 'source-commit.txt').read_text().strip() == head, 'Regression source differs')
    regression = {}
    for suite in ('e11e12', 'e8e10'):
        report = json.loads((a.regressions / suite / 'summary.json').read_bytes())
        require(report['status'] == 'PASS' and report['tests_run'] > 0 and not any(report[k] for k in ('skipped', 'failures', 'errors')), 'Regression not fully passed: ' + suite)
        for name, digest in report['test_sha256'].items():
            require(hashlib.sha256((ROOT / 'labs' / suite / name).read_bytes()).hexdigest() == digest, 'Test changed: ' + name)
        regression[suite] = report['tests_run']
    out = a.out.resolve()
    require((ROOT / 'work').resolve() in out.parents and not out.exists(), 'Use a new work/ document backup OUT')
    out.mkdir(parents=True)
    docroot = ROOT / 'docs/students/241880091/e11-e12'
    names = ['个人报告.md', 'ADR.md', 'AI_USAGE.md']
    title = '\n\n## 本人真实 tomlc99 适配与验收补充\n\n'
    for name in names:
        path = docroot / name
        require(path.is_file() and title.strip() not in path.read_text(encoding='utf-8'), 'Document absent or section already installed: ' + name)
    facts = (f'本次执行代码 SHA：`{head}`。profile canonical SHA256：`{PHASH}`。\n\n'
             f'E11–E12 回归 {regression["e11e12"]} 项、E8–E10 回归 {regression["e8e10"]} 项，均无跳过/失败/错误。'
             f'本人真实 E11-B、E12、独立消费及 {formal["rejection_cases"]} 类拒绝检查通过。'
             'E11-B 固定报告由本人依据已核验 C1 建立，明确不冒充 A13 原始 incremental 报告；'
             '独立消费保留本次 E12 两份原始报告字节及其 SHA256。\n\n'
             f'E12 DRAFT：`{formal["runs"]["e12"]["image_id"]}`；HTTP DRAFT：`{http["checked"]["image_id"]}`。'
             'full/scan/validate/recheck 的真实容器镜像、工具版本、worker代码哈希和退出码见原始 execution.json。'
             '新镜像包含 git/strace，不是原 A13 de2ea79e 镜像；没有静默回退编排器。\n\n'
             f'本人 loopback 8082 job：`{http["job_id"]}`，完成 POST、轮询、原始工件下载/哈希核对、同键幂等及 409 冲突。'
             '此结果不是 A13 客户端正式跨机联调，也不代表共享 8081 已部署本次代码。\n\n'
             '**验收范围仅 toml.o。** 保留全量 findings 中的 `MISSING(toml_json,toml.h)`；不能写成全项目零缺失。'
             '头文件注释变更通过真实编译器 exec/argv 与对象更新时间证明重编译，不要求对象哈希改变。\n\n'
             f'证据路径：formal `{a.formal}`；HTTP `{a.http}`；回归 `{a.regressions}`。\n')
    adr = ('决策：新增显式版本化的受限 tomlc99 release profile，教学逻辑继续使用原入口默认分支。'
           '只有已审计 Makefile 的 toml.o 依赖行允许加项，其余字节和配方必须不变；不引入通用 Makefile 重写器。'
           '两入口、worker 和报告绑定同一 canonical hash，拒绝未知字段、外部 flags 覆盖及错误版本。'
           '缓存键包含编译器身份/版本、有序有效 flags、profile、对象映射、源码与 Makefile 字节。'
           '代价：其他项目或 Makefile 布局须单独审计并版本化；当前真实项目全量残留仍明确开放。\n\n' + facts)
    ai = ('AI 协助分析收到的材料、实现 profile/执行驱动/测试、编写可复制命令。'
          '本地 Windows 契约测试和服务器实际容器实验分别记账；Windows 符号链接用例曾跳过，未当成正式门禁通过。'
          '本节由脚本读取本人实际 summary、校验当前源码与报告工件后生成；收到的成员一、成员三、A13 日志不计成本人执行。'
          '仍须人工核对范围、执行 SHA、镜像 ID、原始证据与本次最终提交；未授权自动合并。\n\n' + facts)
    additions = dict(zip(names, [facts, adr, ai]))
    for name in names:
        path = docroot / name; shutil.copyfile(path, out / name)
        path.write_bytes(path.read_bytes() + (title + additions[name]).encode('utf-8'))
    (out / 'evidence-index.json').write_bytes((json.dumps({'source_commit': head, 'formal': formal, 'http': http, 'regressions': regression}, ensure_ascii=False, indent=2) + '\n').encode())
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print('REAL_DOCUMENT_UPDATE=PASS\nDOCUMENT_BACKUP=' + str(out))


if __name__ == '__main__': raise SystemExit(main())
