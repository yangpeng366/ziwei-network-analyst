#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize factor distribution on fixtures/real-1990 (no soft-label fitting)."""
from __future__ import annotations

import json
import statistics as stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "fixtures" / "real-1990"
OUT = ROOT / "progress" / "real-1990-distribution.json"


def main() -> int:
    rows = []
    for hg in sorted(REAL.glob("*.hypergraph.json")):
        payload = json.loads(hg.read_text(encoding="utf-8"))
        f = payload["factors"]["factors"]
        rows.append({
            "key": hg.name.replace(".hypergraph.json", ""),
            "F1": f["F1_community"]["score"],
            "F1_reading": f["F1_community"]["reading"],
            "F2": f["F2_keystone"]["score"],
            "F3": f["F3_fragility"]["score"],
            "F4": f["F4_tempo"]["score"],
        })
    if not rows:
        print("no hypergraph fixtures in", REAL)
        return 2

    def summarize(key: str) -> dict:
        xs = [r[key] for r in rows]
        return {
            "n": len(xs),
            "mean": round(stats.mean(xs), 4),
            "stdev": round(stats.pstdev(xs), 4),
            "min": round(min(xs), 4),
            "p25": round(sorted(xs)[max(0, len(xs)//4 - 1)], 4),
            "p50": round(sorted(xs)[len(xs)//2], 4),
            "p75": round(sorted(xs)[(3*len(xs))//4], 4),
            "max": round(max(xs), 4),
            "unique": len(set(xs)),
        }

    f1_reads = {}
    for r in rows:
        f1_reads[r["F1_reading"]] = f1_reads.get(r["F1_reading"], 0) + 1

    summary = {
        "n": len(rows),
        "factors": {k: summarize(k) for k in ("F1", "F2", "F3", "F4")},
        "F1_reading_counts": f1_reads,
        "policy": "distribution inspection only; corpus is position-referenced prompt material, not factor labels",
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["factors"], ensure_ascii=False, indent=2))
    print("F1 readings:", f1_reads)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())