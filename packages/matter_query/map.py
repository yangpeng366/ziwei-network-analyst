#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""具体事项 -> 宫位/因子聚焦（势能推演，非传统吉凶占断）。

匹配口径与 docs/matter.js 完全一致，两端共用 packages/matter_query/catalog.json：

- 关键词按长度加权：1 字 1.0 / 2 字 1.5 / 3 字及以上 2.0（越具体越重）
- 命中多个不同关键词，再乘覆盖系数 1 + 0.25 * (命中数 - 1)
- 得分最高者为「主事项」；得分 >= max(1.5, 主分 * 0.4) 的其余类别算「兼看」
- 主事项与兼看的宫位取并集（上限 6 宫），因子取并集（上限 5 项）
- 时间问句（什么时候/哪年/近期…）补入 F4_tempo
- general 为兜底类：没有任何具体类别命中时才启用，此时 matched=False，
  事实卡展开十二宫交由解读方自行取用
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("catalog.json")
_CATALOG: dict[str, Any] = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))

MATTER_CATALOG: list[dict[str, Any]] = _CATALOG["categories"]
TIME_KEYWORDS: list[str] = list(_CATALOG.get("time_keywords") or [])
GENERAL_ID = "general"

MAX_PALACES = 6
MAX_FACTORS = 5
MAX_SECONDARY = 2
MIN_SECONDARY_SCORE = 1.5
SECONDARY_RATIO = 0.4
LABEL_SEP = "＋"


def _kw_weight(k: str) -> float:
    """关键词越具体权重越高。"""
    n = len(k)
    if n <= 1:
        return 1.0
    if n == 2:
        return 1.5
    return 2.0


def _score_category(cat: dict[str, Any], q: str) -> tuple[float, list[str]]:
    hits = [k for k in (cat.get("keywords") or []) if k and k in q]
    if not hits:
        return 0.0, []
    base = sum(_kw_weight(k) for k in hits)
    return base * (1.0 + 0.25 * (len(hits) - 1)), hits


def _general_cat() -> dict[str, Any]:
    return next(c for c in MATTER_CATALOG if c["id"] == GENERAL_ID)


def _fallback_focus(query: str) -> dict[str, Any]:
    """兜底：没有具体事项可归时走整体态势，并标记为未命中（事实卡展开十二宫）。"""
    cat = _general_cat()
    return {
        "query": query,
        "matched": False,
        "matter_id": cat["id"],
        "matter_ids": [cat["id"]],
        "label": cat["label"],
        "labels": [cat["label"]],
        "secondary_labels": [],
        "palaces": list(cat["palaces"]),
        "focus_factors": list(cat["focus_factors"]),
        "lens": cat["lens"],
        "hit_keywords": [],
    }


def resolve_matter(text: str | None) -> dict[str, Any]:
    """把一句人话映射到「主事项 + 兼看事项 + 相关宫位 + 关注因子」。"""
    q = (text or "").strip()
    if not q:
        return _fallback_focus(q)

    scored: list[dict[str, Any]] = []
    for idx, cat in enumerate(MATTER_CATALOG):
        if cat.get("fallback"):
            continue
        score, hits = _score_category(cat, q)
        if score > 0:
            scored.append({"idx": idx, "cat": cat, "score": score, "hits": hits})
    if not scored:
        return _fallback_focus(q)

    scored.sort(key=lambda x: (-x["score"], x["idx"]))
    primary = scored[0]
    threshold = max(MIN_SECONDARY_SCORE, primary["score"] * SECONDARY_RATIO)
    secondaries = [s for s in scored[1:] if s["score"] >= threshold][:MAX_SECONDARY]

    ordered = [primary] + secondaries

    palaces: list[str] = []
    for s in ordered:
        for p in s["cat"].get("palaces") or []:
            if p not in palaces:
                palaces.append(p)
    palaces = palaces[:MAX_PALACES]

    factors: list[str] = []
    for s in ordered:
        for f in s["cat"].get("focus_factors") or []:
            if f not in factors:
                factors.append(f)
    if any(t in q for t in TIME_KEYWORDS) and "F4_tempo" not in factors:
        factors.append("F4_tempo")
    factors = factors[:MAX_FACTORS]

    labels = [s["cat"]["label"] for s in ordered]
    lens = primary["cat"]["lens"]
    for s in secondaries:
        lens += " 同时看「{}」：{}".format(s["cat"]["label"], s["cat"]["lens"])

    hit_keywords: list[str] = []
    for s in ordered:
        for k in s["hits"]:
            if k not in hit_keywords:
                hit_keywords.append(k)

    return {
        "query": q,
        "matched": True,
        "matter_id": primary["cat"]["id"],
        "matter_ids": [s["cat"]["id"] for s in ordered],
        "label": labels[0] if len(labels) == 1 else LABEL_SEP.join(labels),
        "labels": labels,
        "secondary_labels": labels[1:],
        "palaces": palaces,
        "focus_factors": factors,
        "lens": lens,
        "hit_keywords": hit_keywords,
    }


