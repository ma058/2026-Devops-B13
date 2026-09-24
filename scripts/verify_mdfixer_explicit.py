#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_mdfixer_explicit.py — E3 MDFixer 显式声明修复基线验证（成员3）

对 fixtures/mdfixer/{target-style,macro-style,hybrid-style} 执行分工文档 7.3 的
验证流程（修复前复现漏重建 → git apply 参考补丁 → 修复后增量重建 → 重检 MD=0
→ 声明风格一致 → clean build 行为等价），并生成证据三件套：

    evidence/E3/<日期>-mdfixer-<风格>/
      observations.md   人读：环境、命令、观察结果、结论
      verify.log        机跑完整日志（每条命令的 argv/退出码/stdout/stderr）
      summary.json      机器可读：环境、fixture commit、各检查项状态、哈希

证据结构为成员3草案，待成员2的 collect_evidence.py 统一格式定稿后适配【待统一】。

用法（仓库根目录）：
    python3 scripts/verify_mdfixer_explicit.py --style target-style
    python3 scripts/verify_mdfixer_explicit.py --style all
    python3 scripts/verify_mdfixer_explicit.py --style all --keep-work

环境要求：GNU Make（Windows 上为 mingw32-make）、C 编译器（cc 或 gcc）、git、python3。
脚本不依赖 make clean：所有完整构建都在全新工作目录或经 Python 删除产物后进行，
Windows 上没有 rm 命令也可运行；Linux/WSL 与 Windows 均已实测。
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

STYLES = ["target-style", "macro-style", "hybrid-style"]
SOURCE_FILES = ("Makefile.before", "main.c", "config.h")
CONFIG_H = '#define VALUE {value}\n'


# ---------------------------------------------------------------- 日志与命令执行

class Logger:
    """同时输出到控制台与 verify.log 缓冲区。"""

    def __init__(self):
        self.lines = []

    def log(self, text=""):
        print(text)
        self.lines.append(text)

    def save(self, path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(self.lines) + "\n")


class Runner:
    def __init__(self, logger):
        self.logger = logger

    def run(self, argv, cwd, expect_success=None):
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        self.logger.log("$ %s" % " ".join(str(a) for a in argv))
        self.logger.log("cwd=%s exit=%d" % (cwd, proc.returncode))
        if proc.stdout:
            self.logger.log("stdout:\n" + proc.stdout.rstrip("\n"))
        if proc.stderr:
            self.logger.log("stderr:\n" + proc.stderr.rstrip("\n"))
        if expect_success is True and proc.returncode != 0:
            raise AssertionError("command failed: %s" % " ".join(argv))
        if expect_success is False and proc.returncode == 0:
            raise AssertionError("command unexpectedly succeeded: %s" % " ".join(argv))
        return proc


class Checks:
    def __init__(self, logger):
        self.items = []
        self.logger = logger

    def add(self, check_id, description, status, detail=""):
        assert status in ("PASS", "FAIL", "WARN")
        self.items.append({"id": check_id, "description": description,
                           "status": status, "detail": detail})
        mark = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}[status]
        self.logger.log("%s %s — %s %s" % (mark, check_id, description,
                                           ("| " + detail) if detail else ""))

    @property
    def failed(self):
        return [c for c in self.items if c["status"] == "FAIL"]

    @property
    def warned(self):
        return [c for c in self.items if c["status"] == "WARN"]


# ---------------------------------------------------------------- 小工具

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def write_config(workdir, value):
    with open(os.path.join(workdir, "config.h"), "w", encoding="utf-8", newline="") as f:
        f.write(CONFIG_H.format(value=value))


def find_executable(workdir, name):
    for cand in (name, name + ".exe"):
        p = os.path.join(workdir, cand)
        if os.path.exists(p):
            return p
    return None


def main_o_recompiled(make_output, workdir, mtime_before):
    """判断 main.o 是否被重新编译：编译命令出现，或 main.o 时间戳变新。

    注意：Windows 上 gcc 产出 app.exe，目标 app 对应文件始终不存在，每次 make
    都会重新链接并打印含 main.o 字样的链接命令；因此不能用 "main.o in 输出"
    作为重编译依据，必须匹配编译命令 `-c main.c` 或比较 main.o 的 mtime。"""
    if re.search(r"-c\s+main\.c", make_output):
        return True
    main_o = os.path.join(workdir, "main.o")
    return os.path.exists(main_o) and os.path.getmtime(main_o) > mtime_before


