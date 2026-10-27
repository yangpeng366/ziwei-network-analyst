#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F1 regression: community-high > sample > community-low."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
CASES = [
    ("high", ROOT / "fixtures" / "calibration" / "community-high.json"),
    ("sample", ROOT / "fixtures" / "sample-chart.json"),
    ("low", ROOT / "fixtures" / "calibration" / "community-low.json"),
]


def f1_of(chart: Path) -> float:
    subprocess.check_call([sys.executable, str(CONV), str(chart)], cwd=str(ROOT))
    payload = json.loads(chart.with_name(chart.stem + ".hypergraph.json").read_text(encoding="utf-8"))
    return float(payload["factors"]["factors"]["F1_community"]["score"])


def main() -> int:
    scores = {name: f1_of(path) for name, path in CASES}
    print("F1 scores:", scores)
    ok = True
    if not (scores["high"] > scores["sample"] > scores["low"]):
        print("FAIL: expected high > sample > low")
        ok = False
    if scores["high"] < 0.55:
        print("FAIL: high should read as 协作 (>=0.55), got", scores["high"])
        ok = False
    if scores["low"] >= 0.35:
        print("FAIL: low should read as 割裂 (<0.35), got", scores["low"])
        ok = False
    if not (0.35 <= scores["sample"] < 0.55):
        print("WARN: sample expected 拉锯 band [0.35,0.55), got", scores["sample"])
    if ok:
        print("PASS")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())