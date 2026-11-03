"""成员3 自主测试（E8-E10，B 轨道）。

等待期设计草案；公共导入 PR #21 合并后部署至 student/241880115/e8-e10 分支
labs/e8e10/test_member3.py。与 test_profile.py 既有用例的差异：
- 既有 UNSAFE_PATH 用例只测 `../outside.h` 目录穿越；本文件另测绝对路径与非法字符。
- MISSING_INPUT 无既有用例，本文件独立设计。
- UNSUPPORTED_DECLARATION / UNSUPPORTED_MACRO 无既有用例，本文件区分声明解析
  （scan→declarations）与候选生成（patch）两个入口分别构造。
- E10 既有示例为编译失败拒绝；本文件按任务书要求构造"合法、可应用、能构建、
  功能正确、却仍未修复 MD"的候选，证明构建成功不足以接受。

独立预期推导（写入报告用）：
- MISSING_INPUT：lab.patch 在 UNSAFE_PATH 之后检查 (p/dependency).is_file()，
  报告指向项目内不存在文件时应抛 ValueError('MISSING_INPUT')，且发生在任何
  Makefile 写入之前，源字节必保持。
- UNSAFE_PATH 绝对路径：Path(d).is_absolute() 命中；非法字符：不匹配
  [\\w./-]+ 或含 NUL。两者都在写文件之前触发。
- UNSUPPORTED_DECLARATION：declarations() 对宏做最多 8 轮展开后仍残留 $ 即拒绝，
  未定义变量引用属于声明解析入口（经 scan 触发）。
- UNSUPPORTED_MACRO：patch() 中目标行整体恰为单个 $(VAR) 引用且全文无 VAR
  定义行时触发，属于候选生成入口；因该 Makefile 无法通过 scan，报告须人工构造
  （commit 字段填真实 HEAD 以通过 STALE_REPORT 前置，findings 人工给出）。
- E10 能构建仍有 MD：候选仅给 Makefile 添加注释行，不增加 config.h 声明。
  patch_applies/build/test 三项应通过，但 header_change 为 False（config.h 改
  VALUE 2 后 main.o 不重编译，程序输出仍为 1），no_missing 为 False（重检仍有
  MISSING config.h），故 accepted=False、rollback=True、source_unchanged=True。
"""
import tempfile
import unittest
from pathlib import Path

from lab import fixture, patch, scan, validate


def _makefile_bytes(p):
    return (p / 'Makefile').read_bytes()


class StudentMember3E8(unittest.TestCase):
    """E8 自主：异常输入明确拒绝，源 Makefile 字节保持。"""

    def test_missing_input_rejected_and_source_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p)
            report = scan(p)
            before = _makefile_bytes(p)
            # 输入组合：报告指向项目内不存在的头文件（既有用例未覆盖）
            report['findings'] = [{'type': 'MISSING', 'target': 'main.o',
                                   'dependency': 'ghost.h'}]
            with self.assertRaisesRegex(ValueError, 'MISSING_INPUT'):
                patch(p, report)
            self.assertEqual(_makefile_bytes(p), before)

    def test_absolute_path_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p)
            report = scan(p)
            before = _makefile_bytes(p)
            # 变体：绝对路径命中 is_absolute()，先于任何文件访问
            report['findings'] = [{'type': 'MISSING', 'target': 'main.o',
                                   'dependency': '/etc/passwd'}]
            with self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
                patch(p, report)
            self.assertEqual(_makefile_bytes(p), before)

    def test_illegal_characters_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p)
            report = scan(p)
            before = _makefile_bytes(p)
            # 变体：非法字符不匹配 [\w./-]+ 白名单
            report['findings'] = [{'type': 'MISSING', 'target': 'main.o',
                                   'dependency': 'config.h; rm -rf /'}]
            with self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
                patch(p, report)
            self.assertEqual(_makefile_bytes(p), before)

    def test_outside_sentinel_never_touched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / 'sentinel.h'
            sentinel.write_text('#define SENTINEL 1\n')
            p = root / 'sample'
            fixture(p)
            report = scan(p)
            before = _makefile_bytes(p)
            # 目录穿越被拒绝时不应访问范围外哨兵文件（内容保持即未读取或未改动）
            report['findings'] = [{'type': 'MISSING', 'target': 'main.o',
                                   'dependency': '../sentinel.h'}]
            with self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
                patch(p, report)
            self.assertEqual(_makefile_bytes(p), before)
            self.assertEqual(sentinel.read_text(), '#define SENTINEL 1\n')


