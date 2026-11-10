#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事项映射回归测试。

四件事：
1. 目录自检：类别 id 唯一、关键词不跨类别重名、general 存在且为兜底类
2. 语料回归：fixtures/question-corpus.json 逐条核对归类结果与相关宫位
3. 兜底提示：问题落 general 时 suggestions 按 catalog 顺序每类前 4 词、hint 非空；
   命中具体类别时不得出现 suggestions / hint（否则界面会误报「没识别」）
4. 前后端一致：同一份语料交给 docs/matter.js（node）跑一遍，结果必须逐字相同
   —— 含 suggestions / hint；CLI 实际打印的提示行也必须与同一算法一致
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from matter_query.map import (  # noqa: E402
    MATTER_CATALOG,
    MAX_SUGGESTIONS_PER_CLASS,
    TIME_KEYWORDS,
    resolve_matter,
)
from matter_query.prompt_pack import build_user_prompt  # noqa: E402

CORPUS = ROOT / "fixtures" / "question-corpus.json"
PARITY_JS = ROOT / "scripts" / "matter-parity.js"
ASK_PY = ROOT / "scripts" / "ask.py"

COMPARE_FIELDS = (
    "matched",
    "matter_id",
    "matter_ids",
    "label",
    "palaces",
    "focus_factors",
    "lens",
    "hit_keywords",
    "suggestions",
    "hint",
)


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def check_catalog() -> list[str]:
    errs: list[str] = []
    ids = [c["id"] for c in MATTER_CATALOG]
    if len(ids) != len(set(ids)):
        errs.append("类别 id 有重复")
    if "general" not in ids:
        errs.append("缺少 general 兜底类")
    general = next((c for c in MATTER_CATALOG if c["id"] == "general"), None)
    if general is not None and not general.get("fallback"):
        errs.append("general 必须标记 fallback=true")
    if general is not None and len(general.get("focus_factors") or []) != 4:
        errs.append("general 的 focus_factors 应为四项")
    seen: dict[str, str] = {}
    for c in MATTER_CATALOG:
        for k in c.get("keywords") or []:
            if not k:
                errs.append("空关键词：{}".format(c["id"]))
                continue
            if k in seen:
                errs.append("关键词跨类别重名：{!r} 同时属于 {} 与 {}".format(k, seen[k], c["id"]))
            else:
                seen[k] = c["id"]
        if not c.get("palaces"):
            errs.append("类别缺宫位：{}".format(c["id"]))
    return errs


def check_corpus(cases: list[dict]) -> list[str]:
    errs: list[str] = []
    for case in cases:
        q = case.get("q") or ""
        f = resolve_matter(q)
        label = case.get("q") or "(空)"
        if f["matter_id"] != case.get("matter_id"):
            errs.append("{} -> 主事项 {}，期望 {}".format(label, f["matter_id"], case.get("matter_id")))
        if f["matter_ids"] != case.get("matter_ids"):
            errs.append("{} -> 事项集合 {}，期望 {}".format(label, f["matter_ids"], case.get("matter_ids")))
        if f["palaces"] != case.get("palaces"):
            errs.append("{} -> 宫位 {}，期望 {}".format(label, f["palaces"], case.get("palaces")))
        if "matched" in case and f["matched"] != case["matched"]:
            errs.append("{} -> matched {}，期望 {}".format(label, f["matched"], case["matched"]))
        for fid in case.get("focus_factors_include") or []:
            if fid not in f["focus_factors"]:
                errs.append("{} -> 缺关注因子 {}".format(label, fid))
    return errs


def _general_case(cases: list[dict]) -> dict | None:
    """取一条非空问句的 general 样例（空串也算 general，但没法跑 CLI）。"""
    for case in cases:
        if case.get("matter_id") == "general" and (case.get("q") or "").strip():
            return case
    return None


