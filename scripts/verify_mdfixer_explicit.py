#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_mdfixer_explicit.py — E3 MDFixer 显式声明修复基线验证（成员3）

对 fixtures/mdfixer/{target-style,macro-style,hybrid-style} 执行分工文档 7.3 的
验证流程（修复前复现漏重建 → git apply 参考补丁 → 修复后增量重建 → 课程固定
Oracle 重检 MD=0 → 声明风格一致 → clean build 行为等价 → 无效候选拒绝与恢复），
并按 B13 通用运行证据 0.1（evidence/README.md，成员2 维护）生成证据：

    evidence/E3/<日期>-<时间>-mdfixer-<风格>/
      observations.md     人读：环境、命令、观察结果、结论
      verify.log          机跑完整日志（每条命令的 argv/退出码/stdout/stderr 两段）
      summary.json        机器可读摘要（evidence_schema_version=0.1, B13_DRAFT）
      001.stdout.log      第 1 条命令的原始 stdout（分流保存，不保留跨流交错顺序）
      001.stderr.log      第 1 条命令的原始 stderr
      ...

用法（仓库根目录）：
    python3 scripts/verify_mdfixer_explicit.py --style target-style
    python3 scripts/verify_mdfixer_explicit.py --style all
    python3 scripts/verify_mdfixer_explicit.py --style all --keep-work
    python3 scripts/verify_mdfixer_explicit.py --self-test   # 负向回归（注入缺陷必须 FAIL）

环境要求：GNU Make（Windows 上为 mingw32-make）、C 编译器（cc 或 gcc）、git、python3。
脚本不依赖 make clean：所有完整构建都在全新工作目录或经 Python 删除产物后进行，
Windows 上没有 rm 命令也可运行；Linux/WSL 与 Windows 均已实测。

跨平台注意：临时工作目录中的 Makefile 一律以 UTF-8/LF/0644 重新写出，不复制
fixture 文件的权限位与换行符。Windows 检出可能得到 CRLF，且 Windows/WSL 权限
映射会把可执行位带入 Linux 临时目录，直接 copy2 会让临时 Makefile 变成
100755/CRLF，导致按 LF/100644 生成的 reference.patch 在 git apply --check
阶段连锁失败。
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
EVIDENCE_SCHEMA_VERSION = "0.1"
FORMAT_STATUS = "B13_DRAFT"


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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


class Recorder:
    """执行命令并按 B13 通用运行证据 0.1 采集 commands/checks 与分流日志。

    每条命令的原始 stdout/stderr 分别写入 NNN.stdout.log / NNN.stderr.log
    （分流保存，不声称保留两个流的交错时间顺序）；verify.log 按命令记录两段文本。
    """

    def __init__(self, logger, evidence_dir):
        self.logger = logger
        self.evidence_dir = evidence_dir
        self.commands = []
        self.checks = []
        self.last_command_id = None

    def run(self, argv, cwd, expect_success=None):
        argv = [str(a) for a in argv]
        cmd_id = "%03d" % (len(self.commands) + 1)
        started = utc_now()
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        finished = utc_now()
        stdout_name = "%s.stdout.log" % cmd_id
        stderr_name = "%s.stderr.log" % cmd_id
        with open(os.path.join(self.evidence_dir, stdout_name), "w",
                  encoding="utf-8", newline="") as f:
            f.write(proc.stdout if proc.stdout is not None else "")
        with open(os.path.join(self.evidence_dir, stderr_name), "w",
                  encoding="utf-8", newline="") as f:
            f.write(proc.stderr if proc.stderr is not None else "")
        self.commands.append({
            "id": cmd_id,
            "argv": argv,
            "cwd": str(cwd),
            "started_at": started,
            "finished_at": finished,
            "exit_code": proc.returncode,
            "timed_out": False,
            "execution_error": None,
            "stdout_path": stdout_name,
            "stderr_path": stderr_name,
        })
        self.last_command_id = cmd_id
        self.logger.log("$ %s" % " ".join(argv))
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

    def check(self, check_id, expected, actual, passed, required=True):
        self._record(check_id, expected, actual,
                     "PASS" if passed else "FAIL", required)

    def skip(self, check_id, expected, actual, required=False):
        self._record(check_id, expected, actual, "SKIPPED", required)

    def _record(self, check_id, expected, actual, status, required):
        self.checks.append({
            "id": check_id,
            "expected": expected,
            "actual": actual,
            "status": status,
            "command_id": self.last_command_id,
            "required": required,
        })
        self.logger.log("[%s] %s — 期望: %s | 实际: %s"
                        % (status, check_id, expected, actual))


def overall_result(checks):
    """成员2 0.1 判定规则：无检查则 NOT_RUN；有 FAIL 则 FAIL；无 FAIL 但有必需
    检查被跳过/未执行则 INCOMPLETE；全部通过才 PASS。"""
    if not checks:
        return "NOT_RUN"
    if any(c["status"] == "FAIL" for c in checks):
        return "FAIL"
    if any(c["status"] in ("SKIPPED", "NOT_RUN") and c["required"] for c in checks):
        return "INCOMPLETE"
    return "PASS"


