#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build high/low F1 calibration charts from sample-chart.json."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "fixtures" / "sample-chart.json"
OUT_DIR = ROOT / "fixtures" / "calibration"


def palace_map(chart: dict) -> dict[str, dict]:
    return {p["name"]: p for p in chart["palaces"]}


def clear_sihua(palace: dict) -> None:
    for s in palace.get("stars") or []:
        if "siHua" in s:
            s["siHua"] = None
    palace["selfSihua"] = []


def set_star_sihua(palace: dict, star_name: str, sihua: str | None) -> None:
    for s in palace.get("stars") or []:
        if s.get("name") == star_name:
            s["siHua"] = sihua
            return
    # append a marker star if missing
    palace.setdefault("stars", []).append(
        {
            "name": star_name,
            "type": "main",
            "brightness": "bright",
            "brightnessRaw": "旺",
            "siHua": sihua,
        }
    )


def make_high(base: dict) -> dict:
    chart = copy.deepcopy(base)
    chart["birthInfo"] = {
        **chart.get("birthInfo", {}),
        "note": "calibration:high-community",
    }
    pm = palace_map(chart)
    for name in ("交友", "夫妻", "迁移"):
        if name in pm:
            clear_sihua(pm[name])
            pm[name]["isEmpty"] = False
    # positive flow into community
    set_star_sihua(pm["交友"], "贪狼", "禄")
    set_star_sihua(pm["夫妻"], "巨门", "科")
    set_star_sihua(pm["迁移"], "破军", "权")
    # move 忌 off community if present
    if "廉贞" in [s.get("name") for s in pm["迁移"].get("stars") or []]:
        set_star_sihua(pm["迁移"], "廉贞", None)
    # park 忌 on 疾厄 instead
    if "疾厄" in pm:
        set_star_sihua(pm["疾厄"], "太阳", "忌")
    return chart


def make_low(base: dict) -> dict:
    chart = copy.deepcopy(base)
    chart["birthInfo"] = {
        **chart.get("birthInfo", {}),
        "note": "calibration:low-community",
    }
    pm = palace_map(chart)
    for name in ("交友", "夫妻", "迁移"):
        if name in pm:
            clear_sihua(pm[name])
    set_star_sihua(pm["交友"], "贪狼", "忌")
    set_star_sihua(pm["迁移"], "廉贞", "忌")
    set_star_sihua(pm["迁移"], "破军", None)
    # empty 夫妻 with borrow friction
    pm["夫妻"]["isEmpty"] = True
    pm["夫妻"]["stars"] = []
    pm["夫妻"]["borrowedFromBranch"] = pm["兄弟"]["branch"]
    pm["夫妻"]["borrowedStars"] = ["天相"]
    # strip positive community feeders from 财帛禄 if it spills via sanfang — keep natal 禄 but away is ok
    return chart


def main() -> int:
    base = json.loads(SAMPLE.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    high = make_high(base)
    low = make_low(base)
    (OUT_DIR / "community-high.json").write_text(
        json.dumps(high, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "community-low.json").write_text(
        json.dumps(low, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote", OUT_DIR / "community-high.json")
    print("wrote", OUT_DIR / "community-low.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())