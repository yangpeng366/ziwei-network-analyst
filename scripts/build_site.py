#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成静态站数据：docs/data/charts.js（双击 index.html 亦可运行，无需服务器）。

同一份数据也用于本地演示与 GitHub Pages，因此生成必须可复现：
- 浮点统一四舍五入到 4 位
- 固定 LF 换行
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import MATTER_CATALOG, TIME_KEYWORDS  # noqa: E402
from matter_query.facts import build_facts, twelve_palaces  # noqa: E402
from matter_query.prompt_pack import render_facts_text  # noqa: E402
from timeline.sweep import sweep_payload, chart_for_year  # noqa: E402
from hypergraph.chart2hypergraph import build_hypergraph, compute_core_factors, compute_metrics  # noqa: E402

OUT = ROOT / "docs" / "data" / "charts.js"

# 演示盘列表：样例盘 + 两个真实 1990 生盘
CHARTS = [
    ("sample", "演示盘（1990-05-15 辰时）", ROOT / "fixtures" / "sample-chart.json"),
    ("real-a", "真实盘 A（1990-01-01 子时）", ROOT / "fixtures" / "real-1990" / "1990-01-01-0-male.json"),
    ("real-b", "真实盘 B（1990-09-20 巳时）", ROOT / "fixtures" / "real-1990" / "1990-09-20-6-male.json"),
]
SWEEP_FROM, SWEEP_TO = 2015, 2050


def _round_floats(obj: Any) -> Any:
    """递归四舍五入浮点，保证跨 Python 版本一致。"""
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v) for v in obj]
    return obj


def build_payload() -> dict:
    charts = []
    for cid, label, path in CHARTS:
        if not path.exists():
            print("skip (missing):", path)
            continue
        chart = json.loads(path.read_text(encoding="utf-8"))
        birth = chart.get("birthInfo") or {}
        base = {
            "id": cid,
            "label": label,
            "birth": {
                "year": birth.get("year"),
                "month": birth.get("month"),
                "day": birth.get("day"),
                "hour": birth.get("hour"),
                "gender": birth.get("gender"),
                "city": birth.get("city"),
            },
            "daXian": [
                {
                    "startAge": dx.get("startAge"),
                    "endAge": dx.get("endAge"),
                    "palaceName": dx.get("palaceName"),
                }
                for dx in (chart.get("daXians") or [])
            ],
        }
        tl = sweep_payload(chart, SWEEP_FROM, SWEEP_TO)
        base["timeline"] = {
            "range": tl["range"],
            "rows": tl["rows"],
            "daxian_transitions": tl["daxian_transitions"],
            "transition_years": tl.get("transition_years") or [],
            "move_years": tl.get("move_years") or [],
            "hold_years": tl.get("hold_years") or [],
            "risk_years": tl.get("risk_years") or [],
            "summary": tl["summary"],
        }
        cur_year = int(birth.get("year") or 2000) + int(chart.get("currentAge") or 30) - 1
        c3 = chart_for_year(chart, cur_year)
        hg = build_hypergraph(c3)
        metrics = compute_metrics(hg)
        factors = compute_core_factors(hg, metrics)
        payload = {"hypergraph": hg, "metrics": metrics, "factors": factors}
        plain = explain_payload(payload)
        all_names = [row["name"] for row in twelve_palaces(chart)]
        facts = build_facts(chart, all_names, cards_title="全盘十二宫（详卡）")
        base["facts_text"] = render_facts_text(facts)
        base["current"] = {
            "year": cur_year,
            "one_liner": factors.get("one_liner"),
            "factors": factors.get("factors"),
            "plain": plain,
            "keystones": metrics.get("keystones") or [],
            "ji_fragility": metrics.get("ji_fragility") or [],
            "metrics": {
                "connectivity": metrics.get("connectivity"),
                "resilience": metrics.get("resilience"),
                "phase_proximity": metrics.get("phase_proximity"),
            },
            "meta": (hg.get("meta") or {}),
        }
        charts.append(base)
        print("added:", cid, label)

    data = {
        "generated_by": "scripts/build_site.py",
        "sweep_range": [SWEEP_FROM, SWEEP_TO],
        "time_keywords": list(TIME_KEYWORDS),
        "matters": [
            {
                "id": c["id"],
                "label": c["label"],
                "keywords": c["keywords"],
                "palaces": c["palaces"],
                "focus_factors": c["focus_factors"],
                "lens": c["lens"],
                "fallback": bool(c.get("fallback")),
            }
            for c in MATTER_CATALOG
        ],
        "charts": charts,
    }
    return _round_floats(data)


def serialize(data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return "window.ZIWEI_DATA = " + body + ";\n"


def write_payload(data: dict, path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(data), encoding="utf-8", newline="\n")
    return path


def main() -> int:
    data = build_payload()
    path = write_payload(data)
    print("wrote:", path, path.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
