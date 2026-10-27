#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sweep.py - 逐年推演 CLI。

用法：
  python scripts/sweep.py --chart fixtures/sample-chart.json --from 2020 --to 2035
  python scripts/sweep.py --birth 1990-01-01-0-male --from 2020 --to 2035 --svg out/curve.svg
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from timeline.sweep import sweep_payload  # noqa: E402
from timeline.curve_svg import curve_svg  # noqa: E402

CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
ENGINE = Path(os.environ.get("ZIWEI_ENGINE_ROOT", r"F:\github\ziwei-doushu"))
GEN = ENGINE / "scripts" / "gen-one-for-ui.ts"


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _run_engine(spec: str) -> dict:
    parts = spec.split("-")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    h = int(parts[3])
    gender = parts[4]
    age = int(parts[5]) if len(parts) > 5 and parts[5] else None
    tsx = ENGINE / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform.startswith("win") else "tsx")
    if tsx.exists():
        cmd = [str(tsx), str(GEN), str(y), str(m), str(d), str(h), gender]
    else:
        npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
        cmd = [npm, "exec", "--yes", "--", "tsx@4.19.4", str(GEN), str(y), str(m), str(d), str(h), gender]
    if age is not None:
        cmd.append(str(age))
    proc = subprocess.run(cmd, cwd=str(ENGINE), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", shell=False)
    if proc.returncode != 0:
        raise SystemExit("排盘引擎失败：\n" + (proc.stderr or proc.stdout)[-2000:])
    chart = json.loads(proc.stdout)
    if age is not None:
        chart["currentAge"] = age
    return chart


def _markdown(data: dict) -> str:
    rows = data["rows"]
    lines = [
        f"# 逐年推演 {data['range'][0]}–{data['range'][1]}",
        "",
        data["summary"],
        "",
        "| 年 | 虚岁 | 大限 | F1 共同体感 | F3 冲击脆弱 | F4 节律窗口 | 忌压首位 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        hot = r["ji_hotspots"][0] if r.get("ji_hotspots") else None
        hot_txt = f"{hot['palace']}({hot['ji_pressure']})" if hot else "-"
        lines.append(
            f"| {r['year']} | {r.get('age')} | {r.get('daxian_label') or '-'} | "
            f"{r.get('F1')} {r.get('F1_reading') or ''} | {r.get('F3')} {r.get('F3_reading') or ''} | "
            f"{r.get('F4')} {r.get('F4_reading') or ''} | {hot_txt} |"
        )
    if data.get("daxian_transitions"):
        lines.append("")
        lines.append("大限交接：")
        for t in data["daxian_transitions"]:
            lines.append(f"- {t['year']}：{t['from']} → {t['to']}")
    lines.append("")
    lines.append("_仅供参考，非命运断言。_")
    return "\n".join(lines)


def main() -> int:
    _force_utf8_stdout()
    ap = argparse.ArgumentParser(description="逐年推演（F3/F4 曲线）")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--birth", help="生辰 YYYY-MM-DD-H-gender[-age]")
    src.add_argument("--chart", type=Path, help="已有 chart.json")
    ap.add_argument("--from", dest="y_from", type=int, required=True)
    ap.add_argument("--to", dest="y_to", type=int, required=True)
    ap.add_argument("--out", type=Path, default=None, help="输出 json（默认 out/sweep.json）")
    ap.add_argument("--md", type=Path, default=None, help="输出 markdown 表")
    ap.add_argument("--svg", type=Path, default=None, help="输出 SVG 曲线")
    args = ap.parse_args()

    if args.birth:
        chart = _run_engine(args.birth)
    else:
        chart = json.loads(args.chart.read_text(encoding="utf-8"))

    data = sweep_payload(chart, args.y_from, args.y_to)

    out = args.out or (ROOT / "out" / "sweep.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("json:", out)

    md = args.md or out.with_suffix(".md")
    md.write_text(_markdown(data), encoding="utf-8")
    print("md:", md)

    if args.svg:
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(
            curve_svg(data["rows"], data.get("daxian_transitions"), title=f"逐年推演 {data['range'][0]}–{data['range'][1]}"),
            encoding="utf-8",
        )
        print("svg:", args.svg)

    print(data["plain"]["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())