def _palace_pressure(payload: dict[str, Any], palace: str) -> float | None:
    metrics = payload.get("metrics") or {}
    for row in metrics.get("ji_fragility") or []:
        if str(row.get("palace")) == palace:
            try:
                return float(row.get("ji_pressure"))
            except (TypeError, ValueError):
                return None
    return None


def _keystones_on_palaces(payload: dict[str, Any], palaces: set[str]) -> list[dict[str, Any]]:
    metrics = payload.get("metrics") or {}
    out = []
    for ks in metrics.get("keystones") or []:
        if str(ks.get("palace")) in palaces:
            out.append(ks)
    return out


def explain_matter(payload: dict[str, Any], matter_text: str | None) -> dict[str, Any]:
    """在已有四因子 payload 上，生成具体事项聚焦白话。"""
    focus = resolve_matter(matter_text)
    palaces = focus["palaces"]
    pset = set(palaces)

    pressures = []
    for p in palaces:
        v = _palace_pressure(payload, p)
        if v is not None:
            pressures.append({"palace": p, "ji_pressure": v})
    pressures.sort(key=lambda x: x["ji_pressure"], reverse=True)

    carriers = _keystones_on_palaces(payload, pset)
    factors = ((payload.get("factors") or {}).get("factors")) or {}
    factor_bits = []
    for fid in focus["focus_factors"]:
        block = factors.get(fid) or {}
        reading = block.get("reading")
        score = block.get("score")
        if reading is not None:
            factor_bits.append("{}:{}".format(fid, reading) + ("({})".format(score) if score is not None else ""))

    if pressures:
        hot = "、".join("{}({})".format(x["palace"], x["ji_pressure"]) for x in pressures[:3])
        risk = "与本题相关的忌压热区偏在：{}。宜留缓冲，不把同一处连续加压。".format(hot)
    else:
        risk = "本题相关宫位上，活跃层忌压热区不明显；仍建议看承重是否过载。"

    if carriers:
        carry = "、".join("{}@{}".format(c.get("name"), c.get("palace")) for c in carriers[:4])
        carry_txt = "落在本题宫位上的承重星：{}。".format(carry)
    else:
        carry_txt = "本题宫位上暂未见最顶级承重星；力量可能来自邻宫或借对。"

    summary = "就「{}」看：优先宫位 {}。{}".format(focus["label"], "、".join(palaces), focus["lens"])
    plain = " ".join([summary, carry_txt, risk, "结论只标势能方向与可觉察点，不作吉凶判决。"])

    return {
        "focus": focus,
        "related_pressures": pressures,
        "related_keystones": [
            {"name": c.get("name"), "palace": c.get("palace"), "score": c.get("score")}
            for c in carriers[:6]
        ],
        "factor_snapshot": factor_bits,
        "plain": plain,
        "actions": [
            "先盯本题宫位的承重星与忌压，再看是否撞上 F4 换轨窗口。",
            "把建议落成可逆的小动作（留缓冲、分摊负荷、错峰决策），不要一次梭哈。",
            "六亲/婚恋/健康仅参考受限；重大决策请结合现实信息与专业意见。",
        ],
        "disclaimer": "事项聚焦=盘面房间打光，不是卜卦判定吉凶。",
    }