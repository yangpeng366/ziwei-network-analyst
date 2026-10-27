#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F3/F4 逐年曲线 -> 纯 SVG（无第三方依赖）。"""
from __future__ import annotations

from typing import Any

W, H = 960, 360
PAD_L, PAD_R, PAD_T, PAD_B = 56, 20, 26, 44

SERIES = [
    ("F4", "节律窗口（换轨压力）", "#0f6a5a"),
    ("F3", "冲击脆弱", "#8a2f3b"),
]


def _esc(s: Any) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def curve_svg(rows: list[dict[str, Any]], transitions: list[dict[str, Any]] | None = None, title: str = "") -> str:
    rows = [r for r in rows if r.get("F3") is not None and r.get("F4") is not None]
    if len(rows) < 2:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="80" role="img"></svg>'

    xs = [r["year"] for r in rows]
    x0, x1 = min(xs), max(xs)
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    def px(year: int) -> float:
        if x1 == x0:
            return PAD_L + plot_w / 2
        return PAD_L + (year - x0) / (x1 - x0) * plot_w

    def py(v: float) -> float:
        v = max(0.0, min(1.0, float(v)))
        return PAD_T + (1 - v) * plot_h

    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
        f'height="{H}" role="img" aria-label="逐年因子曲线" font-family="Segoe UI, Microsoft YaHei, sans-serif">'
    )
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fffdf8"/>')

    if title:
        out.append(f'<text x="{PAD_L}" y="16" font-size="13" font-weight="600" fill="#1f2430">{_esc(title)}</text>')

    # grid + y labels
    for i in range(5):
        v = i / 4
        y = py(v)
        out.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" stroke="#e6e0d5" stroke-width="1"/>')
        out.append(f'<text x="{PAD_L - 8}" y="{y + 4:.1f}" font-size="11" fill="#5c6575" text-anchor="end">{v:.2f}</text>')

    # 大限交接竖线
    for t in transitions or []:
        if t.get("year") is None or not (x0 <= t["year"] <= x1):
            continue
        x = px(t["year"])
        out.append(f'<line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{H - PAD_B}" stroke="#c9a227" stroke-width="1" stroke-dasharray="4 4"/>')
        out.append(f'<text x="{x + 4:.1f}" y="{PAD_T + 12}" font-size="10" fill="#8a6d1f">大限交接</text>')

    # x labels
    step = max(1, len(rows) // 10)
    for r in rows[::step]:
        x = px(r["year"])
        out.append(f'<text x="{x:.1f}" y="{H - PAD_B + 16}" font-size="11" fill="#5c6575" text-anchor="middle">{r["year"]}</text>')

    # series
    for key, label, color in SERIES:
        pts = " ".join(f"{px(r['year']):.1f},{py(r[key]):.1f}" for r in rows)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
        for r in rows:
            out.append(f'<circle cx="{px(r["year"]):.1f}" cy="{py(r[key]):.1f}" r="3" fill="{color}"/>')

    # legend
    lx = PAD_L
    for key, label, color in SERIES:
        out.append(f'<rect x="{lx}" y="{H - 16}" width="10" height="10" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 15}" y="{H - 7}" font-size="11" fill="#1f2430">{_esc(label)}</text>')
        lx += 18 + len(label) * 11

    out.append("</svg>")
    return "".join(out)