def check_suggestions(cases: list[dict]) -> list[str]:
    """兜底提示的字段契约：顺序、条数、词源、非兜底时不出现。"""
    errs: list[str] = []
    classes = [c for c in MATTER_CATALOG if not c.get("fallback")]
    order = [c["id"] for c in classes]
    by_id = {c["id"]: c for c in MATTER_CATALOG}

    general_cases = [c for c in cases if c.get("matter_id") == "general"]
    if not general_cases:
        errs.append("语料里缺少 general 兜底样例，无法锁提示行为")

    for case in general_cases:
        q = case.get("q") or ""
        tag = q or "(空)"
        f = resolve_matter(q)
        sugs = f.get("suggestions")
        if not sugs:
            errs.append("{} -> general 缺 suggestions".format(tag))
            continue
        got_order = [s.get("matter_id") for s in sugs]
        if got_order != order:
            errs.append("{} -> suggestions 顺序/集合 {}，期望 catalog 顺序 {}".format(tag, got_order, order))
        for item in sugs:
            mid = item.get("matter_id")
            cat = by_id.get(mid) or {}
            kws = [k for k in (cat.get("keywords") or []) if k]
            expect = kws[:MAX_SUGGESTIONS_PER_CLASS]
            got = item.get("keywords") or []
            if got != expect:
                errs.append("{} -> {} 的 suggestions 词 {!r}，期望该类前 {} 个关键词 {!r}".format(
                    tag, mid, got, MAX_SUGGESTIONS_PER_CLASS, expect))
            if len(got) != MAX_SUGGESTIONS_PER_CLASS:
                errs.append("{} -> {} 的 suggestions 应给满 {} 词，实为 {}".format(
                    tag, mid, MAX_SUGGESTIONS_PER_CLASS, len(got)))
            if item.get("label") != cat.get("label"):
                errs.append("{} -> {} 的 suggestions 标签 {!r} 与目录 {!r} 不一致".format(
                    tag, mid, item.get("label"), cat.get("label")))
        hint = f.get("hint") or ""
        if not hint:
            errs.append("{} -> general 缺 hint".format(tag))
            continue
        for item in sugs[:1]:
            sample = (item.get("keywords") or [""])[0]
            if sample and sample not in hint:
                errs.append("{} -> hint 里没带可试说法（缺 {!r}）".format(tag, sample))

    for case in cases:
        q = case.get("q") or ""
        f = resolve_matter(q)
        if f["matched"] and ("suggestions" in f or "hint" in f):
            errs.append("{} -> 命中具体类别却仍带 suggestions/hint".format(q))
    return errs


def check_cli_hint(cases: list[dict]) -> list[str]:
    """CLI 必须把同一句提示单独打一行；提示包里也要带上。"""
    errs: list[str] = []
    case = _general_case(cases)
    if not case:
        return ["语料里没有非空 general 样例，无法核对 CLI 提示"]
    q = case["q"]
    hint = resolve_matter(q).get("hint") or ""
    if not hint:
        return ["{} -> general 缺 hint，CLI 无从打印".format(q)]

    proc = subprocess.run(
        [sys.executable, str(ASK_PY), "--demo", "--matter", q],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        return ["ask.py 跑不通：{}".format((proc.stderr or proc.stdout or "")[-400:])]
    lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    hits = [l for l in lines if l == hint]
    if not hits:
        errs.append("CLI 未按整行打印兜底提示：期望一行 {!r}".format(hint))
    elif len(hits) > 1:
        errs.append("CLI 兜底提示重复打印 {} 次".format(len(hits)))

    matched = next((c for c in cases if c.get("matter_id") not in (None, "general")), None)
    mq = (matched or {}).get("q") or ""
    if mq:
        payload = {"matter": {"focus": resolve_matter(mq)}}
        text = build_user_prompt(payload, mq)
        if "【问法提示】" in text:
            errs.append("命中具体类别时提示包不应出现「问法提示」：{}".format(mq))
    payload = {"matter": {"focus": resolve_matter(q)}}
    text = build_user_prompt(payload, q)
    if "【问法提示】" not in text or hint not in text:
        errs.append("兜底时提示包未写入问法提示：{}".format(q))
    return errs


def check_parity(cases: list[dict]) -> list[str]:
    errs: list[str] = []
    node = shutil.which("node")
    if not node:
        return ["找不到 node，无法校验前后端一致性"]
    proc = subprocess.run(
        [node, str(PARITY_JS)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        return ["node 跑 matter-parity.js 失败：{}".format((proc.stderr or "").strip()[:400])]
    try:
        js_rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return ["matter-parity.js 输出不是合法 JSON：{}".format(exc)]
    if len(js_rows) != len(cases):
        return ["前后端语料条数不一致：js={} py={}".format(len(js_rows), len(cases))]
    for case, js in zip(cases, js_rows):
        f = resolve_matter(case.get("q") or "")
        for field in COMPARE_FIELDS:
            if js.get(field) != f.get(field):
                errs.append(
                    "前后端不一致 [{}] {}：js={!r} py={!r}".format(
                        case.get("q") or "(空)", field, js.get(field), f.get(field)
                    )
                )
    return errs


def main() -> int:
    _force_utf8_stdout()
    if not CORPUS.exists():
        print("缺少 fixtures/question-corpus.json")
        return 1
    cases = json.loads(CORPUS.read_text(encoding="utf-8")).get("cases") or []
    if not cases:
        print("语料为空")
        return 1

    errs = check_catalog()
    errs += check_corpus(cases)
    errs += check_suggestions(cases)
    errs += check_cli_hint(cases)
    errs += check_parity(cases)

    if errs:
        print("MATTER MAPPING FAIL（{} 项）".format(len(errs)))
        for e in errs[:40]:
            print(" -", e)
        return 1
    print("MATTER MAPPING PASS：语料 {} 条，目录 {} 类，关键词 {} 个，前后端一致".format(
        len(cases), len(MATTER_CATALOG), sum(len(c.get("keywords") or []) for c in MATTER_CATALOG)
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())