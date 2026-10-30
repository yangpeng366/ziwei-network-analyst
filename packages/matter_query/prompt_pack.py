#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把结构化盘面结果拼成可粘贴给其他 AI 的提示词（无本机 LLM 也能用）。"""
from __future__ import annotations

from typing import Any


# 宫义速查的顺序：命宫在前，其余按人生面展开
LIFE_ORDER = [
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移",
    "交友", "仆役", "官禄", "田宅", "福德", "父母",
]

# 与命宫关系在十二宫一览里用短标签，详卡里用全称
REL_SHORT = {
    "命宫": "本宫",
    "命宫三方": "三方",
    "命宫对宫": "对宫",
    "命宫之外": "之外",
}


def _palace_label(name: Any) -> str:
    nm = str(name or "")
    return nm if nm.endswith("宫") else f"{nm}宫"


def _life_line(facts: dict[str, Any]) -> str:
    """宫义速查：没命中关键词时，一行说清十二宫各管什么。"""
    life = facts.get("palace_life") or {}
    rows = facts.get("twelve") or []
    by_name = {str(r.get("name") or ""): r for r in rows}
    bits: list[str] = []
    for name in LIFE_ORDER:
        row = by_name.get(name)
        if not row:
            continue
        meaning = life.get(name) or row.get("life") or "这一宫所管的生活面"
        bits.append(f"{_palace_label(name)}={meaning}")
    for name, row in by_name.items():
        if name in LIFE_ORDER:
            continue
        meaning = life.get(name) or row.get("life") or "这一宫所管的生活面"
        bits.append(f"{_palace_label(name)}={meaning}")
    return "；".join(bits)


def render_facts_text(facts: dict[str, Any]) -> str:
    """把事实卡渲染成提示词正文（静态站与本地共用同一份，保证一致）。

    星曜/亮度/四化只在「十二宫一览」给一次；详卡只补宫义，避免同一份星曜重复两遍。
    """
    if not facts:
        return ""
    out: list[str] = []
    out.append("· 十二宫一览（宫名(与命宫关系)｜主星(亮度)｜辅星｜生年四化｜自化）")
    for row in facts.get("twelve") or []:
        parts = []
        if row.get("major"):
            parts.append("主星 " + "、".join(row["major"]))
        if row.get("minor"):
            parts.append("辅星 " + "、".join(row["minor"]))
        if row.get("lucky"):
            parts.append("吉煞 " + "、".join(row["lucky"]))
        if row.get("self_sihua"):
            parts.append("自化 " + "、".join(row["self_sihua"]))
        if row.get("is_empty"):
            parts.append("空宫(借对宫论)")
        rel = str(row.get("relation_to_ming") or "")
        tag = f"({REL_SHORT.get(rel, rel)})" if rel else ""
        out.append(
            f"  - {_palace_label(row.get('name'))}{tag}："
            + ("；".join(parts) if parts else "无主星")
        )
    if facts.get("sihua_inflows"):
        out.append("")
        out.append("· 生年四化飞入")
        for s in facts["sihua_inflows"]:
            out.append(f"  - {s}")
    dx = facts.get("daxian")
    if dx:
        out.append("")
        out.append(
            f"· 当前大限：第 {dx.get('index')} 大限（{dx.get('start_age')}–{dx.get('end_age')} 岁，{dx.get('palace_name')}宫）"
        )
        if dx.get("flows"):
            out.append("  - 大限宫干四化：" + "；".join(dx["flows"]))
    cards = facts.get("cards") or []
    if cards:
        out.append("")
        out.append("· " + str(facts.get("cards_title") or "与本题直接相关的宫（详卡）"))
        for c in cards:
            out.append(
                f"  - {_palace_label(c.get('name'))}"
                f"（{c.get('life')}；与命宫关系：{c.get('relation_to_ming')}）"
            )
    else:
        # 未命中关键词：不铺开十二张详卡，一行宫义速查即可
        life_line = _life_line(facts)
        if life_line:
            out.append("")
            hint = (
                "问题未命中关键词，按整体态势取用"
                if facts.get("matched") is False
                else "未找到对应宫位，仅给十二宫一览"
            )
            out.append("· 宫义速查（" + hint + "）：" + life_line)
    return "\n".join(out)


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

    facts_text = payload.get("facts_text")
    if not facts_text:
        facts_text = render_facts_text(payload.get("facts") or {})
    if facts_text:
        lines.append("【盘面事实（解释的唯一依据，可回溯）】")
        lines.append("")
        lines.append(facts_text.rstrip())
        lines.append("")
        lines.append("（以上为机器整理的事实。关键词归类可能不全，可依事实自行调整取用的宫位。）")
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

    lines.append("【怎么答】")
    lines.append("1. 第一句就给结论：就用户问的那件事，此刻的势能偏向哪边。")
    lines.append("2. 再讲依据：点名具体宫位与星曜（如「迁移宫廉贞陷、破军旺」「太阴化忌在财帛」），不要只引分数。")
    lines.append("3. 用日常话解释星曜含义（说「这事靠不靠得住」，不要只说「廉贞化忌」）。")
    lines.append("4. 若问题命中某一年的窗口或忌压，点明是哪一年；没有就说不涉及。")
    lines.append("5. 给 2-3 条可逆的小动作（留缓冲、分担、错峰、试一小步），不要下必须怎么做的断言。")
    lines.append("6. 涉及六亲、婚恋、健康时标注「参考受限」。")
    lines.append("7. 结尾一句免责：仅供参考，非命运断言。")
    lines.append("")
    lines.append("【不要做】")
    lines.append("- 不要编造盘上没有的星曜、四化或年份")
    lines.append("- 不要把分数改写成吉凶，也不要用「一定/必然/注定」")
    lines.append("- 不要输出与用户所问无关的整盘泛批")
    return "\n".join(lines).strip() + "\n"


def build_system_prompt() -> str:
    return (
        "你是一位用易学白话讲命盘的顾问。只做两件事：把结构化结果翻译成好懂的话，"
        "并针对用户问的那件具体事给出可落地的建议。\n"
        "规矩：排盘与分数以用户粘贴的硬证据为准；星曜、四化、年份只能取自「盘面事实」；"
        "禁止编造古籍原文；禁止绝对吉凶判决；六亲/婚恋/健康标注参考受限。\n"
    )
