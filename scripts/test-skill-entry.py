#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill 可被显式调用回归。

本仓的 skill 是产品入口：用户/别的 agent 显式点名 `ziwei-network-analyst` 就得
能用。本检查锁四件事：

1. SKILL.md frontmatter 合法（name / description 在位，name 与目录名一致）
2. skill 里提到的仓内路径都真实存在（指向的模块不许漂走）
3. skill 教的入口命令真能跑通（ask.py 出提示包、sweep.py 出推演）
4. 本机若装了全局 skill，必须与仓内源码一致（否则显式调用到的是旧版）

第 4 条在本机存在全局安装目录时才检查；CI 环境没有该目录，跳过。
对应本周衡量指标：Skill 可被显式调用。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "ziwei-network-analyst"
SKILL_MD = SKILL_DIR / "SKILL.md"
PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|py|json|yaml|yml|ts))`")
GLOBAL_SKILL = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".codex-home" / "skills" / "ziwei-network-analyst"


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def main() -> int:
    _force_utf8_stdout()
    errs: list[str] = []

    if not SKILL_MD.exists():
        print("缺 skill 源文件：{}".format(SKILL_MD))
        return 1
    text = SKILL_MD.read_text(encoding="utf-8")

    # 1) frontmatter
    if not text.startswith("---"):
        errs.append("SKILL.md 缺 frontmatter")
    else:
        fm = text.split("---", 2)[1]
        name = ""
        desc = ""
        for line in fm.splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
        if name != "ziwei-network-analyst":
            errs.append("skill name 应为 ziwei-network-analyst，实为 {}".format(name or "(空)"))
        if not desc:
            errs.append("skill 缺 description")
        if SKILL_DIR.name != name:
            errs.append("skill 目录名与 frontmatter name 不一致：{} / {}".format(SKILL_DIR.name, name))

    # 2) 提到的仓内路径都存在
    refs = sorted({m for m in PATH_RE.findall(text) if "/" in m and not m.startswith(("http", "C:", "D:", "F:"))})
    missing = [r for r in refs if not (ROOT / r).exists()]
    for r in missing:
        errs.append("skill 引用的路径不存在：{}".format(r))
    print("skill 引用仓内路径 {} 个，缺失 {}".format(len(refs), len(missing)))

    # 3) 入口命令跑得通
    ask = _run([sys.executable, str(ROOT / "scripts" / "ask.py"), "--demo",
                "--matter", "今年适合跳槽吗", "--print-only"])
    if ask.returncode != 0:
        errs.append("ask.py 跑不通：{}".format((ask.stderr or ask.stdout)[-400:]))
    elif "盘面事实" not in ask.stdout or "【怎么答】" not in ask.stdout:
        errs.append("ask.py 输出缺事实卡或回答契约")
    sweep = _run([sys.executable, str(ROOT / "scripts" / "sweep.py"),
                  "--chart", str(ROOT / "fixtures" / "sample-chart.json"), "--from", "2020", "--to", "2035"])
    if sweep.returncode != 0:
        errs.append("sweep.py 跑不通：{}".format((sweep.stderr or sweep.stdout)[-400:]))
    elif "逐年推演" not in sweep.stdout:
        errs.append("sweep.py 输出缺逐年推演")

    # 4) 全局安装与仓内一致（装了才查）
    if GLOBAL_SKILL.exists():
        for rel in ("SKILL.md", "agents/openai.yaml", "references/system.md", "references/corpus-policy.md"):
            src = SKILL_DIR / rel
            dst = GLOBAL_SKILL / rel
            if not src.exists() or not dst.exists():
                errs.append("全局 skill 缺 {}：{}".format(rel, dst))
                continue
            if src.read_bytes() != dst.read_bytes():
                errs.append("全局 skill 与仓内不一致：{}（显式调用到的是旧版，需重新安装）".format(rel))
        print("已检查全局安装：{}".format(GLOBAL_SKILL))
    else:
        print("未装全局 skill（{}），跳过同步检查".format(GLOBAL_SKILL))

    if errs:
        print("SKILL ENTRY FAIL（{} 项）".format(len(errs)))
        for e in errs:
            print(" - {}".format(e))
        return 1
    print("SKILL ENTRY PASS：frontmatter 合法、路径无漂、入口命令可跑")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
