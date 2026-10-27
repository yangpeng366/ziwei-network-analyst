#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""具体事项 -> 宫位/因子聚焦（势能推演，非传统吉凶占断）。"""
from __future__ import annotations

from typing import Any


# 关键词越靠前越优先；同组可多词命中。
MATTER_CATALOG: list[dict[str, Any]] = [
    {
        "id": "career",
        "label": "事业职场",
        "keywords": ["事业", "工作", "职场", "升迁", "晋升", "跳槽", "面试", "创业", "官运", "职责", "老板"],
        "palaces": ["官禄", "仆役", "财帛", "迁移"],
        "focus_factors": ["F2_keystone", "F3_fragility", "F4_tempo"],
        "lens": "看舞台（官禄）谁在扛、同事借力是否稳，以及今年会不会换剧本。",
    },
    {
        "id": "money",
        "label": "钱财资源",
        "keywords": ["钱", "财", "收入", "投资", "理财", "亏损", "回款", "开销", "工资", "副业"],
        "palaces": ["财帛", "田宅", "官禄", "福德"],
        "focus_factors": ["F2_keystone", "F3_fragility"],
        "lens": "看进账与留存的房间，谁在扛钱粮，哪里忌压偏高要留缓冲。",
    },
    {
        "id": "relationship",
        "label": "亲密关系",
        "keywords": ["感情", "恋爱", "相亲", "结婚", "婚姻", "分手", "复合", "配偶", "伴侣", "桃花"],
        "palaces": ["夫妻", "福德", "迁移", "交友"],
        "focus_factors": ["F1_community", "F3_fragility", "F4_tempo"],
        "lens": "看亲密宫与共同体感：连得上还是拉锯，忌压落在哪一侧。",
    },
    {
        "id": "health",
        "label": "身体消耗",
        "keywords": ["健康", "身体", "生病", "疲劳", "失眠", "手术", "养生", "疾厄"],
        "palaces": ["疾厄", "福德", "父母"],
        "focus_factors": ["F3_fragility", "F2_keystone"],
        "lens": "把疾厄当消耗账本：忌压与承重是否叠在同一处。",
    },
    {
        "id": "home",
        "label": "安家置业",
        "keywords": ["房子", "购房", "租房", "搬家", "装修", "家", "房产", "安家", "田宅"],
        "palaces": ["田宅", "财帛", "迁移", "父母"],
        "focus_factors": ["F3_fragility", "F4_tempo", "F2_keystone"],
        "lens": "看安顿与变动是否撞车：田宅稳不稳、迁移会不会掀桌。",
    },
    {
        "id": "travel",
        "label": "外出变动",
        "keywords": ["出行", "出差", "旅行", "留学", "移民", "外派", "远行", "变动"],
        "palaces": ["迁移", "交友", "官禄", "疾厄"],
        "focus_factors": ["F4_tempo", "F1_community", "F3_fragility"],
        "lens": "看对外场面与节律窗口：是深耕本地，还是适合换环境。",
    },
    {
        "id": "collaboration",
        "label": "合作共事",
        "keywords": ["合作", "合伙", "同事", "团队", "下属", "朋友", "人脉", "贵人", "借力"],
        "palaces": ["交友", "仆役", "官禄", "夫妻"],
        "focus_factors": ["F1_community", "F2_keystone", "F3_fragility"],
        "lens": "看共同体感与借力宫：互助台阶多，还是忌刺多。",
    },
    {
        "id": "exam",
        "label": "考试文书",
        "keywords": ["考试", "升学", "考研", "考证", "文书", "合同", "诉讼", "答辩", "论文"],
        "palaces": ["父母", "官禄", "疾厄", "交友"],
        "focus_factors": ["F2_keystone", "F3_fragility", "F4_tempo"],
        "lens": "看规矩来源与舞台压力：承重是否够、忌压会不会搅节奏。",
    },
    {
        "id": "family",
        "label": "长辈晚辈",
        "keywords": ["父母", "长辈", "孩子", "子女", "生育", "家庭矛盾", "家事"],
        "palaces": ["父母", "子女", "田宅", "兄弟"],
        "focus_factors": ["F1_community", "F3_fragility"],
        "lens": "六亲仅作参考受限：只标张力方向与可觉察点，不作判决。",
    },
    {
        "id": "general",
        "label": "整体态势",
        "keywords": ["整体", "运势", "今年", "大方向", "怎么办", "看看盘"],
        "palaces": ["命宫", "官禄", "夫妻", "财帛"],
        "focus_factors": ["F1_community", "F2_keystone", "F3_fragility", "F4_tempo"],
        "lens": "不锁单一事项时，仍用四因子总览，再点最热宫位。",
    },
]