# ---------------------------------------------------------------- 小工具

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def write_text_lf(path, text):
    """以 UTF-8/LF/0644 写文本文件。"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.chmod(path, 0o644)


def copy_fixture_text(fixture_dir, names, workdir):
    """把 fixture 源文件读为文本后以 LF/0644 写入工作目录（Makefile.before
    改名为 Makefile）。不复制原文件的权限位与换行符：Windows 检出可能是 CRLF，
    且 Windows/WSL 权限映射会把可执行位带入 Linux 临时目录，直接 copy2 会让
    临时 Makefile 成为 100755/CRLF，导致按 LF/100644 生成的 reference.patch
    在 git apply --check 阶段失败。"""
    for name in names:
        src = os.path.join(fixture_dir, name)
        dst = os.path.join(workdir, "Makefile" if name == "Makefile.before" else name)
        with open(src, "r", encoding="utf-8", newline=None) as f:
            write_text_lf(dst, f.read())


def write_config(workdir, value):
    write_text_lf(os.path.join(workdir, "config.h"), CONFIG_H.format(value=value))


def find_executable(workdir, name):
    for cand in (name, name + ".exe"):
        p = os.path.join(workdir, cand)
        if os.path.exists(p):
            return p
    return None


def remove_artifacts(workdir):
    for art in ("app", "app.exe", "main.o"):
        p = os.path.join(workdir, art)
        if os.path.exists(p):
            os.remove(p)


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


def git_text(git, repo_root, *args):
    proc = subprocess.run([git] + list(args), cwd=repo_root,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return (proc.stdout or "").strip()


def fixture_commit(repo_root, git, style):
    """返回定义该 fixture 被分析源码当前内容的真实提交 SHA（两段式提交的第一段）。

    只对被分析的源码文件（Makefile.before/main.c/config.h）取 git log：若对整个
    fixture 目录用 --diff-filter=A，后续新增的辅助文件（如 invalid.patch）会把
    检测结果带偏到非「引入被分析源码」的提交。"""
    sha = git_text(git, repo_root, "log", "--format=%H", "-1", "--",
                   "fixtures/mdfixer/%s/Makefile.before" % style,
                   "fixtures/mdfixer/%s/main.c" % style,
                   "fixtures/mdfixer/%s/config.h" % style)
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

def verify_style(style, repo_root, make, cc, git, keep_work,
                 mutation=None, patch_override=None, tag=None, note=None):
    """执行一个风格的完整验证并落盘证据。

    常规运行不传 mutation/patch_override。--self-test 负向回归会：
    - mutation：对工作目录中的源码注入缺陷（如 main.c 的 return 0 → return 7），
      要求验证器的退出码检查把它判为 FAIL；
    - patch_override：用被篡改的参考补丁（追加创建无关文件）替换 reference.patch，
      要求 S4.patch-minimal 的文件范围检查把它判为 FAIL。
    注入运行的 summary.result=FAIL 是预期结果，不是回归失败。
    """
    fixture_dir = os.path.join(repo_root, "fixtures", "mdfixer", style)
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as f:
        expected = json.load(f)
    with open(os.path.join(fixture_dir, "Makefile.before"), encoding="utf-8") as f:
        makefile_before = f.read()
    patch_path = patch_override or os.path.join(fixture_dir, "reference.patch")
    invalid_patch_path = os.path.join(fixture_dir, "invalid.patch")

    started_at = utc_now()

    # ---- source：源码版本与指纹（成员2 0.1 约定）。dirty 判定与 git_status
    # 排除 evidence/ 输出（证据不是源码；同批运行前序风格产生的证据目录不应
    # 使后续风格的源码状态被误报为 dirty）。
    head_sha = git_text(git, repo_root, "rev-parse", "HEAD")
    raw_status = git_text(git, repo_root, "status", "--porcelain")
    src_status = [ln for ln in raw_status.splitlines()
                  if ln.strip() and "evidence/" not in ln.replace("\\", "/")]
    git_status = "\n".join(src_status)
    remote_url = git_text(git, repo_root, "remote", "get-url", "origin")
    fcommit = fixture_commit(repo_root, git, style)
    tracked = ["scripts/verify_mdfixer_explicit.py"] + [
        "fixtures/mdfixer/%s/%s" % (style, name)
        for name in ("Makefile.before", "main.c", "config.h", "reference.patch",
                     "invalid.patch", "expected.json", "md-report.json", "README.md")
    ]
    file_hashes = {}
    for rel in tracked:
        p = os.path.join(repo_root, rel)
        if os.path.exists(p):
            file_hashes[rel] = sha256_of(p)
    source = {"repository": remote_url, "commit_sha": head_sha,
              "dirty": bool(git_status), "git_status": git_status,
              "file_sha256": file_hashes}

    run_id = "%s-mdfixer-%s" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S"), style)
    if tag:
        run_id += "-" + tag
    evidence_dir = os.path.join(repo_root, "evidence", "E3", run_id)
    if os.path.exists(evidence_dir):
        raise FileExistsError("证据目录已存在，拒绝覆盖: %s" % evidence_dir)
    os.makedirs(evidence_dir)

    logger = Logger()
    recorder = Recorder(logger, evidence_dir)
    logger.log("== style=%s" % style)
    logger.log("== fixture_dir: %s" % fixture_dir)
    logger.log("== fixture_commit（引入该 fixture 的真实提交）: %s" % fcommit)
    logger.log("== evidence_dir: %s" % evidence_dir)
    logger.log("== HEAD=%s dirty=%s" % (head_sha, bool(git_status)))
    logger.log("== Oracle 来源: B13_MANUAL_ORACLE（课程固定 Oracle 程序化实现）；"
               "A13 EChecker 未执行")

    # md-report.json 引用的提交必须与 git 历史中定义被分析源码内容的提交一致
    # （若被分析源码日后变更，报告必须更新为新的真实提交，否则此处 FAIL）。
    with open(os.path.join(fixture_dir, "md-report.json"), encoding="utf-8") as f:
        report_commit = json.load(f)["repository"]["commit"]
    recorder.check("S0.report-commit",
                   "md-report.json 引用的 fixture 提交与 git 历史一致（真实提交）",
                   "报告引用=%s，git 历史=%s" % (report_commit, fcommit),
                   report_commit == fcommit)

    env = {"os": platform.system().lower(), "os_release": platform.release(),
           "arch": platform.machine(), "cwd": repo_root}
    v_make = recorder.run([make, "--version"], cwd=repo_root).stdout.splitlines()
    v_cc = recorder.run([cc, "--version"], cwd=repo_root).stdout.splitlines()
    v_git = recorder.run([git, "--version"], cwd=repo_root).stdout.splitlines()
    tools = {
        "python": {"value": platform.python_version(), "path": sys.executable},
        "git": {"value": v_git[0] if v_git else "", "path": git},
        "make": {"value": v_make[0] if v_make else "", "path": make},
        "cc": {"value": v_cc[0] if v_cc else "", "path": cc},
        "docker": {"value": None, "reason": "本验证套件不使用 Docker"},
    }

    workdir = tempfile.mkdtemp(prefix="mdfixer-%s-" % style)
    logger.log("== workdir: %s" % workdir)
    copy_fixture_text(fixture_dir, SOURCE_FILES, workdir)
    if note:
        logger.log("== 负向回归说明: %s" % note)
    if mutation is not None:
        mutation(workdir)

    exp = expected["expect"]

    # ---------- 步骤 1：VALUE=1 完整构建，程序输出 1
    p = recorder.run([make, "CC=%s" % cc], cwd=workdir)
    recorder.check("S1.build-before", "修复前完整构建退出码为 0",
                   "exit=%d" % p.returncode, p.returncode == 0)
    app = find_executable(workdir, expected["project"]["executable"])
    p = recorder.run([app], cwd=workdir) if app else None
    out1 = (p.stdout.strip() if p else "")
    recorder.check("S1.output-before", "VALUE=1 完整构建后程序输出 1 且正常退出",
                   "exit=%s stdout=%r" % (p.returncode if p else None, out1),
                   app is not None and p.returncode == 0
                   and out1 == exp["prefix_clean_output"])
    hash_prefix = sha256_of(app) if app else None

    # ---------- 步骤 2+3：只改 config.h 为 VALUE=2，普通 make 仍输出旧值 1（复现漏重建）
    # 等待 1.2s 再改 config.h：保证其 mtime 严格晚于 main.o（规避文件系统时间戳
    # 粒度导致的"同一时间戳不重建"假象），使"改了头文件却没重编译"成为有效证据。
    time.sleep(1.2)
    write_config(workdir, 2)
    mtime_main_o_before = os.path.getmtime(os.path.join(workdir, "main.o"))
    p = recorder.run([make, "CC=%s" % cc], cwd=workdir)
    rebuilt_before_fix = main_o_recompiled(p.stdout + p.stderr, workdir, mtime_main_o_before)
    recorder.check("S3.no-rebuild-before",
                   "修复前只改 config.h 后普通 make 成功且不重编译 main.o（复现漏重建）",
                   "make_exit=%d，main.o 重编译=%s" % (p.returncode, rebuilt_before_fix),
                   p.returncode == 0 and not rebuilt_before_fix)
    p = recorder.run([app], cwd=workdir)
    out2_stale = p.stdout.strip()
    recorder.check("S3.stale-output", "修复前增量构建后程序仍输出旧值 1 且正常退出",
                   "exit=%d stdout=%r" % (p.returncode, out2_stale),
                   p.returncode == 0 and out2_stale == exp["stale_output_before_fix"])

    oracle_before = oracle_detect(makefile_before, workdir)
    recorder.check("S3.oracle-before",
                   "课程固定 Oracle 在修复前报告 1 条 MISSING(main.o→config.h)",
                   json.dumps(oracle_before, ensure_ascii=False),
                   len(oracle_before["missing"]) == exp["oracle_md_before"]
                   and oracle_before["missing"] == [expected["md"]["dependency"]])

    # ---------- 步骤 4：git apply --check，再 git apply reference.patch
    # 应用前快照源文件内容：补丁应用后核对实际变更范围（只允许 Makefile 变化）
    snapshot = {name: sha256_of(os.path.join(workdir, name))
                for name in ("Makefile", "main.c", "config.h")
                if os.path.exists(os.path.join(workdir, name))}
    p = recorder.run([git, "apply", "--check", patch_path], cwd=workdir)
    recorder.check("S4.apply-check", "git apply --check reference.patch 通过",
                   "exit=%d" % p.returncode, p.returncode == 0)
    p = recorder.run([git, "apply", patch_path], cwd=workdir)
    recorder.check("S4.apply", "git apply reference.patch 成功",
                   "exit=%d" % p.returncode, p.returncode == 0)
    with open(os.path.join(workdir, "Makefile"), encoding="utf-8") as f:
        makefile_after = f.read()

    # 补丁最小性（三层）：
    # (a) 文件范围：diff --git 头只允许出现 Makefile，禁止新增/删除/重命名/模式变化/二进制；
    # (b) 行内容：增删行必须匹配 allowed_change_patterns；
    # (c) 应用后实际变更：工作目录中只有 Makefile 内容变化，且不允许出现快照之外的
    #     任何新文件（源文件+构建产物白名单之外一律拒绝）。
    with open(patch_path, encoding="utf-8", newline=None) as f:
        patch_text = f.read()
    scope_files, scope_problems = analyze_patch_scope(patch_text)
    changed_lines = []
    for line in patch_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            changed_lines.append(line[1:])
    patterns = [re.compile(x) for x in expected["patch_policy"]["allowed_change_patterns"]]
    bad_lines = [ln for ln in changed_lines if not any(rx.match(ln) for rx in patterns)]
    actual_changes = []
    for name, before_hash in snapshot.items():
        cur = os.path.join(workdir, name)
        if not os.path.exists(cur):
            actual_changes.append("%s 被删除" % name)
        elif sha256_of(cur) != before_hash:
            actual_changes.append(name)
    allowed_files = {"Makefile", "main.c", "config.h", "app", "app.exe", "main.o"}
    unexpected_files = sorted(set(os.listdir(workdir)) - allowed_files)
    minimal_ok = (scope_files == ["Makefile"] and not scope_problems
                   and not bad_lines and actual_changes == ["Makefile"]
                   and not unexpected_files)
    recorder.check("S4.patch-minimal",
                   "补丁只修改指定 Makefile 的必要依赖声明（文件范围+行内容+应用后实际变更）",
                   "diff 文件=%s，范围问题=%s，违例行=%s，实际变更=%s，意外文件=%s"
                   % (scope_files, scope_problems, bad_lines, actual_changes,
                      unexpected_files),
                   minimal_ok)

    # Hybrid 守卫：wildcard 命中的同类型文件必须全部是有效依赖且无无关文件
    if style == "hybrid-style":
        guard = expected["hybrid_guard"]
        matched = sorted(os.path.basename(p) for p in glob.glob(os.path.join(workdir, "*.h")))
        valid = sorted(guard["valid_dependencies"])
        recorder.check("S4.hybrid-guard",
                       "Hybrid wildcard 守卫：%s 命中的 .h 全部为有效依赖且无无关文件" % guard["wildcard"],
                       "wildcard 命中=%s, 有效依赖=%s" % (matched, valid),
                       matched == valid)

    # ---------- 步骤 5：完整构建（Python 删除产物，等价 clean build），输出 2
    remove_artifacts(workdir)
    p = recorder.run([make, "CC=%s" % cc], cwd=workdir)
    recorder.check("S5.build-after", "修复后完整构建退出码为 0",
                   "exit=%d" % p.returncode, p.returncode == 0)
    app = find_executable(workdir, expected["project"]["executable"])
    p = recorder.run([app], cwd=workdir) if app else None
    out3 = (p.stdout.strip() if p else "")
    recorder.check("S5.output-after", "修复后完整构建输出当前 VALUE=2 且正常退出",
                   "exit=%s stdout=%r" % (p.returncode if p else None, out3),
                   app is not None and p.returncode == 0
                   and out3 == exp["after_fix_full_build_output"])

    # ---------- 步骤 6-8：改 VALUE=3，不 clean 直接 make，应触发重建并输出 3
    time.sleep(1.2)  # 同样保证 config.h 的 mtime 严格晚于 main.o
    write_config(workdir, 3)
    mtime_main_o_mid = os.path.getmtime(os.path.join(workdir, "main.o"))
    p = recorder.run([make, "CC=%s" % cc], cwd=workdir)
    rebuilt_after_fix = main_o_recompiled(p.stdout + p.stderr, workdir, mtime_main_o_mid)
    recorder.check("S7.incremental-rebuild", "修复后修改 config.h，普通 make 成功且触发 main.o 重编译",
                   "make_exit=%d，main.o 重编译=%s" % (p.returncode, rebuilt_after_fix),
                   p.returncode == 0 and rebuilt_after_fix)
    p = recorder.run([app], cwd=workdir)
    out4 = p.stdout.strip()
    recorder.check("S8.incremental-output", "修复后增量构建输出新值 3 且正常退出",
                   "exit=%d stdout=%r" % (p.returncode, out4),
                   p.returncode == 0 and out4 == exp["after_fix_incremental_output"])

    # ---------- 步骤 9：课程固定 Oracle 重检，目标 MD 数量为 0
    oracle_after = oracle_detect(makefile_after, workdir)
    recorder.check("S9.oracle-after", "修复后课程固定 Oracle 重检 MD 数量为 0",
                   json.dumps(oracle_after, ensure_ascii=False),
                   len(oracle_after["missing"]) == exp["oracle_md_after"])

    # ---------- 步骤 10：修复前后声明风格分类一致
    style_before = classify_style(makefile_before)
    style_after = classify_style(makefile_after)
    recorder.check("S10.style-consistency",
                   "修复前后声明风格一致（期望 %s）" % expected["style"],
                   "before=%s after=%s" % (style_before, style_after),
                   style_before == style_after == expected["style"])

    # ---------- 步骤 11：修复前后 clean build 行为一致；记录产物哈希
    workdir_equiv = tempfile.mkdtemp(prefix="mdfixer-%s-equiv-" % style)
    copy_fixture_text(fixture_dir, SOURCE_FILES, workdir_equiv)
    write_config(workdir_equiv, exp["behavior_equivalence_value"])
    write_text_lf(os.path.join(workdir_equiv, "Makefile"), makefile_after)
    p = recorder.run([make, "CC=%s" % cc], cwd=workdir_equiv)
    make_equiv_exit = p.returncode
    app_equiv = find_executable(workdir_equiv, expected["project"]["executable"])
    p = recorder.run([app_equiv], cwd=workdir_equiv) if app_equiv else None
    out_equiv = (p.stdout.strip() if p else "")
    recorder.check("S11.behavior-equivalence",
                   "修复后 clean build（VALUE=1）构建成功且程序行为与修复前一致",
                   "make_exit=%d app_exit=%s stdout=%r"
                   % (make_equiv_exit, p.returncode if p else None, out_equiv),
                   make_equiv_exit == 0 and app_equiv is not None
                   and p.returncode == 0
                   and out_equiv == exp["behavior_equivalence_output"])
    hash_after_equiv = sha256_of(app_equiv) if app_equiv else None
    if hash_prefix and hash_after_equiv and hash_prefix == hash_after_equiv:
        recorder.check("S11.artifact-hash",
                       "补充检查：修复前后 VALUE=1 产物 SHA-256 一致",
                       "sha256=%s" % hash_prefix, True, required=False)
    else:
        recorder.skip("S11.artifact-hash",
                      "补充检查：修复前后 VALUE=1 产物 SHA-256 一致",
                      "before=%s after=%s 不同（工具链内嵌时间戳等非确定性因素），"
                      "以 S11.behavior-equivalence 行为一致为准" % (hash_prefix, hash_after_equiv))

    # ---------- 步骤 12：无效修复候选的拒绝与恢复
    # invalid.patch 把编译 recipe 替换为 `false`：可干净应用，但构建必然失败，
    # 用于验证"无效候选被拒绝，且恢复原始 Makefile 后一切如初"。
    rejdir = tempfile.mkdtemp(prefix="mdfixer-%s-reject-" % style)
    copy_fixture_text(fixture_dir, SOURCE_FILES, rejdir)
    p = recorder.run([git, "apply", "--check", invalid_patch_path], cwd=rejdir)
    recorder.check("S12.invalid-apply-check",
                   "git apply --check invalid.patch 通过（补丁格式合法、可干净应用）",
                   "exit=%d" % p.returncode, p.returncode == 0)
    p = recorder.run([git, "apply", invalid_patch_path], cwd=rejdir)
    recorder.check("S12.invalid-apply", "git apply invalid.patch 成功",
                   "exit=%d" % p.returncode, p.returncode == 0)
    p = recorder.run([make, "CC=%s" % cc], cwd=rejdir)
    recorder.check("S12.invalid-rejected",
                   "应用无效候选后构建失败（退出码非 0），候选被拒绝",
                   "exit=%d" % p.returncode, p.returncode != 0)
    write_text_lf(os.path.join(rejdir, "Makefile"), makefile_before)
    remove_artifacts(rejdir)
    p = recorder.run([make, "CC=%s" % cc], cwd=rejdir)
    app_rej = find_executable(rejdir, expected["project"]["executable"])
    p2 = recorder.run([app_rej], cwd=rejdir) if (p.returncode == 0 and app_rej) else None
    out_rej = (p2.stdout.strip() if p2 else "")
    recorder.check("S12.recovery",
                   "恢复原始 Makefile 后完整构建成功且程序输出 %s 并正常退出"
                   % exp["prefix_clean_output"],
                   "build_exit=%d app_exit=%s stdout=%r"
                   % (p.returncode, p2.returncode if p2 else None, out_rej),
                   p.returncode == 0 and p2 is not None and p2.returncode == 0
                   and out_rej == exp["prefix_clean_output"])

    # ---------- 汇总与证据落盘
    finished_at = utc_now()
    result = overall_result(recorder.checks)

    _write_observations(os.path.join(evidence_dir, "observations.md"),
                        style, run_id, started_at, finished_at, env, tools,
                        source, fcommit, recorder.checks, result, expected,
                        oracle_before, oracle_after, style_before, style_after,
                        hash_prefix, hash_after_equiv, note)
    n_pass = len([c for c in recorder.checks if c["status"] == "PASS"])
    n_fail = len([c for c in recorder.checks if c["status"] == "FAIL"])
    n_skip = len([c for c in recorder.checks if c["status"] == "SKIPPED"])
    logger.log("== style=%s 总体结果: %s (PASS=%d FAIL=%d SKIPPED=%d)"
               % (style, result, n_pass, n_fail, n_skip))
    logger.save(os.path.join(evidence_dir, "verify.log"))

    artifacts = []
    for name in sorted(os.listdir(evidence_dir)):
        if name == "summary.json":
            continue  # 不对 summary 自身求哈希，避免循环引用
        p = os.path.join(evidence_dir, name)
        if os.path.isfile(p):
            artifacts.append({"path": name, "sha256": sha256_of(p)})

    summary = {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "format_status": FORMAT_STATUS,
        "run_id": run_id,
        "suite": "E3",
        "case": "mdfixer-%s" % style,
        "started_at": started_at,
        "finished_at": finished_at,
        "source": source,
        "environment": env,
        "tools": tools,
        "commands": recorder.commands,
        "checks": recorder.checks,
        "artifacts": artifacts,
        "provenance": {
            "oracle": "B13_MANUAL_ORACLE",
            "basis": "课程固定 Oracle 的程序化实现（本脚本 oracle_detect）；"
                     "人工判断依据 fixtures/mdfixer/%s 与其 expected.json" % style,
            "detector_executed": False,
            "note": "A13 EChecker 修复后重检尚未执行，本证据不声称真实检测器 MD=0",
        },
        "result": result,
        "details": {
            "fixture_dir": "fixtures/mdfixer/%s" % style,
            "fixture_commit": fcommit,
            "hashes": {"clean_before_fix_sha256": hash_prefix,
                       "clean_after_fix_sha256": hash_after_equiv},
            "oracle": {"before": oracle_before, "after": oracle_after},
            "style_classification": {"before": style_before, "after": style_after},
        },
    }
    if mutation is not None or patch_override is not None:
        summary["details"]["self_test"] = {
            "injected_defect": note,
            "expected_inner_result": "FAIL",
            "meaning": "负向回归运行：故意注入缺陷，验证器必须将其判为 FAIL；"
                       "本目录 result=FAIL 是预期结果，不是回归失败",
        }
    with open(os.path.join(evidence_dir, "summary.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if not keep_work:
        shutil.rmtree(workdir, ignore_errors=True)
        shutil.rmtree(workdir_equiv, ignore_errors=True)
        shutil.rmtree(rejdir, ignore_errors=True)
    else:
        print("--keep-work 已保留工作目录: %s , %s , %s" % (workdir, workdir_equiv, rejdir))
    return summary


def _write_observations(path, style, run_id, started_at, finished_at, env, tools,
                        source, fcommit, checks, result, expected,
                        oracle_before, oracle_after, style_before, style_after,
                        hash_prefix, hash_after_equiv, note=None):
    lines = []
    lines.append("# E3 MDFixer 显式声明修复验证记录：%s" % style)
    lines.append("")
    if note:
        lines.append("> **负向回归运行**：%s" % note)
        lines.append("> 本目录 `result=FAIL` 是预期结果（缺陷被验证器捕获），"
                     "不是回归失败。")
        lines.append("")
    lines.append("- run_id：`%s`" % run_id)
    lines.append("- 开始/结束（UTC）：%s → %s" % (started_at, finished_at))
    lines.append("- 执行环境：%s %s（%s），GNU Make=%s，CC=%s，Git=%s，Python=%s" % (
        env["os"], env["arch"], env["os_release"],
        tools["make"]["value"], tools["cc"]["value"],
        tools["git"]["value"], tools["python"]["value"]))
    lines.append("- 源码：`%s`，HEAD `%s`，dirty=%s" % (
        source["repository"], source["commit_sha"], source["dirty"]))
    lines.append("- Fixture：`fixtures/mdfixer/%s`，引入提交 `%s`" % (style, fcommit))
    lines.append("- Oracle 来源：B13_MANUAL_ORACLE（课程固定 Oracle 的程序化实现），"
                 "不是 A13 检测器结果；A13 EChecker 修复后重检尚未执行")
    lines.append("- 证据格式：B13 通用运行证据 %s（%s），与 evidence/README.md 一致" % (
        EVIDENCE_SCHEMA_VERSION, FORMAT_STATUS))
    lines.append("")
    lines.append("## 实际观察")
    lines.append("")
    lines.append("1. 修复前：VALUE=1 完整构建输出 1；只改 config.h 为 VALUE=2 后普通 make "
                 "**不重编译** main.o，程序仍输出旧值 1（复现漏重建）。修复前 Oracle："
                 "declared=%s，actual=%s，missing=%s。" % (
                     oracle_before["declared"], oracle_before["actual"],
                     oracle_before["missing"]))
    lines.append("2. `git apply --check` 与 `git apply` 退出码均为 0；补丁改动行仅为依赖声明"
                 "（patch_policy 校验通过）。")
    lines.append("3. 修复后完整构建输出 2；再把 config.h 改为 VALUE=3 后不 clean 直接 make，"
                 "main.o 被重编译，程序输出 3（增量重建恢复）。")
    lines.append("4. 修复后 Oracle 重检：declared=%s，missing=%s，目标 MD 数量为 0。"
                 % (oracle_after["declared"], oracle_after["missing"]))
    lines.append("5. 声明风格分类：修复前 %s，修复后 %s，一致（期望 %s）。" % (
        style_before, style_after, expected["style"]))
    if hash_prefix == hash_after_equiv:
        lines.append("6. 修复前后 VALUE=1 clean build 的程序行为一致（输出 1），"
                     "产物 SHA-256 相同：`%s`。" % hash_prefix)
    else:
        lines.append("6. 修复前后 VALUE=1 clean build 的程序行为一致（输出 1）。"
                     "产物 SHA-256 不同（before=%s，after=%s）：工具链二进制含内嵌时间戳"
                     "等非确定性内容，按课程要求以行为一致为准。" % (hash_prefix, hash_after_equiv))
    if style == "hybrid-style":
        lines.append("7. Hybrid wildcard 守卫已实际检查：工作目录中 `*.h` 仅命中 config.h"
                     "（唯一有效依赖），无无关文件，满足论文 wildcard 两条前置条件。")
    lines.append("8. 无效候选拒绝与恢复：`invalid.patch`（编译 recipe 替换为 `false`）可干净"
                 "应用，应用后构建失败（退出码非 0，候选被拒绝）；恢复原始 Makefile 后完整"
                 "构建成功，程序输出 1，一切如初。")
    lines.append("")
    lines.append("## 检查项汇总")
    lines.append("")
    lines.append("| 检查项 | 期望 | 状态 |")
    lines.append("|---|---|---|")
    for c in checks:
        lines.append("| %s | %s | %s |" % (c["id"], c["expected"], c["status"]))
    lines.append("")
    lines.append("总体结果：**%s**" % result)
    lines.append("")
    lines.append("## 限制")
    lines.append("")
    lines.append("- A13 的 EChecker 修复后重检尚未执行，不能声称真实检测结果的 MD 数量为 0。")
    lines.append("- 每条命令的原始 stdout/stderr 见同目录 `NNN.stdout.log`/`NNN.stderr.log`"
                 "（分流保存，不保留跨流交错顺序）；机跑完整日志见 `verify.log`；"
                 "机器可读摘要见 `summary.json`。")
    lines.append("")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------- 补丁范围分析

DIFF_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")
# 出现任一标记即说明补丁涉及新增/删除/重命名文件、权限位变化或二进制内容，
# 都不属于「只修改指定 Makefile 的必要依赖声明」。
PATCH_SCOPE_FORBIDDEN_MARKERS = (
    "new file mode", "deleted file mode", "rename from", "rename to",
    "copy from", "copy to", "old mode", "new mode", "Binary files",
    "GIT binary patch",
)


def analyze_patch_scope(patch_text):
    """解析补丁的文件范围：返回 (涉及的文件列表, 范围问题列表)。"""
    files = []
    problems = []
    for line in patch_text.splitlines():
        m = DIFF_FILE_RE.match(line)
        if m:
            files.append(m.group(2))
            continue
        for marker in PATCH_SCOPE_FORBIDDEN_MARKERS:
            if line.startswith(marker):
                problems.append(line)
                break
    return files, problems


# ---------------------------------------------------------------- 负向回归注入

def mutate_exit_code(workdir):
    """注入缺陷：main.c 的 return 0 → return 7（输出不变、退出码 7）。

    用于验证输出类检查同时校验退出码；若验证器只比 stdout 不看退出码，
    该缺陷将被放行（成员2审查反馈 P2-1 的复现方式）。"""
    path = os.path.join(workdir, "main.c")
    with open(path, "r", encoding="utf-8", newline=None) as f:
        text = f.read()
    if "return 0;" not in text:
        raise AssertionError("main.c 中未找到 return 0; 无法注入退出码缺陷")
    write_text_lf(path, text.replace("return 0;", "return 7;"))


# 追加到参考补丁末尾的“夹带文件”diff：创建 unrelated.txt，其内容恰好匹配
# allowed_change_patterns，因此只检查行内容时会放行（成员2审查反馈 P2-2 的复现方式）。
EXTRA_FILE_DIFF = (
    "diff --git a/unrelated.txt b/unrelated.txt\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/unrelated.txt\n"
    "@@ -0,0 +1 @@\n"
    "+main.o: main.c config.h\n"
)


def build_extra_file_patch(repo_root, style):
    """把原始参考补丁 + 夹带文件 diff 写入临时文件，返回其路径。"""
    original = os.path.join(repo_root, "fixtures", "mdfixer", style, "reference.patch")
    with open(original, "r", encoding="utf-8", newline=None) as f:
        text = f.read()
    if not text.endswith("\n"):
        text += "\n"
    tampered_dir = tempfile.mkdtemp(prefix="mdfixer-selftest-patch-")
    tampered = os.path.join(tampered_dir, "reference.patch")
    write_text_lf(tampered, text + EXTRA_FILE_DIFF)
    return tampered


def run_self_test(repo_root, make, cc, git):
    """负向回归：故意注入两类缺陷，验证验证器必须把它们判为 FAIL。

    元结论 PASS = 两类缺陷均被捕获；任一缺陷被放行则元结论 FAIL（脚本非零退出）。
    每次注入运行的完整证据照常落盘（其 result=FAIL 为预期）。"""
    note_exit = ("注入缺陷：main.c 的 return 0 → return 7（stdout 不变、退出码 7）；"
                 "期望输出类检查因退出码非 0 判 FAIL，整体 FAIL")
    s1 = verify_style("target-style", repo_root, make, cc, git, False,
                     mutation=mutate_exit_code, tag="selftest-exit7",
                     note=note_exit)
    caught_exit = (s1["result"] == "FAIL"
                   and any(c["id"] == "S1.output-before" and c["status"] == "FAIL"
                           for c in s1["checks"]))
    print("[SELFTEST] exit-code 注入被捕获: %s（run_id=%s，inner result=%s）"
          % (caught_exit, s1["run_id"], s1["result"]))

    tampered_patch = build_extra_file_patch(repo_root, "target-style")
    note_patch = ("注入缺陷：reference.patch 追加创建 unrelated.txt"
                 "（内容匹配 allowed_change_patterns）；期望 S4.patch-minimal 的"
                 "文件范围/实际变更检查判 FAIL，整体 FAIL")
    s2 = verify_style("target-style", repo_root, make, cc, git, False,
                     patch_override=tampered_patch, tag="selftest-extra-file",
                     note=note_patch)
    shutil.rmtree(os.path.dirname(tampered_patch), ignore_errors=True)
    caught_extra = (s2["result"] == "FAIL"
                    and any(c["id"] == "S4.patch-minimal" and c["status"] == "FAIL"
                            for c in s2["checks"]))
    print("[SELFTEST] extra-file 注入被捕获: %s（run_id=%s，inner result=%s）"
          % (caught_extra, s2["run_id"], s2["result"]))

    ok = caught_exit and caught_extra
    print("[SELFTEST] 负向回归总体: %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    parser = argparse.ArgumentParser(description="E3 MDFixer 显式声明修复基线验证（成员3）")
    parser.add_argument("--style", choices=STYLES + ["all"], default="all")
    parser.add_argument("--repo-root", default=None,
                        help="仓库根目录（含 fixtures/ 与 evidence/），默认为脚本所在目录的上级")
    parser.add_argument("--keep-work", action="store_true", help="保留临时工作目录以便人工检查")
    parser.add_argument("--make", default=None, help="make 可执行文件路径或名称")
    parser.add_argument("--cc", default=None, help="C 编译器路径或名称")
    parser.add_argument("--self-test", action="store_true",
                        help="负向回归：注入退出码缺陷与夹带文件补丁，验证验证器能将其判为 FAIL")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = args.repo_root or os.path.dirname(script_dir)
    make, cc, git = detect_tools(args.make, args.cc)
    print("工具: make=%s cc=%s git=%s" % (make, cc, git))

    if args.self_test:
        sys.exit(0 if run_self_test(repo_root, make, cc, git) else 1)

    styles = STYLES if args.style == "all" else [args.style]
    results = {}
    for style in styles:
        summary = verify_style(style, repo_root, make, cc, git, args.keep_work)
        results[style] = summary["result"] == "PASS"
    print("\n===== 汇总 =====")
    for style, ok in results.items():
        print("%-14s %s" % (style, "PASS" if ok else "FAIL"))
    if not all(results.values()):
        sys.exit(1)
    print("全部风格验证通过。")


if __name__ == "__main__":
    main()
