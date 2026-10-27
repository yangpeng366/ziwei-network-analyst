#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐年推演：把命盘按流年 + 大限推进，算出 F3/F4 的时间曲线。

用途：回答「哪几年更该动、哪几年宜守」，而不是只讲某一个流年。
"""
from __future__ import annotations

import copy
from typing import Any

from hypergraph.chart2hypergraph import build_hypergraph, compute_core_factors, compute_metrics
from plain_reading.explain import explain_payload


DREAD_BANDS = {"高脆", "中脆", "偏抗造"}


def _force_utf8_stdout() -> None:
    for stream in (__import__("sys").stdout, __import__("sys").stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def birth_year_of(chart: dict[str, Any]) -> int | None:
    birth = chart.get("birthInfo") or {}
    try:
        return int(birth.get("year"))
    except (TypeError, ValueError):
        return None


def age_in_year(chart: dict[str, Any], year: int) -> int | None:
    """虚岁 = 年 - 出生年 + 1。"""
    by = birth_year_of(chart)
    if by is None:
        return None
    return int(year) - by + 1


def daxian_index_for_age(chart: dict[str, Any], age: int | None) -> int | None:
    """按 startAge/endAge 找当年所处大限；找不到则沿用盘上的当前大限。"""
    daxians = chart.get("daXians") or []
    if age is not None:
        for i, dx in enumerate(daxians):
            s, e = dx.get("startAge"), dx.get("endAge")
            try:
                if s is not None and e is not None and int(s) <= age <= int(e):
                    return i
            except (TypeError, ValueError):
                continue
        # 超出表尾（少年/老年段）时，取最近的一档
        if daxians:
            starts = []
            for dx in daxians:
                try:
                    starts.append(int(dx.get("startAge", 0)))
                except (TypeError, ValueError):
                    continue
            if starts:
                return max(range(len(starts)), key=lambda i: (starts[i] <= age, starts[i]))
    cur = chart.get("currentDaXianIndex")
    return cur if isinstance(cur, int) else None


def daxian_label(chart: dict[str, Any], index: int | None) -> str | None:
    daxians = chart.get("daXians") or []
    if index is None or not (0 <= index < len(daxians)):
        return None
    dx = daxians[index]
    return f"{dx.get('startAge')}-{dx.get('endAge')}·{dx.get('palaceName')}"


def boundary_distance(chart: dict[str, Any], age: int | None) -> tuple[int | None, bool]:
    """距最近的大限交接还有几年；是否为大限起始年。"""
    daxians = chart.get("daXians") or []
    if age is None or not daxians:
        return None, False
    best: int | None = None
    for dx in daxians:
        try:
            s = int(dx.get("startAge"))
            e = int(dx.get("endAge"))
        except (TypeError, ValueError):
            continue
        for boundary in (s, e + 1):
            d = abs(age - boundary)
            if best is None or d < best:
                best = d
    for i, dx in enumerate(daxians):
        try:
            s = int(dx.get("startAge"))
        except (TypeError, ValueError):
            continue
        if age == s:
            return best, True
    return best, False


def chart_for_year(chart: dict[str, Any], year: int) -> dict[str, Any]:
    """把盘投影到指定年份：设流年、虚岁、当年大限。"""
    c = copy.deepcopy(chart)
    c["asOfYear"] = int(year)
    age = age_in_year(c, year)
    if age is not None:
        c["currentAge"] = age
    idx = daxian_index_for_age(c, age)
    if idx is not None:
        c["currentDaXianIndex"] = idx
    return c


def year_factors(chart: dict[str, Any], year: int) -> dict[str, Any]:
    c = chart_for_year(chart, year)
    hg = build_hypergraph(c)
    metrics = compute_metrics(hg)
    factors = compute_core_factors(hg, metrics)
    f = factors.get("factors") or {}
    age = age_in_year(c, year)
    idx = c.get("currentDaXianIndex")
    dist, is_start = boundary_distance(c, age)
    return {
        "year": int(year),
        "age": age,
        "daxian_index": idx,
        "daxian_label": daxian_label(c, idx),
        "years_to_boundary": dist,
        "is_daxian_start": is_start,
        "F1": (f.get("F1_community") or {}).get("score"),
        "F1_reading": (f.get("F1_community") or {}).get("reading"),
        "F2": (f.get("F2_keystone") or {}).get("score"),
        "F2_reading": (f.get("F2_keystone") or {}).get("reading"),
        "F3": (f.get("F3_fragility") or {}).get("score"),
        "F3_reading": (f.get("F3_fragility") or {}).get("reading"),
        "F4": (f.get("F4_tempo") or {}).get("score"),
        "F4_reading": (f.get("F4_tempo") or {}).get("reading"),
        "phase_proximity": metrics.get("phase_proximity"),
        "top_keystone": (metrics.get("keystones") or [{}])[0].get("name") if metrics.get("keystones") else None,
        "keystones": [
            {"name": k.get("name"), "palace": k.get("palace"), "score": k.get("score")}
            for k in (metrics.get("keystones") or [])[:4]
        ],
        "ji_hotspots": [
            {"palace": r.get("palace"), "ji_pressure": r.get("ji_pressure")}
            for r in (metrics.get("ji_fragility") or [])[:3]
        ],
    }


def sweep(chart: dict[str, Any], from_year: int, to_year: int) -> dict[str, Any]:
    if to_year < from_year:
        from_year, to_year = to_year, from_year
    span = to_year - from_year + 1
    if span > 120:
        span = 120
        to_year = from_year + span - 1

    rows = [year_factors(chart, y) for y in range(from_year, to_year + 1)]

    # 大限交接年
    transitions = []
    for i in range(1, len(rows)):
        if rows[i]["daxian_index"] != rows[i - 1]["daxian_index"]:
            transitions.append(
                {
                    "year": rows[i]["year"],
                    "from": rows[i - 1].get("daxian_label"),
                    "to": rows[i].get("daxian_label"),
                }
            )

    def _rank(key: str, reverse: bool = True) -> list[dict[str, Any]]:
        vals = [r for r in rows if r.get(key) is not None]
        vals.sort(key=lambda r: r[key], reverse=reverse)
        return vals

    peak_fragility = _rank("F3")[:3]
    peak_rewrite = _rank("F4")[:3]

    # 相对自身基线：避免固定阈值在不同盘上失真
    f3_vals = sorted(r["F3"] for r in rows if r.get("F3") is not None)
    median_f3 = f3_vals[len(f3_vals) // 2] if f3_vals else 0.0
    risk_gate = max(0.62, median_f3 + 0.08)

    move_years = [r["year"] for r in rows if (r.get("years_to_boundary") or 9) <= 1]
    hold_years = [
        r["year"]
        for r in rows
        if (r.get("years_to_boundary") or 9) >= 3 and (r.get("F3") or 1.0) <= median_f3
    ]
    risk_years = [r["year"] for r in rows if (r.get("F3") or 0) >= risk_gate]

    transition_years = [t["year"] for t in transitions]
    if rows and rows[0].get("is_daxian_start"):
        transition_years = [rows[0]["year"]] + transition_years

    return {
        "range": [from_year, to_year],
        "rows": rows,
        "daxian_transitions": transitions,
        "transition_years": transition_years,
        "move_years": move_years,
        "hold_years": hold_years,
        "risk_years": risk_years,
        "median_F3": round(median_f3, 4),
        "risk_gate": round(risk_gate, 4),
        "peak_fragility": peak_fragility,
        "peak_rewrite": peak_rewrite,
        "steady_years": hold_years,
        "active_years": risk_years,
        "summary": summarize(rows, transitions, hold_years),
    }


def summarize(rows: list[dict[str, Any]], transitions: list[dict[str, Any]], steady_years: list[int]) -> str:
    if not rows:
        return "区间为空。"
    parts: list[str] = []
    if transitions:
        t = transitions[0]
        parts.append(f"区间内大限交接 {len(transitions)} 次，首次在 {t['year']} 年（{t['from']} → {t['to']}）。")
    else:
        parts.append("区间内大限未交接，属同一剧本深耕期。")
    hot = max(rows, key=lambda r: r.get("F3") or 0)
    parts.append(f"冲击脆弱峰值在 {hot['year']} 年（F3={hot.get('F3')}，{hot.get('F3_reading')}）。")
    rw = max(rows, key=lambda r: r.get("F4") or 0)
    if (rw.get("F4") or 0) >= 0.8:
        parts.append(f"结构重写压力最高在 {rw['year']} 年（F4={rw.get('F4')}），换轨意愿多来自这里。")
    if steady_years:
        shown = "、".join(str(y) for y in steady_years[:10])
        more = "…" if len(steady_years) > 10 else ""
        parts.append(f"相对平缓年：{shown}{more}（共 {len(steady_years)} 年）。")
    return "".join(parts)


def sweep_payload(chart: dict[str, Any], from_year: int, to_year: int) -> dict[str, Any]:
    """完整产物：曲线数据 + 白话解读（供网页/提示包共用）。"""
    data = sweep(chart, from_year, to_year)
    rows = data["rows"]
    lines = [
        f"逐年推演 {from_year}–{to_year}：",
        data["summary"],
    ]
    risk_years = data.get("risk_years") or []
    if risk_years:
        lines.append(
            "冲击吃紧的年份：" + "、".join(str(y) for y in risk_years[:8]) + "（宜留缓冲、别连续加压）。"
        )
    ty = data.get("transition_years") or []
    if ty:
        lines.append(
            "大限交接年：" + "、".join(str(y) for y in ty[:6]) + "（结构改写最强，换轨想法多在此起意）。"
        )
    my = data.get("move_years") or []
    if my:
        lines.append(
            "宜动窗口（贴近交接）：" + "、".join(str(y) for y in my[:8]) + "（想换轨、换重心多在此起意）。"
        )
    hy = data.get("hold_years") or []
    if hy:
        shown = "、".join(str(y) for y in hy[:10])
        more = "…" if len(hy) > 10 else ""
        lines.append(f"相对宜守的年份：{shown}{more}（共 {len(hy)} 年，宜深耕、少折腾）。")
    data["plain"] = {
        "summary": "".join(lines),
        "timeline_plain": lines,
        "disclaimer": "流年只改当下张力，不改你是谁；窗口提示非指令。",
    }
    return data