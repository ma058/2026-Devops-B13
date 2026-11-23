#!/usr/bin/env python3
"""E4 密钥泄露检查：仓库文件、Git 历史、镜像层三处。

用法：
  python3 scripts/secret_scan.py [目录]                 # 扫描工作区（Git 仓库只扫描已跟踪文件）
  python3 scripts/secret_scan.py . --history            # 另外扫描全部 Git 历史
  python3 scripts/secret_scan.py . --image <镜像名>      # 另外扫描 docker history 与镜像环境变量
发现疑似密钥时退出码为 1。输出只显示前 4 位，避免检查本身再泄露一次。
"""
import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("LLM/API Key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("私钥", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("密钥赋值", re.compile(r"(?i)\b[\w.-]*(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*[\"']?([^\s\"'#,;]{12,})")),
]
PLACEHOLDER = re.compile(r"(?i)replace|your[_-]|example|changeme|xxxx|<[^>]*>|\$\{|\$\(|\*\*\*")
SKIP_DIRS = {".git", "work", "__pycache__", ".venv", "node_modules"}


def mask(s):
    return s[:4] + "***" if len(s) > 4 else "***"


def runtime_expression(line, match):
    """Exempt only parsed dynamic RHS nodes at this exact match position.

    Never exempt quoted literals, appended values, or another match on the line.
    Git patch prefixes are removed only for parsing, not for reported locations.
    """
    prefix = 1 if line.startswith(('+', '-')) else 0
    tail = line[prefix:]
    source = tail.lstrip()
    offset = prefix + len(tail) - len(source)
    position = match.start(1) - offset
    if position < 0:
        return False
    column = len(source[:position].encode('utf-8'))
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return False
    known = ["uuid.uuid4().hex",
             "Path(config['token_file']).read_bytes().strip()",
             "os.environ.get('E14_TOKEN','')"]
    shapes = {ast.dump(ast.parse(s, mode='eval').body) for s in known}
    env_shape = ast.dump(ast.parse("'E14_TOKEN" + "='+token.read_text()+'\\n'", mode='eval').body)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if node.value.col_offset == column and ast.dump(node.value) in shapes:
                return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'write_text' and len(node.args) == 1
                and ast.dump(node.args[0]) == env_shape):
            literal = node.args[0].left.left
            if literal.end_col_offset == column:
                return True
    return False


def scan_text(text, where):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for name, pat in PATTERNS:
            for m in pat.finditer(line):
                value = m.group(m.lastindex or 0)
                if name == "密钥赋值" and PLACEHOLDER.search(value):
                    continue
                if name == "密钥赋值" and runtime_expression(line, m):
                    continue
                hits.append(f"{where}:{n}  {name}  {mask(value)}")
    return hits


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding='utf-8', errors='replace')


def files(root):
    p = git(root, "ls-files")
    if p.returncode == 0:
        return [root / f for f in p.stdout.splitlines()], True
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        out += [Path(dirpath) / f for f in filenames]
    return out, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--image")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    hits = []

    paths, in_git = files(root)
    for p in paths:
        rel = p.relative_to(root).as_posix()
        if p.name == ".env" or (p.name.startswith(".env.") and p.name != ".env.example"):
            if in_git:
                hits.append(f"{rel}  .env 被 Git 跟踪（应在 .gitignore 中，并立即作废其中的 Key）")
            continue  # 未跟踪的 .env 本来就用于存放密钥，不报
        try:
            if p.stat().st_size > 2_000_000:
                continue
            hits += scan_text(p.read_text(encoding="utf-8", errors="ignore"), rel)
        except OSError:
            pass

    env = root / ".env"
    if env.exists() and os.name == "posix" and env.stat().st_mode & 0o077:
        hits.append(".env 权限过宽：执行 chmod 600 .env")

    if args.history and in_git:
        log = git(root, "log", "--all", "-p", "--no-color").stdout
        hits += scan_text(log, "git-history")
    if args.image:
        for cmd, where in ((["docker", "history", "--no-trunc", "--format", "{{.CreatedBy}}", args.image], "image-history"),
                           (["docker", "image", "inspect", "--format", "{{range .Config.Env}}{{println .}}{{end}}", args.image], "image-env")):
            p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if p.returncode != 0:
                print(f"无法检查镜像 {args.image}：{p.stderr.strip()}", file=sys.stderr)
                sys.exit(2)
            hits += scan_text(p.stdout, where)

    for h in hits:
        print("FOUND  " + h)
    print(f"密钥检查：{'未发现问题' if not hits else f'发现 {len(hits)} 处疑似泄露'}"
          f"（文件 {len(paths)} 个{'，含 Git 历史' if args.history else ''}{'，含镜像 ' + args.image if args.image else ''}）")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