def resolve_matter(text: str | None) -> dict[str, Any]:
    q = (text or "").strip()
    if not q:
        cat = next(c for c in MATTER_CATALOG if c["id"] == "general")
        return {
            "query": "",
            "matched": False,
            "matter_id": cat["id"],
            "label": cat["label"],
            "palaces": list(cat["palaces"]),
            "focus_factors": list(cat["focus_factors"]),
            "lens": cat["lens"],
            "hit_keywords": [],
        }

    best = None
    best_hits: list[str] = []
    for cat in MATTER_CATALOG:
        hits = [k for k in cat["keywords"] if k and k in q]
        if len(hits) > len(best_hits):
            best = cat
            best_hits = hits
    if best is None:
        best = next(c for c in MATTER_CATALOG if c["id"] == "general")
        best_hits = []
    return {
        "query": q,
        "matched": bool(best_hits) or best["id"] == "general",
        "matter_id": best["id"],
        "label": best["label"],
        "palaces": list(best["palaces"]),
        "focus_factors": list(best["focus_factors"]),
        "lens": best["lens"],
        "hit_keywords": best_hits,
    }


def _palace_pressure(payload: dict[str, Any], palace: str) -> float | None:
    metrics = payload.get("metrics") or {}
    for row in metrics.get("ji_fragility") or []:
        if str(row.get("palace")) == palace:
            try:
                return float(row.get("ji_pressure"))
            except (TypeError, ValueError):
                return None
    return None


def _keystones_on_palaces(payload: dict[str, Any], palaces: set[str]) -> list[dict[str, Any]]:
    metrics = payload.get("metrics") or {}
    out = []
    for ks in metrics.get("keystones") or []:
        if str(ks.get("palace")) in palaces:
            out.append(ks)
    return out


def explain_matter(payload: dict[str, Any], matter_text: str | None) -> dict[str, Any]:
    """在已有四因子 payload 上，生成具体事项聚焦白话。"""
    focus = resolve_matter(matter_text)
    palaces = focus["palaces"]
    pset = set(palaces)

    pressures = []
    for p in palaces:
        v = _palace_pressure(payload, p)
        if v is not None:
            pressures.append({"palace": p, "ji_pressure": v})
    pressures.sort(key=lambda x: x["ji_pressure"], reverse=True)

    carriers = _keystones_on_palaces(payload, pset)
    factors = ((payload.get("factors") or {}).get("factors")) or {}
    factor_bits = []
    for fid in focus["focus_factors"]:
        block = factors.get(fid) or {}
        reading = block.get("reading")
        score = block.get("score")
        if reading is not None:
            factor_bits.append(f"{fid}:{reading}" + (f"({score})" if score is not None else ""))

    if pressures:
        hot = "、".join(f"{x['palace']}({x['ji_pressure']})" for x in pressures[:3])
        risk = f"与本题相关的忌压热区偏在：{hot}。宜留缓冲，不把同一处连续加压。"
    else:
        risk = "本题相关宫位上，活跃层忌压热区不明显；仍建议看承重是否过载。"

    if carriers:
        carry = "、".join(f"{c.get('name')}@{c.get('palace')}" for c in carriers[:4])
        carry_txt = f"落在本题宫位上的承重星：{carry}。"
    else:
        carry_txt = "本题宫位上暂未见最顶级承重星；力量可能来自邻宫或借对。"

    summary = (
        f"就「{focus['label']}」看：优先宫位 "
        + "、".join(palaces)
        + f"。{focus['lens']}"
    )
    plain = " ".join([summary, carry_txt, risk, "结论只标势能方向与可觉察点，不作吉凶判决。"])

    return {
        "focus": focus,
        "related_pressures": pressures,
        "related_keystones": [
            {"name": c.get("name"), "palace": c.get("palace"), "score": c.get("score")}
            for c in carriers[:6]
        ],
        "factor_snapshot": factor_bits,
        "plain": plain,
        "actions": [
            "先盯本题宫位的承重星与忌压，再看是否撞上 F4 换轨窗口。",
            "把建议落成可逆的小动作（留缓冲、分摊负荷、错峰决策），不要一次梭哈。",
            "六亲/婚恋/健康仅参考受限；重大决策请结合现实信息与专业意见。",
        ],
        "disclaimer": "事项聚焦=盘面房间打光，不是卜卦判定吉凶。",
    }