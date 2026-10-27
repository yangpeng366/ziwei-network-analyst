#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""易学概念 -> 白话解释（非断吉凶）。"""
from __future__ import annotations

from typing import Any


PALACE_LIFE = {
    "命宫": "自己怎么活、怎么被看见",
    "兄弟": "同辈手足与近互助伴",
    "夫妻": "亲密关系与搭档相处",
    "子女": "晚辈、作品、创造性输出",
    "财帛": "钱怎么进、怎么留",
    "疾厄": "身体负担与消耗点",
    "迁移": "外出、变动环境、对外场面",
    "交友": "朋友圈子与共事关系",
    "仆役": "下属、同事、可借力的人",
    "官禄": "事业舞台与职责",
    "田宅": "家、房产、内部安顿",
    "福德": "心里是否安稳、精神账本",
    "父母": "长辈缘与规矩来源",
}

STAR_HINT = {
    "紫微": "要有主心骨、愿意扛名分",
    "天机": "爱想办法、脑力周转快",
    "太阳": "向外发光、也容易耗自己",
    "武曲": "做事硬派、重结果与钱粮",
    "天同": "求安稳舒服、不爱硬碰",
    "廉贞": "情绪与原则都深，易纠结",
    "天府": "守库、求稳、怕折腾",
    "太阴": "内敛细腻、重感受与积蓄",
    "贪狼": "欲望与才华并强，要有出口",
    "巨门": "口舌是非与表达力同在",
    "天相": "辅佐协调、当二把手也稳",
    "天梁": "荫护清高、常成别人依靠",
    "七杀": "行动决断、压力下更锋利",
    "破军": "破旧立新、坐不住旧局",
}


def _palace_phrase(name: str) -> str:
    life = PALACE_LIFE.get(name, "这一宫所管的生活面")
    return f"{name}（{life}）"


def _star_phrase(name: str, palace: str | None) -> str:
    hint = STAR_HINT.get(name, "这颗星在盘里占分量")
    if palace:
        return f"{name}落在{_palace_phrase(palace)}——{hint}"
    return f"{name}——{hint}"


def explain_payload(payload: dict[str, Any]) -> dict[str, Any]:
    factors = ((payload.get("factors") or {}).get("factors")) or {}
    metrics = payload.get("metrics") or {}
    meta = ((payload.get("hypergraph") or {}).get("meta")) or {}

    f1 = factors.get("F1_community") or {}
    f2 = factors.get("F2_keystone") or {}
    f3 = factors.get("F3_fragility") or {}
    f4 = factors.get("F4_tempo") or {}

    ev = f1.get("evidence") or {}
    community = ev.get("community_palaces") or []
    pos = ev.get("positive_edges") or []
    ji = ev.get("ji_edges") or []
    if f1.get("reading") == "偏协作归属":
        f1_plain = "关系网上，你更容易感到“我和人是连着的”，互助比防备更占上风。"
    elif f1.get("reading") == "偏割裂":
        f1_plain = "关系网上，防备、切割感更明显，像有几条线老被扯断，要靠自己补。"
    else:
        f1_plain = "关系网处在拉锯：有时很能连上人，有时又突然抽离，关键在你怎么选边。"
    if community:
        f1_plain += " 主要看这些宫：" + "、".join(community) + "。"
    if pos and not ji:
        f1_plain += " 盘面多见禄/科/权进入关系宫，像有人递台阶。"
    elif ji and not pos:
        f1_plain += " 关系宫更多见到忌来冲，像合作里总有一根刺。"
    elif pos and ji:
        f1_plain += " 有助益也有忌冲，属于“能成事也容易内耗”的关系结构。"

    tops = f2.get("top") or metrics.get("keystones") or []
    if tops:
        bits = [_star_phrase(str(t.get("name")), t.get("palace")) for t in tops[:4]]
        f2_plain = "眼下最能扛事的几颗星：" + "；".join(bits) + "。它们亮、连线又多，倒哪颗，整盘体感会晃。"
    else:
        f2_plain = "承重星还不清晰，先把主星亮度与连线看全。"
    if f2.get("reading") == "负荷集中":
        f2_plain += " 负荷偏集中：少数人/少数主题在撑场面。"
    else:
        f2_plain += " 负荷较分散：不是一棵树撑天，而是几处一起分担。"

    hot = f3.get("hotspots") or metrics.get("ji_fragility") or []
    if hot:
        hs = []
        for h in hot[:3]:
            p = str(h.get("palace"))
            hs.append(_palace_phrase(p) + "压力偏高")
        f3_plain = "忌像“关键点被扯住”：优先留意" + "；".join(hs) + "。"
        f3_plain += " 白话讲：不是注定出事，而是这些生活面更吃冲击，宜留缓冲、少硬顶。"
    else:
        f3_plain = "当前活跃层里，忌压热区不明显。"
    if f3.get("reading") == "高脆":
        f3_plain += " 整体偏脆，遇变故时恢复成本更高。"
    elif f3.get("reading") == "中脆":
        f3_plain += " 中等脆弱：扛得住，但别连续加压。"
    else:
        f3_plain += " 相对抗造，仍要看具体宫位。"

    age = meta.get("current_age")
    dx = meta.get("current_daxian_index")
    as_of = meta.get("as_of_year")
    if f4.get("reading") == "接近结构重写":
        f4_plain = "你正靠近大限交接或窗口边缘：生活结构更容易改写——换轨、换重心、换相处方式都更常见。"
    else:
        f4_plain = "节律窗口相对平稳：更像在当前大限剧本里深耕，而不是整章翻篇。"
    extra = []
    if age is not None:
        extra.append(f"虚岁约{age}")
    if dx is not None:
        extra.append(f"当前大限序{dx}")
    if as_of is not None:
        extra.append(f"对照流年{as_of}")
    if extra:
        f4_plain += "（" + "，".join(str(x) for x in extra) + "）"

    one = (payload.get("factors") or {}).get("one_liner") or ""
    summary = (
        f"一句话：{one}。用易学白话说——共同体感看你与人连得上吗；"
        "承重星看谁在扛；忌压看哪块生活面怕冲击；节律看这十年是不是在换剧本。"
    )

    return {
        "summary": summary,
        "factors_plain": {
            "F1_community": f1_plain,
            "F2_keystone": f2_plain,
            "F3_fragility": f3_plain,
            "F4_tempo": f4_plain,
        },
        "how_to_look_next": [
            "先看四因子读法，再看承重星落在哪一宫（那是你生活里真正出力的主题）。",
            "忌压宫位 = 更需要留余地的地方，不是判决书。",
            "流年只改“当下张力”，不改你是谁；可把流年数字换一年对比。",
            "六亲、婚恋细节仅作参考受限，勿作唯一决策依据。",
        ],
        "glossary": {
            "宫": "生活的房间：田宅是家底与安顿，疾厄是消耗与身体账，仆役是共事与借力。",
            "承重星": "亮度高又连线多的星，像屋里承重墙。",
            "忌": "四化里的牵扯力，常表现为卡点、消耗、不得不面对的摩擦。",
            "大限/流年": "十年剧本与当年天气；天气变，房梁还在。",
        },
        "disclaimer": "系统势能白话翻译，仅供自我觉察，非命运断言。",
    }