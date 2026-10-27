#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成静态站数据：site/data/charts.js（双击 HTML 也能跑，无需服务器）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import MATTER_CATALOG  # noqa: E402
from timeline.sweep import sweep_payload  # noqa: E402

OUT = ROOT / "docs" / "data" / "charts.js"

# 演示盘列表：样例盘 + 两个真实 1990 生盘
CHARTS = [
    ("sample", "演示盘（1990-05-15 辰时）", ROOT / "fixtures" / "sample-chart.json"),
    ("real-a", "真实盘 A（1990-01-01 子时）", ROOT / "fixtures" / "real-1990" / "1990-01-01-0-male.json"),
    ("real-b", "真实盘 B（1990-09-20 巳时）", ROOT / "fixtures" / "real-1990" / "1990-09-20-6-male.json"),
]
SWEEP_FROM, SWEEP_TO = 2015, 2050


def load_chart(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    charts = []
    for cid, label, path in CHARTS:
        if not path.exists():
            print("skip (missing):", path)
            continue
        chart = load_chart(path)
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
        # 逐年推演（自带 factors / plain）
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
        # 基准年（当年）完整 payload
        cur_year = int((chart.get("birthInfo") or {}).get("year") or 2000) + int(chart.get("currentAge") or 30) - 1
        c2 = dict(chart)
        c2["asOfYear"] = cur_year
        from timeline.sweep import chart_for_year  # noqa: PLC0415
        from hypergraph.chart2hypergraph import build_hypergraph, compute_core_factors, compute_metrics  # noqa: PLC0415

        c3 = chart_for_year(chart, cur_year)
        hg = build_hypergraph(c3)
        metrics = compute_metrics(hg)
        factors = compute_core_factors(hg, metrics)
        payload = {"hypergraph": hg, "metrics": metrics, "factors": factors}
        plain = explain_payload(payload)
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
        "generated_by": "scripts/build-site.py",
        "sweep_range": [SWEEP_FROM, SWEEP_TO],
        "matters": [
            {"id": c["id"], "label": c["label"], "keywords": c["keywords"], "palaces": c["palaces"], "lens": c["lens"]}
            for c in MATTER_CATALOG
        ],
        "charts": charts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text("window.ZIWEI_DATA = " + body + ";\n", encoding="utf-8")
    print("wrote:", OUT, OUT.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())