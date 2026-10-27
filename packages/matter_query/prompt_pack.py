#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把结构化盘面结果拼成可粘贴给其他 AI 的提示词（无本机 LLM 也能用）。"""
from __future__ import annotations

from typing import Any


def build_user_prompt(payload: dict[str, Any], matter_text: str | None = None, timeline: dict[str, Any] | None = None) -> str:
    factors = payload.get("factors") or {}
    plain = payload.get("plain") or {}
    matter = payload.get("matter") or {}
    metrics = payload.get("metrics") or {}
    meta = ((payload.get("hypergraph") or {}).get("meta")) or {}

    lines: list[str] = []
    lines.append("你是命盘复杂系统分析助手。下面是已经算好的结构化结果，请只做白话翻译与情景推演。")
    lines.append("硬约束：不得改分数；不得重排盘；不得下绝对命运断言；六亲仅参考受限。")
    lines.append("")

    if matter_text or matter:
        q = matter_text or ((matter.get("focus") or {}).get("query") or "")
        label = (matter.get("focus") or {}).get("label") or "整体态势"
        lines.append(f"【用户想问的事】{q or '（未指定，按整体态势）'}")
        lines.append(f"【事项归类】{label}")
        if matter.get("plain"):
            lines.append(f"【事项聚焦草稿】{matter['plain']}")
        lines.append("")

    lines.append("【四因子一句话】")
    lines.append(str(factors.get("one_liner") or ""))
    lines.append("")

    lines.append("【白话摘要】")
    lines.append(str(plain.get("summary") or ""))
    fp = plain.get("factors_plain") or {}
    for k in ("F1_community", "F2_keystone", "F3_fragility", "F4_tempo"):
        if fp.get(k):
            lines.append(f"- {k}: {fp[k]}")
    lines.append("")

    tl = timeline or payload.get("timeline")
    if tl:
        rng = tl.get("range") or []
        lines.append(f"【逐年推演 {rng[0] if rng else ''}–{rng[1] if len(rng) > 1 else ''}（参考，非结论）】")
        tl_lines = (tl.get("plain") or {}).get("timeline_plain") or []
        for line in tl_lines:
            if str(line).startswith("逐年推演"):
                continue
            lines.append(f"- {line}")
        ty = tl.get("transition_years") or []
        if ty and not any("大限交接年" in str(x) for x in tl_lines):
            lines.append("- 大限交接年：" + "、".join(str(y) for y in ty[:8]))
        lines.append("")

    lines.append("【硬证据（勿改）】")
    fblocks = factors.get("factors") or {}
    for k, block in fblocks.items():
        if not isinstance(block, dict):
            continue
        lines.append(f"- {k}: score={block.get('score')} reading={block.get('reading')}")
    ks = metrics.get("keystones") or []
    if ks:
        lines.append(
            "- keystones: "
            + ", ".join(f"{x.get('name')}@{x.get('palace')}" for x in ks[:5])
        )
    fr = metrics.get("ji_fragility") or []
    if fr:
        lines.append(
            "- ji_hotspots: "
            + ", ".join(f"{x.get('palace')}={x.get('ji_pressure')}" for x in fr[:5])
        )
    extra = []
    if meta.get("current_age") is not None:
        extra.append(f"age={meta.get('current_age')}")
    if meta.get("current_daxian_index") is not None:
        extra.append(f"daxian={meta.get('current_daxian_index')}")
    if meta.get("as_of_year") is not None:
        extra.append(f"asOfYear={meta.get('as_of_year')}")
    if extra:
        lines.append("- meta: " + ", ".join(extra))
    lines.append("")

    lines.append("【请你输出】")
    lines.append("1. 先用大白话回答用户的具体事（若未指定则给整体态势）")
    lines.append("2. 点明：相关宫位 / 承重星 / 忌压热区 / 是否靠近换轨窗口")
    lines.append("3. 给 2-3 条可逆的自我觉察建议（非决策指令）")
    lines.append("4. 结尾加一句免责：仅供参考，非命运断言")
    return "\n".join(lines).strip() + "\n"


def build_system_prompt() -> str:
    return (
        "你只做翻译与情景生成。排盘与分数以用户粘贴的硬证据为准；"
        "禁止编造星曜位置、四化路径或古籍原文；禁止绝对吉凶判决。\n"
    )