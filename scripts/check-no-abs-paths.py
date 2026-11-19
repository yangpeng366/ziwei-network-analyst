#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径纪律：代码禁盘符硬编码 + ps1 必须 dot-source repo-paths.ps1 + 文档正文禁绝对路径。

为什么：机器一换盘符（旧盘仓根 F 盘 github -> 现盘 D 盘 gitAll）就有脚本静默指到空目录，
排盘引擎「不存在」这类报错往往只是路径漂移，不是代码错；文档里的绝对路径同理会误导复制粘贴。
唯一派生点是 scripts/lib/repo-paths.ps1（$RepoRoot / $EngineRoot / Assert-EngineRoot）。

三条规则：
  1. 代码文件里不得出现「盘符 + 冒号 + 斜杠」的绝对路径。真需要写字面量示例时，
     在该行加注释标记   no-abs-path: allow <原因>   —— 白名单只按行，不按文件。
  2. 每个 .ps1 必须 dot-source repo-paths.ps1；例外只有 repo-paths.ps1 自身，
     或显式声明   no-repo-paths: allow <原因>   （.cmd/.bat 无法 dot-source，不适用）。
  3. 文档（docs/**、skill/**、仓根 *.md）正文里不得出现绝对路径：机器路径只许出现在围栏代码块里
     （``` / ~~~ 包住的「可跑示例」）。正文用仓内相对路径、%USERPROFILE%、<(占位符)>，
     或在该行加 HTML 注释 <!-- no-abs-path: allow <原因> --> 白名单（渲染不可见）。

用法：
  python scripts/check-no-abs-paths.py   # 通过 -> 退出 0；违规 -> 列出并退出 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 代码扫描范围：文档目录里的代码同样要守规则
CODE_SUFFIXES = {".ps1", ".psm1", ".cmd", ".bat", ".py", ".js", ".mjs", ".cjs", ".ts", ".sh"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "out", "work", ".venv", "venv", "dist", "build"}

# 文档范围：docs/ 与 skill/ 递归全扫，仓根只扫顶层 *.md（不递归，否则等于全网扫一遍）。
# 围栏代码块内的机器路径是「可跑示例」，放行；正文只许相对路径 / %USERPROFILE% / 占位符。
DOC_DIRS = ("docs", "skill")
DOC_SUFFIXES = {".md"}

REPO_PATHS_REL = "scripts/lib/repo-paths.ps1"
REPO_PATHS_SELF = Path(REPO_PATHS_REL)

# 盘符绝对路径：前面不能紧跟字母数字下划线，避免把 URL 里协议后的双斜杠误判成盘符
DRIVE_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z]):[\\/]")
# dot-source + repo-paths.ps1 同一行：  . (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')
DOTSOURCE_RE = re.compile(r"^\s*\.\s*[(\s].*repo-paths\.ps1", re.IGNORECASE)
ALLOW_DRIVE = re.compile(r"no-abs-path:\s*allow", re.IGNORECASE)
ALLOW_PS1 = re.compile(r"no-repo-paths:\s*allow", re.IGNORECASE)
# 围栏代码块：``` 或 ~~~ 开头（允许最多 3 个前导空格）；块内是示例，放行
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def _read(path: Path) -> str:
    for enc in ("utf-8-sig", "cp936", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _code_files() -> list[Path]:
    out: list[Path] = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in CODE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts[:-1]):
            continue
        out.append(p)
    return out


def _doc_files() -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for name in DOC_DIRS:
        base = ROOT / name
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in DOC_SUFFIXES:
                continue
            if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts[:-1]):
                continue
            if p not in seen:
                seen.add(p)
                out.append(p)
    # 仓根 *.md：只顶层，不跟 DOC_DIRS 递归
    for p in sorted(ROOT.glob("*.md")):
        if p.is_file() and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def check_doc_prose(path: Path, text: str) -> list[tuple[int, str, str]]:
    """文档正文（围栏代码块之外）不得出现盘符绝对路径。"""
    bad: list[tuple[int, str, str]] = []
    fence: str | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        if ALLOW_DRIVE.search(line):
            continue
        hit = DRIVE_RE.search(line)
        if hit:
            bad.append((lineno, "文档正文硬编码盘符 {}".format(hit.group(0)), line.strip()))
    return bad


def check_drive_letters(path: Path, text: str) -> list[tuple[int, str, str]]:
    bad: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_DRIVE.search(line):
            continue
        m = DRIVE_RE.search(line)
        if m:
            bad.append((lineno, "硬编码盘符 {}".format(m.group(0)), line.strip()))
    return bad


def check_dot_source(path: Path, text: str) -> list[tuple[int, str, str]]:
    if ALLOW_PS1.search(text):
        return []
    for line in text.splitlines():
        if DOTSOURCE_RE.match(line):
            return []
    return [(1, "未 dot-source {}".format(REPO_PATHS_REL), "缺 . (Join-Path $PSScriptRoot 'lib\\repo-paths.ps1')")]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if not (ROOT / REPO_PATHS_SELF).exists():
        print("缺少唯一派生点：{}（先补它再让脚本依赖）".format(REPO_PATHS_REL))
        return 1

    files = _code_files()
    failures: list[tuple[str, int, str, str]] = []
    ps1_count = 0
    for path in files:
        text = _read(path)
        rel = _rel(path)
        for lineno, kind, snippet in check_drive_letters(path, text):
            failures.append((rel, lineno, kind, snippet))
        if path.suffix.lower() == ".ps1" and path.relative_to(ROOT).as_posix() != REPO_PATHS_SELF.as_posix():
            ps1_count += 1
            for lineno, kind, snippet in check_dot_source(path, text):
                failures.append((rel, lineno, kind, snippet))

    docs = _doc_files()
    for path in docs:
        rel = _rel(path)
        for lineno, kind, snippet in check_doc_prose(path, _read(path)):
            failures.append((rel, lineno, kind, snippet))

    if not failures:
        print("NO-ABS-PATHS OK：{} 个代码文件无盘符硬编码；{} 个 .ps1 全部 dot-source {}；"
              "{} 个文档正文无绝对路径（代码块内示例除外）".format(
                  len(files), ps1_count, REPO_PATHS_REL, len(docs)))
        return 0

    print("NO-ABS-PATHS FAIL：{} 处违规".format(len(failures)))
    for rel, lineno, kind, snippet in failures:
        print("  {}:{}  {}".format(rel, lineno, kind))
        print("    | {}".format(snippet[:180]))
    print("  修法：代码里仓根/引擎根走 scripts/lib/repo-paths.ps1 的 $RepoRoot/$EngineRoot；"
          "确需字面量示例时在该行写 `no-abs-path: allow <原因>`；"
          "文档正文改用仓内相对路径 / %USERPROFILE% / 占位符，或把机器路径挪进围栏代码块")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
