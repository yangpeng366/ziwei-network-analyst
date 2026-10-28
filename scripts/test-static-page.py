#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态站结构自检：app.js 里引用的元素 id 必须真实存在于 index.html。

背景：静态站曾在 render() 开头就写 #chart-label，而 HTML 里并没有这个元素，
抛错后整页只剩「加载中…」，而 CI 只校验生成数据、从不加载页面，漏掉了。
这个检查无需浏览器，任何环境都能跑。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
APP_JS = DOCS / "app.js"
INDEX_HTML = DOCS / "index.html"

ID_RE = re.compile(r"""\$\(\s*["']([^"']+)["']\s*\)|getElementById\(\s*["']([^"']+)["']\s*\)""")
HTML_ID_RE = re.compile(r"""\bid=["']([^"']+)["']""")
SCRIPT_SRC_RE = re.compile(r"""<script[^>]*\bsrc=["']([^"']+)["']""")
CSS_HREF_RE = re.compile(r"""<link[^>]*\bhref=["']([^"']+)["']""")


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _force_utf8_stdout()
    errs: list[str] = []

    for f in (APP_JS, INDEX_HTML):
        if not f.exists():
            print("缺少文件：{}".format(f))
            return 1

    html = INDEX_HTML.read_text(encoding="utf-8")
    js = APP_JS.read_text(encoding="utf-8")

    html_ids = set(HTML_ID_RE.findall(html))
    used_ids = set()
    for a, b in ID_RE.findall(js):
        used_ids.add(a or b)

    missing = sorted(used_ids - html_ids)
    for mid in missing:
        errs.append("app.js 引用了不存在的元素 id：#{}".format(mid))

    for src in SCRIPT_SRC_RE.findall(html):
        if src.startswith(("http://", "https://", "//", "data:")):
            continue
        if not (DOCS / src).exists():
            errs.append("index.html 引用的脚本不存在：{}".format(src))
    for href in CSS_HREF_RE.findall(html):
        if href.startswith(("http://", "https://", "//", "data:")):
            continue
        if not (DOCS / href).exists():
            errs.append("index.html 引用的样式不存在：{}".format(href))

    if errs:
        print("STATIC PAGE FAIL（{} 项）".format(len(errs)))
        for e in errs:
            print(" -", e)
        return 1
    print("STATIC PAGE PASS：app.js 引用 {} 个元素 id，index.html 全部存在".format(len(used_ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())