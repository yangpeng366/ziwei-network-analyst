#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事项映射回归测试。

三件事：
1. 目录自检：类别 id 唯一、关键词不跨类别重名、general 存在且为兜底类
2. 语料回归：fixtures/question-corpus.json 逐条核对归类结果与相关宫位
3. 前后端一致：同一份语料交给 docs/matter.js（node）跑一遍，结果必须逐字相同
   —— 静态站与本地引擎共用 catalog.json，一旦算法改一边不同步，这里会立刻报错
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from matter_query.map import MATTER_CATALOG, TIME_KEYWORDS, resolve_matter  # noqa: E402

CORPUS = ROOT / "fixtures" / "question-corpus.json"
PARITY_JS = ROOT / "scripts" / "matter-parity.js"

COMPARE_FIELDS = ("matched", "matter_id", "matter_ids", "label", "palaces", "focus_factors", "lens", "hit_keywords")


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