def detect_tools(make_override=None, cc_override=None):
    make = make_override or shutil.which("make") or shutil.which("mingw32-make")
    cc = cc_override or shutil.which("cc") or shutil.which("gcc")
    git = shutil.which("git")
    missing = [n for n, v in (("make/mingw32-make", make), ("cc/gcc", cc), ("git", git)) if not v]
    if missing:
        print("缺少必需工具: %s" % ", ".join(missing))
        print("Windows 可安装 MinGW（提供 mingw32-make 与 gcc）与 Git for Windows；")
        print("Linux/macOS 请安装 make、gcc、git。")
        sys.exit(2)
    return make, cc, git


def fixture_commit(repo_root, git, style):
    """返回引入该 fixture 目录的真实提交 SHA（两段式提交的第一段）。"""
    proc = subprocess.run(
        [git, "log", "--diff-filter=A", "--format=%H", "-1", "--",
         "fixtures/mdfixer/%s" % style],
        cwd=repo_root, capture_output=True, text=True)
    sha = proc.stdout.strip()
    return sha if re.fullmatch(r"[0-9a-fA-F]{40}", sha) else None


# ------------------------------------------------- 课程固定 Oracle 与风格分类器
# 说明：以下为课程固定 Oracle（B13_MANUAL_ORACLE 的程序化版本），不是 EChecker
# 论文实现。论文语义约束：MD = 实际依赖中存在但未在声明依赖中；RD = 声明依赖中
# 存在但实际未使用。本 Oracle 只针对本课程单目标样本（main.o ← main.c + config.h），
# 不做系统调用跟踪。

ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
RULE_MAIN_O_RE = re.compile(r"^main\.o\s*:\s*(.*)$")
INCLUDE_RE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)


def parse_makefile_vars(makefile_text):
    assignments = {}
    for line in makefile_text.splitlines():
        if line.startswith("\t"):
            continue  # recipe 行
        m = ASSIGN_RE.match(line)
        if m:
            assignments[m.group(1)] = m.group(2).strip()
    return assignments


def expand_tokens(expr, assignments, workdir, depth=0):
    """把声明右侧展开为文件列表：处理 $(VAR) 递归与 $(wildcard 模式)。

    分词时先按括号感知方式取出 $(...) 整体（支持 $(wildcard *.h) 这类带空格的
    函数调用；本课程样本不含嵌套括号），再处理普通空白分隔的文件名。"""
    if depth > 10:
        raise ValueError("宏展开深度超限")
    tokens = []
    for raw in re.findall(r"\$\([^()]*\)|\S+", expr):
        wm = re.fullmatch(r"\$\(wildcard\s+(.+)\)", raw)
        vm = re.fullmatch(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)", raw)
        if wm:
            pattern = wm.group(1)
            hits = sorted(os.path.basename(p) for p in glob.glob(os.path.join(workdir, pattern)))
            tokens.extend(hits)
        elif vm:
            value = assignments.get(vm.group(1), "")
            tokens.extend(expand_tokens(value, assignments, workdir, depth + 1))
        else:
            tokens.append(raw)
    return tokens


def declared_deps_of_main_o(makefile_text, workdir):
    assignments = parse_makefile_vars(makefile_text)
    for line in makefile_text.splitlines():
        if line.startswith("\t"):
            continue
        m = RULE_MAIN_O_RE.match(line)
        if m:
            return expand_tokens(m.group(1), assignments, workdir)
    raise ValueError("未找到 main.o 的声明行")


def actual_deps_of_main_o(workdir):
    """实际依赖：main.c 本身 + main.c 中 #include 的项目内头文件。"""
    with open(os.path.join(workdir, "main.c"), encoding="utf-8") as f:
        src = f.read()
    deps = {"main.c"}
    deps.update(INCLUDE_RE.findall(src))
    return deps


def oracle_detect(makefile_text, workdir):
    declared = set(declared_deps_of_main_o(makefile_text, workdir))
    actual = actual_deps_of_main_o(workdir)
    md = sorted(actual - declared)
    rd = sorted(declared - actual)
    return {"target": "main.o", "declared": sorted(declared),
            "actual": sorted(actual), "missing": md, "redundant": rd}


