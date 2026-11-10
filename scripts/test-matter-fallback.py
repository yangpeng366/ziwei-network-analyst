#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「问法没被识别」兜底提示回归：CLI 与静态站必须同时可见，且文案逐字同源。

锁四件事：
1. 问题落 general 时，Python 侧 focus 带 suggestions + hint（非空）
2. CLI ask.py 把同一句提示单独打一行，并写进提示包（【问法提示】）
3. 静态站真跑 docs/app.js（node + 最小 DOM 桩），#matter-hint 的 DOM 文本与 CLI 逐字一致
4. 命中具体类别时，`#matter-hint` 必须清空并隐藏，不许误报「没识别」

文案唯一来源是 packages/matter_query/catalog.json 的 fallback_hint；
本检查只比对结果，不复制字面量。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from matter_query.map import resolve_matter  # noqa: E402

ASK_PY = ROOT / "scripts" / "ask.py"
DOM_JS = ROOT / "scripts" / "matter-fallback-dom.js"
INDEX_HTML = ROOT / "docs" / "index.html"
CORPUS = ROOT / "fixtures" / "question-corpus.json"

MATCHED_Q = "今年适合跳槽吗"


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _general_query() -> str:
    if CORPUS.exists():
        cases = json.loads(CORPUS.read_text(encoding="utf-8")).get("cases") or []
        for case in cases:
            if case.get("matter_id") == "general" and (case.get("q") or "").strip():
                return case["q"]
    return "看看我最近怎么样"


def _dom(query: str) -> dict:
    node = shutil.which("node")
    if not node:
        raise SystemExit("找不到 node，无法校验静态站 DOM 文本")
    proc = subprocess.run(
        [node, str(DOM_JS), query], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        raise SystemExit("node 跑 matter-fallback-dom.js 失败：\n" + (proc.stderr or proc.stdout)[:1200])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("DOM 桩输出不是合法 JSON：{}".format(exc))


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ASK_PY), *args],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )


def main() -> int:
    _force_utf8_stdout()
    errs: list[str] = []

    gq = _general_query()
    g_focus = resolve_matter(gq)
    g_hint = g_focus.get("hint") or ""
    if g_focus["matched"]:
        errs.append("语料里的 general 样例现在命中了具体类别，换一条样例：{}".format(gq))
    if not g_hint:
        errs.append("{} -> general 缺 hint，CLI 与站点都无从显示".format(gq))
    if not g_focus.get("suggestions"):
        errs.append("{} -> general 缺 suggestions".format(gq))

    # 1) 静态站：DOM 文本
    dom_g = _dom(gq)
    dom_m = _dom(MATCHED_Q)
    if dom_g.get("hint") != g_hint:
        errs.append("站点 #matter-hint 文本与 Python hint 不一致：dom={!r} py={!r}".format(
            dom_g.get("hint"), g_hint))
    if dom_g.get("hidden"):
        errs.append("兜底时 #matter-hint 仍带 hidden，用户看不到提示")
    if "整体态势" not in (dom_g.get("label") or ""):
        errs.append("兜底时 #matter-label 不是整体态势：{!r}".format(dom_g.get("label")))
    if not dom_g.get("promptHasHint"):
        errs.append("站点提示包里没有【问法提示】")
    if dom_m.get("hint"):
        errs.append("命中具体类别时 #matter-hint 仍非空：{!r}".format(dom_m.get("hint")))
    if not dom_m.get("hidden"):
        errs.append("命中具体类别时 #matter-hint 未隐藏")
    if dom_m.get("promptHasHint"):
        errs.append("命中具体类别时站点提示包仍出现【问法提示】")

    # 2) CLI：单独一行 + 提示包
    cli = _cli("--demo", "--matter", gq)
    if cli.returncode != 0:
        errs.append("ask.py 兜底问句跑不通：{}".format((cli.stderr or cli.stdout)[-400:]))
        cli_hint = ""
    else:
        lines = [l.strip() for l in cli.stdout.splitlines() if l.strip()]
        hits = [l for l in lines if l == g_hint]
        cli_hint = hits[0] if hits else ""
        if not hits:
            errs.append("CLI 未按整行打印兜底提示：期望 {!r}".format(g_hint))
        elif len(hits) > 1:
            errs.append("CLI 兜底提示重复打印 {} 次".format(len(hits)))
        if cli_hint and dom_g.get("hint") != cli_hint:
            errs.append("CLI 与站点文案不一致：cli={!r} dom={!r}".format(cli_hint, dom_g.get("hint")))

    pack = _cli("--demo", "--matter", gq, "--print-only")
    if pack.returncode != 0:
        errs.append("ask.py --print-only 跑不通：{}".format((pack.stderr or pack.stdout)[-400:]))
    else:
        if "【问法提示】" + g_hint not in pack.stdout:
            errs.append("提示包里没有与 CLI 同源的【问法提示】行")
    pack_m = _cli("--demo", "--matter", MATCHED_Q, "--print-only")
    if pack_m.returncode != 0:
        errs.append("ask.py --print-only（命中）跑不通：{}".format((pack_m.stderr or pack_m.stdout)[-400:]))
    elif "【问法提示】" in pack_m.stdout:
        errs.append("命中具体类别时提示包仍出现【问法提示】")

    # 3) 元素真的在页面里（防止只有 JS 在写一个不存在的节点）
    if INDEX_HTML.exists():
        html = INDEX_HTML.read_text(encoding="utf-8")
        if 'id="matter-hint"' not in html:
            errs.append("index.html 缺 #matter-hint 元素")
    else:
        errs.append("缺 docs/index.html")

    if errs:
        print("MATTER FALLBACK FAIL（{} 项）".format(len(errs)))
        for e in errs:
            print(" -", e)
        return 1
    print("MATTER FALLBACK PASS：兜底问句 {!r} 的提示在 CLI 与站点一致（{} 字）".format(gq, len(g_hint)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
