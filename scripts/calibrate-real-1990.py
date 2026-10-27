#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"F:\github\ziwei-network-analyst")
REAL = ROOT / "fixtures" / "real-1990"
CORPUS = ROOT / "data" / "v4-sample" / "year-1990.jsonl"
CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
OUT = ROOT / "progress" / "calibration-real-1990.json"

POS = ["人缘好", "贵人", "合作", "朋友多", "人脉", "和谐", "得助", "人气", "和睦", "得力", "互助", "人缘佳"]
NEG = ["孤独", "隔阂", "不合", "离别", "难相处", "孤立", "争吵", "冷淡", "聚少离多", "波折大", "防人", "人际压力"]


def extract_dingdiao(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"【一句话定调】\s*([\s\S]{0,120})", text)
    if m:
        return m.group(1).split("【", 1)[0].strip()
    # fallback: first 120 chars of 感情总览
    m2 = re.search(r"【感情总览】\s*([\s\S]{0,120})", text)
    return (m2.group(1) if m2 else text[:120]).strip()


def soft_score(love: str, friends: str) -> tuple[float, list[str], str]:
    focus = extract_dingdiao(love) + "\n" + extract_dingdiao(friends)
    # also take first 200 of friends overview if present
    fm = re.search(r"【.*?总览】\s*([\s\S]{0,200})", friends or "")
    if fm:
        focus += "\n" + fm.group(1)
    p = n = 0
    hits = []
    for w in POS:
        if w in focus:
            p += 1
            hits.append("+" + w)
    for w in NEG:
        if w in focus:
            n += 1
            hits.append("-" + w)
    score = (p + 0.2) / (p + n + 0.4)
    return max(0.0, min(1.0, score)), hits[:12], focus[:160]


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return float("nan")
    return num / (denx * deny)


def main():
    index = json.loads((REAL / "index.json").read_text(encoding="utf-8"))
    want = {i["key"] for i in index}
    soft_map = {}
    with CORPUS.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("k") not in want:
                continue
            c = row.get("c") or {}
            score, hits, focus = soft_score(c.get("love") or "", c.get("friends") or "")
            soft_map[row["k"]] = {"soft_community": round(score, 4), "soft_hits": hits, "focus": focus}
            if len(soft_map) >= len(want):
                break

    rows = []
    for item in index:
        key = item["key"]
        soft = soft_map.get(key, {})
        item["soft_community"] = soft.get("soft_community", item.get("soft_community"))
        item["soft_hits"] = soft.get("soft_hits", [])
        item["soft_focus"] = soft.get("focus", "")
        chart = REAL / item["file"]
        subprocess.check_call([sys.executable, str(CONV), str(chart)], cwd=str(ROOT))
        payload = json.loads(chart.with_name(chart.stem + ".hypergraph.json").read_text(encoding="utf-8"))
        f = payload["factors"]["factors"]
        rows.append({
            "key": key,
            "soft_community": item["soft_community"],
            "soft_hits": item["soft_hits"],
            "soft_focus": item.get("soft_focus"),
            "F1": f["F1_community"]["score"],
            "F1_reading": f["F1_community"]["reading"],
            "F2": f["F2_keystone"]["score"],
            "F3": f["F3_fragility"]["score"],
            "F4": f["F4_tempo"]["score"],
            "one_liner": payload["factors"]["one_liner"],
        })
        print(key, payload["factors"]["one_liner"], "soft", item["soft_community"])

    (REAL / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    f1s = [r["F1"] for r in rows]
    softs = [float(r["soft_community"]) for r in rows]
    corr = pearson(f1s, softs)
    summary = {
        "n": len(rows),
        "pearson_F1_vs_soft_dingdiao": None if corr != corr else round(corr, 4),
        "F1_mean": round(sum(f1s)/len(f1s), 4),
        "F4_mean": round(sum(r["F4"] for r in rows)/len(rows), 4),
        "F4_unique": sorted(set(r["F4"] for r in rows)),
        "soft_mean": round(sum(softs)/len(softs), 4),
        "note": "soft label uses 一句话定调(+friends overview snippet); not ground truth",
        "rows": rows,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("pearson", summary["pearson_F1_vs_soft_dingdiao"], "F4_unique", summary["F4_unique"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()