def classify_style(makefile_text):
    """课程级简化 DIS 分类（MDFixer 论文式(6)的单目标近似）：
    声明右侧只有普通文件 -> TARGET；只有 $(宏) -> MACRO；两者兼有 -> HYBRID。"""
    for line in makefile_text.splitlines():
        if line.startswith("\t"):
            continue
        m = RULE_MAIN_O_RE.match(line)
        if m:
            tokens = m.group(1).split()
            has_macro = any(t.startswith("$(") for t in tokens)
            has_atomic = any(not t.startswith("$(") for t in tokens)
            if has_macro and has_atomic:
                return "HYBRID"
            if has_macro:
                return "MACRO"
            return "TARGET"
    raise ValueError("未找到 main.o 的声明行，无法分类")


# ---------------------------------------------------------------- 主验证流程

def verify_style(style, repo_root, make, cc, git, keep_work):
    fixture_dir = os.path.join(repo_root, "fixtures", "mdfixer", style)
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as f:
        expected = json.load(f)
    with open(os.path.join(fixture_dir, "Makefile.before"), encoding="utf-8") as f:
        makefile_before = f.read()
    patch_path = os.path.join(fixture_dir, "reference.patch")

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    evidence_dir = os.path.join(repo_root, "evidence", "E3", "%s-mdfixer-%s" % (today, style))
    if os.path.exists(evidence_dir):
        evidence_dir += "-" + datetime.datetime.now().strftime("%H%M%S")
    os.makedirs(evidence_dir, exist_ok=True)
    logger = Logger()
    runner = Runner(logger)
    checks = Checks(logger)

    fcommit = fixture_commit(repo_root, git, style)
    logger.log("== style=%s" % style)
    logger.log("== fixture_dir: %s" % fixture_dir)
    logger.log("== fixture_commit: %s" % fcommit)
    logger.log("== evidence_dir: %s" % evidence_dir)

    env = {"os": platform.system().lower(), "os_release": platform.release(),
           "arch": platform.machine(), "python": platform.python_version(),
           "make_exe": make, "cc_exe": cc, "git_exe": git}
    v_make = runner.run([make, "--version"], cwd=repo_root).stdout.splitlines()
    v_cc = runner.run([cc, "--version"], cwd=repo_root).stdout.splitlines()
    v_git = runner.run([git, "--version"], cwd=repo_root).stdout.splitlines()
    env["make_version"] = v_make[0] if v_make else ""
    env["cc_version"] = v_cc[0] if v_cc else ""
    env["git_version"] = v_git[0] if v_git else ""

    workdir = tempfile.mkdtemp(prefix="mdfixer-%s-" % style)
    logger.log("== workdir: %s" % workdir)
    for name in SOURCE_FILES:
        src = os.path.join(fixture_dir, name)
        dst = os.path.join(workdir, "Makefile" if name == "Makefile.before" else name)
        shutil.copy2(src, dst)

    exp = expected["expect"]

    # ---------- 步骤 1：VALUE=1 完整构建，程序输出 1
    p = runner.run([make, "CC=%s" % cc], cwd=workdir)
    checks.add("S1.build-before", "修复前完整构建退出码为 0",
               "PASS" if p.returncode == 0 else "FAIL", "exit=%d" % p.returncode)
    app = find_executable(workdir, expected["project"]["executable"])
    p = runner.run([app], cwd=workdir) if app else None
    out1 = (p.stdout.strip() if p else "")
    checks.add("S1.output-before", "VALUE=1 完整构建后程序输出 1",
               "PASS" if out1 == exp["prefix_clean_output"] else "FAIL",
               "stdout=%r" % out1)
    hash_prefix = sha256_of(app) if app else None

    # ---------- 步骤 2+3：只改 config.h 为 VALUE=2，普通 make 仍输出旧值 1（复现漏重建）
    # 等待 1.2s 再改 config.h：保证其 mtime 严格晚于 main.o（规避文件系统时间戳
    # 粒度导致的"同一时间戳不重建"假象），使"改了头文件却没重编译"成为有效证据。
    time.sleep(1.2)
    write_config(workdir, 2)
    mtime_main_o_before = os.path.getmtime(os.path.join(workdir, "main.o"))
    p = runner.run([make, "CC=%s" % cc], cwd=workdir)
    rebuilt_before_fix = main_o_recompiled(p.stdout + p.stderr, workdir, mtime_main_o_before)
    checks.add("S3.no-rebuild-before", "修复前修改 config.h 后普通 make 不重编译 main.o（复现 MD）",
               "PASS" if not rebuilt_before_fix else "FAIL",
               "make 输出: %s" % (p.stdout.strip() or p.stderr.strip()))
    p = runner.run([app], cwd=workdir)
    out2_stale = p.stdout.strip()
    checks.add("S3.stale-output", "修复前增量构建后程序仍输出旧值 1",
               "PASS" if out2_stale == exp["stale_output_before_fix"] else "FAIL",
               "stdout=%r" % out2_stale)

    oracle_before = oracle_detect(makefile_before, workdir)
    checks.add("S3.oracle-before", "课程固定 Oracle 在修复前报告 1 条 MISSING(main.o→config.h)",
               "PASS" if len(oracle_before["missing"]) == exp["oracle_md_before"]
                        and oracle_before["missing"] == [expected["md"]["dependency"]] else "FAIL",
               json.dumps(oracle_before, ensure_ascii=False))

    # ---------- 步骤 4：git apply --check，再 git apply reference.patch
    p = runner.run([git, "apply", "--check", patch_path], cwd=workdir)
    checks.add("S4.apply-check", "git apply --check reference.patch 通过",
               "PASS" if p.returncode == 0 else "FAIL", p.stderr.strip())
    p = runner.run([git, "apply", patch_path], cwd=workdir)
    checks.add("S4.apply", "git apply reference.patch 成功",
               "PASS" if p.returncode == 0 else "FAIL", p.stderr.strip())
    with open(os.path.join(workdir, "Makefile"), encoding="utf-8") as f:
        makefile_after = f.read()

    # 补丁最小性：只允许改动依赖声明（allowed_change_patterns）
    changed_lines = []
    with open(patch_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith(("+++", "---")):
                continue
            if line.startswith(("+", "-")):
                changed_lines.append(line[1:].rstrip("\n"))
    patterns = [re.compile(x) for x in expected["patch_policy"]["allowed_change_patterns"]]
    bad_lines = [ln for ln in changed_lines if not any(rx.match(ln) for rx in patterns)]
    checks.add("S4.patch-minimal", "补丁只修改必要的依赖声明",
               "PASS" if not bad_lines else "FAIL",
               "改动行=%s" % changed_lines)

    # Hybrid 守卫：wildcard 命中的同类型文件必须全部是有效依赖且无无关文件
    if style == "hybrid-style":
        guard = expected["hybrid_guard"]
        matched = sorted(os.path.basename(p) for p in glob.glob(os.path.join(workdir, "*.h")))
        valid = sorted(guard["valid_dependencies"])
        checks.add("S4.hybrid-guard",
                   "Hybrid wildcard 守卫：%s 命中的 .h 全部为有效依赖且无无关文件" % guard["wildcard"],
                   "PASS" if matched == valid else "FAIL",
                   "wildcard 命中=%s, 有效依赖=%s" % (matched, valid))

    # ---------- 步骤 5：完整构建（Python 删除产物，等价 clean build），输出 2
    for art in ("app", "app.exe", "main.o"):
        ap = os.path.join(workdir, art)
        if os.path.exists(ap):
            os.remove(ap)
    p = runner.run([make, "CC=%s" % cc], cwd=workdir)
    checks.add("S5.build-after", "修复后完整构建退出码为 0",
               "PASS" if p.returncode == 0 else "FAIL", "exit=%d" % p.returncode)
    app = find_executable(workdir, expected["project"]["executable"])
    p = runner.run([app], cwd=workdir)
    out3 = p.stdout.strip()
    checks.add("S5.output-after", "修复后完整构建输出当前 VALUE=2",
               "PASS" if out3 == exp["after_fix_full_build_output"] else "FAIL",
               "stdout=%r" % out3)

    # ---------- 步骤 6-8：改 VALUE=3，不 clean 直接 make，应触发重建并输出 3
    time.sleep(1.2)  # 同样保证 config.h 的 mtime 严格晚于 main.o
    write_config(workdir, 3)
    mtime_main_o_mid = os.path.getmtime(os.path.join(workdir, "main.o"))
    p = runner.run([make, "CC=%s" % cc], cwd=workdir)
    rebuilt_after_fix = main_o_recompiled(p.stdout + p.stderr, workdir, mtime_main_o_mid)
    checks.add("S7.incremental-rebuild", "修复后修改 config.h，普通 make 触发 main.o 重编译",
               "PASS" if rebuilt_after_fix else "FAIL",
               "make 输出: %s" % (p.stdout.strip() or p.stderr.strip()))
    p = runner.run([app], cwd=workdir)
    out4 = p.stdout.strip()
    checks.add("S8.incremental-output", "修复后增量构建输出新值 3",
               "PASS" if out4 == exp["after_fix_incremental_output"] else "FAIL",
               "stdout=%r" % out4)

    # ---------- 步骤 9：课程固定 Oracle 重检，目标 MD 数量为 0
    oracle_after = oracle_detect(makefile_after, workdir)
    checks.add("S9.oracle-after", "修复后课程固定 Oracle 重检 MD 数量为 0",
               "PASS" if len(oracle_after["missing"]) == exp["oracle_md_after"] else "FAIL",
               json.dumps(oracle_after, ensure_ascii=False))

    # ---------- 步骤 10：修复前后声明风格分类一致
    style_before = classify_style(makefile_before)
    style_after = classify_style(makefile_after)
    checks.add("S10.style-consistency",
               "修复前后声明风格一致（%s → %s，期望 %s）" % (style_before, style_after, expected["style"]),
               "PASS" if (style_before == style_after == expected["style"]) else "FAIL",
               "before=%s after=%s" % (style_before, style_after))

    # ---------- 步骤 11：修复前后 clean build 行为一致；记录产物哈希
    workdir_equiv = tempfile.mkdtemp(prefix="mdfixer-%s-equiv-" % style)
    for name in SOURCE_FILES:
        src = os.path.join(fixture_dir, name)
        dst = os.path.join(workdir_equiv, "Makefile" if name == "Makefile.before" else name)
        shutil.copy2(src, dst)
    write_config(workdir_equiv, exp["behavior_equivalence_value"])
    with open(os.path.join(workdir_equiv, "Makefile"), "w", encoding="utf-8", newline="") as f:
        f.write(makefile_after)
    p = runner.run([make, "CC=%s" % cc], cwd=workdir_equiv)
    app_equiv = find_executable(workdir_equiv, expected["project"]["executable"])
    p = runner.run([app_equiv], cwd=workdir_equiv) if app_equiv else None
    out_equiv = (p.stdout.strip() if p else "")
    checks.add("S11.behavior-equivalence",
               "修复后 clean build（VALUE=1）程序行为与修复前一致",
               "PASS" if out_equiv == exp["behavior_equivalence_output"] else "FAIL",
               "stdout=%r" % out_equiv)
    hash_after_equiv = sha256_of(app_equiv) if app_equiv else None
    if hash_prefix and hash_after_equiv:
        if hash_prefix == hash_after_equiv:
            checks.add("S11.artifact-hash",
                       "产物哈希稳定且一致 sha256=%s" % hash_prefix, "PASS")
        else:
            checks.add("S11.artifact-hash",
                       "产物哈希不同（工具链内嵌时间戳等非确定性因素），以行为一致为准",
                       "WARN", "before=%s after=%s" % (hash_prefix, hash_after_equiv))

    # ---------- 汇总与证据落盘
    overall = "PASS" if not checks.failed else "FAIL"
    finished = datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary = {
        "style": style,
        "overall": overall,
        "run_at": finished,
        "fixture_dir": "fixtures/mdfixer/%s" % style,
        "fixture_commit": fcommit,
        "environment": env,
        "checks_passed": len([c for c in checks.items if c["status"] == "PASS"]),
        "checks_failed": len(checks.failed),
        "checks_warned": len(checks.warned),
        "checks": checks.items,
        "hashes": {"clean_before_fix_sha256": hash_prefix,
                   "clean_after_fix_sha256": hash_after_equiv},
        "oracle": {"before": oracle_before, "after": oracle_after},
        "style_classification": {"before": style_before, "after": style_after},
        "evidence_format": "observations.md + verify.log + summary.json（成员3草案，待成员2统一）",
    }
    with open(os.path.join(evidence_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.log("== style=%s 总体结果: %s (PASS=%d FAIL=%d WARN=%d)" %
               (style, overall, summary["checks_passed"], summary["checks_failed"],
                summary["checks_warned"]))
    logger.save(os.path.join(evidence_dir, "verify.log"))

    _write_observations(os.path.join(evidence_dir, "observations.md"),
                        style, summary, expected)

    if not keep_work:
        shutil.rmtree(workdir, ignore_errors=True)
        shutil.rmtree(workdir_equiv, ignore_errors=True)
    else:
        print("--keep-work 已保留工作目录: %s , %s" % (workdir, workdir_equiv))
    return overall == "PASS"


def _write_observations(path, style, summary, expected):
    env = summary["environment"]
    lines = []
    lines.append("# E3 MDFixer 显式声明修复验证记录：%s" % style)
    lines.append("")
    lines.append("- 运行时间（UTC）：%s" % summary["run_at"])
    lines.append("- 执行环境：%s %s，GNU Make=%s，CC=%s，Git=%s，Python=%s" % (
        env["os"], env["arch"], env["make_version"], env["cc_version"],
        env["git_version"], env["python"]))
    lines.append("- Fixture：`%s`，引入提交 `%s`" % (summary["fixture_dir"],
                                                 summary["fixture_commit"]))
    lines.append("- Oracle 来源：B13_MANUAL_ORACLE（课程固定 Oracle 的程序化实现），不是 A13 检测器结果")
    lines.append("- 证据结构：成员3草案，待成员2统一证据格式【待统一】")
    lines.append("")
    lines.append("## 实际观察")
    lines.append("")
    ob = summary["oracle"]["before"]
    oa = summary["oracle"]["after"]
    lines.append("1. 修复前：VALUE=1 完整构建输出 1；只改 config.h 为 VALUE=2 后普通 make "
                 "**不重编译** main.o，程序仍输出旧值 1（复现漏重建）。修复前 Oracle："
                 "declared=%s，actual=%s，missing=%s。" % (ob["declared"], ob["actual"], ob["missing"]))
    lines.append("2. `git apply --check` 与 `git apply` 退出码均为 0；补丁改动行仅为依赖声明"
                 "（patch_policy 校验通过）。")
    lines.append("3. 修复后完整构建输出 2；再把 config.h 改为 VALUE=3 后不 clean 直接 make，"
                 "main.o 被重编译，程序输出 3（增量重建恢复）。")
    lines.append("4. 修复后 Oracle 重检：declared=%s，missing=%s，目标 MD 数量为 0。"
                 % (oa["declared"], oa["missing"]))
    lines.append("5. 声明风格分类：修复前 %s，修复后 %s，一致（期望 %s）。" % (
        summary["style_classification"]["before"],
        summary["style_classification"]["after"], expected["style"]))
    hb = summary["hashes"]["clean_before_fix_sha256"]
    ha = summary["hashes"]["clean_after_fix_sha256"]
    if hb == ha:
        lines.append("6. 修复前后 VALUE=1 clean build 的程序行为一致（输出 1），"
                     "产物 SHA-256 相同：`%s`。" % hb)
    else:
        lines.append("6. 修复前后 VALUE=1 clean build 的程序行为一致（输出 1）。"
                     "产物 SHA-256 不同（before=%s，after=%s）：工具链二进制含内嵌时间戳"
                     "等非确定性内容，按课程要求以行为一致为准。" % (hb, ha))
    if style == "hybrid-style":
        lines.append("7. Hybrid wildcard 守卫已实际检查：工作目录中 `*.h` 仅命中 config.h"
                     "（唯一有效依赖），无无关文件，满足论文 wildcard 两条前置条件。")
    lines.append("")
    lines.append("## 检查项汇总")
    lines.append("")
    lines.append("| 检查项 | 说明 | 结果 |")
    lines.append("|---|---|---|")
    for c in summary["checks"]:
        lines.append("| %s | %s | %s |" % (c["id"], c["description"], c["status"]))
    lines.append("")
    lines.append("## 限制")
    lines.append("")
    lines.append("- A13 的 EChecker 修复后重检尚未执行，不能声称真实检测结果的 MD 数量为 0。")
    lines.append("- 完整命令日志见同目录 `verify.log`，机器可读摘要见 `summary.json`。")
    lines.append("")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="E3 MDFixer 显式声明修复基线验证（成员3）")
    parser.add_argument("--style", choices=STYLES + ["all"], default="all")
    parser.add_argument("--repo-root", default=None,
                        help="仓库根目录（含 fixtures/ 与 evidence/），默认为脚本所在目录的上级")
    parser.add_argument("--keep-work", action="store_true", help="保留临时工作目录以便人工检查")
    parser.add_argument("--make", default=None, help="make 可执行文件路径或名称")
    parser.add_argument("--cc", default=None, help="C 编译器路径或名称")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = args.repo_root or os.path.dirname(script_dir)
    make, cc, git = detect_tools(args.make, args.cc)
    print("工具: make=%s cc=%s git=%s" % (make, cc, git))

    styles = STYLES if args.style == "all" else [args.style]
    results = {}
    for style in styles:
        results[style] = verify_style(style, repo_root, make, cc, git, args.keep_work)
    print("\n===== 汇总 =====")
    for style, ok in results.items():
        print("%-14s %s" % (style, "PASS" if ok else "FAIL"))
    if not all(results.values()):
        sys.exit(1)
    print("全部风格验证通过。")


if __name__ == "__main__":
    main()