class StudentMember3E9(unittest.TestCase):
    """E9 自主：不支持的声明形式以确定错误拒绝，不放宽为任意异常。"""

    def test_unsupported_declaration_via_scan_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p)
            # 声明解析入口（scan→declarations）：未定义变量 8 轮展开后仍残留 $
            text = (p / 'Makefile').read_text().replace(
                'main.o: main.c unused.h', 'main.o: $(UNDEFINED_VAR) main.c unused.h')
            (p / 'Makefile').write_text(text)
            # 构造完不支持状态后再取基准：拒绝动作（scan）本身不得再改动文件
            before = _makefile_bytes(p)
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_DECLARATION'):
                scan(p)
            self.assertEqual(_makefile_bytes(p), before)

    def test_unsupported_macro_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'sample'
            fixture(p)
            # 候选生成入口（patch）：目标行整体为单宏引用但宏无定义行
            text = (p / 'Makefile').read_text().replace(
                'main.o: main.c unused.h', 'main.o: $(MYDEPS)')
            (p / 'Makefile').write_text(text)
            before = _makefile_bytes(p)
            # 人工构造报告：commit 为真实 HEAD（通过 STALE_REPORT 前置），不冒充 scan 产物
            import subprocess
            head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=p,
                                  text=True, capture_output=True, check=True).stdout.strip()
            report = {'commit': head,
                      'findings': [{'type': 'MISSING', 'target': 'main.o',
                                    'dependency': 'config.h'}]}
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_MACRO'):
                patch(p, report)
            self.assertEqual(_makefile_bytes(p), before)


class StudentMember3E10(unittest.TestCase):
    """E10 自主：能构建、功能正确、却仍有 MD 的候选必须拒绝，源字节保持。"""

    def test_buildable_candidate_with_md_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'sample'
            fixture(p)
            before = _makefile_bytes(p)
            # 构造候选：仅给 Makefile 添加注释行，不增加 config.h 声明
            original = (p / 'Makefile').read_text()
            cosmetic = '# cosmetic change only\n' + original
            candidate = root / 'cosmetic.patch'
            import difflib
            candidate.write_text(''.join(difflib.unified_diff(
                original.splitlines(True), cosmetic.splitlines(True),
                fromfile='a/Makefile', tofile='b/Makefile')))
            result = validate(p, candidate, root / 'validation')
            # 逐项记录实际值：可应用、可构建、初始功能正确
            self.assertTrue(result['checks']['patch_applies'])
            self.assertTrue(result['checks']['build'])
            self.assertTrue(result['checks']['test'])
            # 但头文件变化检查失败（main.o 不重编译，程序输出仍为 1）
            self.assertFalse(result['checks']['header_change'])
            # 重检仍发现 MISSING config.h
            recheck = scan(root / 'validation' / 'sandbox')
            self.assertIn('config.h', [f['dependency'] for f in recheck['findings']
                                       if f['type'] == 'MISSING'])
            self.assertFalse(result['checks']['no_missing'])
            # 结论：构建成功不足以接受
            self.assertFalse(result['accepted'])
            self.assertTrue(result['rollback'])
            self.assertTrue(result['source_unchanged'])
            # 源 Makefile 与验证前逐字节相同（仅验证 Makefile，不扩张到全项目声明）
            self.assertEqual(_makefile_bytes(p), before)


if __name__ == '__main__':
    unittest.main()
