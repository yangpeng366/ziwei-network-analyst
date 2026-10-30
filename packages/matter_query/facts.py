#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把盘面整理成「事实卡」：让 LLM 有料可解释，而不是空谈。

分四层：
1. 十二宫一览：每宫主星/辅星/亮度/生年四化（简洁，供 LLM 自行取用）
2. 相关宫详卡：题问命中的宫，展开宫义与与命宫关系（星曜已在一览，不重复）
3. 生年四化飞入：哪颗星化禄权科忌、落在哪宫
4. 大限：当前所处大限、宫干四化的落点
"""
from __future__ import annotations

from typing import Any

from hypergraph.constants import SI_HUA_TABLE, BRANCHES

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
SANFANG = {  # 三方四正：命宫 + 对宫 + 三合
    0: (4, 8, 6), 1: (5, 9, 7), 2: (6, 10, 8), 3: (7, 11, 9),
    4: (8, 0, 10), 5: (9, 1, 11), 6: (10, 2, 0), 7: (11, 3, 1),
    8: (0, 4, 2), 9: (1, 5, 3), 10: (2, 6, 4), 11: (3, 7, 5),
}


def _stem_sihua(stem: Any) -> dict[str, str]:
    try:
        arr = SI_HUA_TABLE.get(int(stem))
    except (TypeError, ValueError):
        return {}
    if not arr:
        return {}
    return {"禄": arr[0], "权": arr[1], "科": arr[2], "忌": arr[3]}


def _palaces(chart: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for p in chart.get("palaces") or []:
        branch = p.get("branch")
        try:
            branch = int(branch)
        except (TypeError, ValueError):
            branch = None
        out.append({**p, "branch": branch})
    return out


def _stars_of(palace: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    res = []
    for s in palace.get("stars") or []:
        if (s.get("type") or "").lower() != kind:
            continue
        res.append(
            {
                "name": s.get("name"),
                "brightness": s.get("brightnessRaw"),
                "sihua": s.get("siHua"),
            }
        )
    return res

def _ming_branch(chart: dict[str, Any]) -> int | None:
    for p in _palaces(chart):
        if p.get("isMingGong"):
            return p.get("branch")
    return None

def relation_to_ming(branch: int | None, ming_branch: int | None) -> str:
    """该宫与命宫的关系：命宫本体 / 三方 / 对宫 / 之外。"""
    if branch is None or ming_branch is None:
        return "命宫之外"
    if branch == ming_branch:
        return "命宫"
    if branch == (ming_branch + 6) % 12:
        return "命宫对宫"
    if branch in SANFANG.get(ming_branch, ()):
        return "命宫三方"
    return "命宫之外"


def _palace_label(name: Any) -> str:
    """宫名统一补「宫」字；已带「宫」的不要再叠一个（命宫宫）。"""
    nm = str(name or "")
    return nm if nm.endswith("宫") else f"{nm}宫"


def _self_sihua(palace: dict[str, Any]) -> list[str]:
    """宫干四化落在本宫星曜上 = 自化。"""
    transforms = _stem_sihua(palace.get("stem"))
    if not transforms:
        return []
    hit = []
    for s in palace.get("stars") or []:
        mark = s.get("siHua")
        for kind, star in transforms.items():
            if mark == kind and s.get("name") == star:
                hit.append(f"{s.get('name')}自化{kind}")
    return hit


def twelve_palaces(chart: dict[str, Any]) -> list[dict[str, Any]]:
    """十二宫一览（紧凑）。"""
    rows = []
    ming_branch = _ming_branch(chart)
    for p in _palaces(chart):
        major = _stars_of(p, "major")
        minor = _stars_of(p, "minor")
        lucky = _stars_of(p, "lucky")
        sihua_marks = [f"{s['name']}化{s['sihua']}" for s in (major + minor + lucky) if s.get("sihua")]
        branch = p.get("branch")
        rows.append(
            {
                "name": p.get("name"),
                "branch": BRANCHES[p["branch"]] if p.get("branch") is not None and 0 <= p["branch"] < 12 else None,
                "stem": p.get("stem"),
                "major": [f"{s['name']}({s['brightness']})" if s.get("brightness") else s["name"] for s in major],
                "minor": [f"{s['name']}({s['brightness']})" if s.get("brightness") else s["name"] for s in minor],
                "lucky": [f"{s['name']}{('化' + s['sihua']) if s.get('sihua') else ''}" for s in lucky],
                "sihua_marks": sihua_marks,
                "self_sihua": _self_sihua(p),
                "relation_to_ming": relation_to_ming(branch, ming_branch),
                "is_empty": bool(p.get("isEmpty")),
                "is_ming": bool(p.get("isMingGong")),
            }
        )
    return rows


def sihua_inflows(chart: dict[str, Any]) -> list[str]:
    """生年四化飞入：哪颗星在哪宫化禄权科忌。"""
    lines = []
    for p in _palaces(chart):
        for s in p.get("stars") or []:
            if s.get("siHua"):
                lines.append(f"{s.get('name')} 化{s.get('siHua')} → {_palace_label(p.get('name'))}")
    return lines


def palace_cards(chart: dict[str, Any], names: list[str]) -> list[dict[str, Any]]:
    """相关宫详卡。"""
    want = {n for n in names if n}
    ming_branch = _ming_branch(chart)
    cards = []
    for p in _palaces(chart):
        if p.get("name") not in want:
            continue
        branch = p.get("branch")
        rel = relation_to_ming(branch, ming_branch)
        major = _stars_of(p, "major")
        minor = _stars_of(p, "minor")
        lucky = _stars_of(p, "lucky")
        cards.append(
            {
                "name": p.get("name"),
                "life": PALACE_LIFE.get(str(p.get("name")), "这一宫所管的生活面"),
                "branch": BRANCHES[branch] if branch is not None and 0 <= branch < 12 else None,
                "stem": p.get("stem"),
                "relation_to_ming": rel,
                "major": major,
                "minor": minor,
                "lucky": lucky,
                "self_sihua": _self_sihua(p),
                "is_empty": bool(p.get("isEmpty")),
                "note": "空宫，借对宫论" if p.get("isEmpty") else "",
            }
        )
    return cards


def daxian_facts(chart: dict[str, Any], index: Any = None) -> dict[str, Any] | None:
    daxians = chart.get("daXians") or []
    if not daxians:
        return None
    if index is None:
        index = chart.get("currentDaXianIndex")
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return None
    if not (0 <= idx < len(daxians)):
        return None
    dx = daxians[idx]
    branch = None
    try:
        branch = int(dx.get("palaceBranch"))
    except (TypeError, ValueError):
        pass
    stem = None
    for p in _palaces(chart):
        if branch is not None and p.get("branch") == branch:
            stem = p.get("stem")
            break
    transforms = _stem_sihua(stem)
    hits = []
    if transforms:
        for p in _palaces(chart):
            for s in p.get("stars") or []:
                for kind, star in transforms.items():
                    if s.get("name") == star:
                        hits.append(f"{star}在{_palace_label(p.get('name'))}化{kind}")
    return {
        "index": idx,
        "start_age": dx.get("startAge"),
        "end_age": dx.get("endAge"),
        "palace_name": dx.get("palaceName"),
        "branch": BRANCHES[branch] if branch is not None and 0 <= branch < 12 else None,
        "stem": stem,
        "stem_sihua": transforms,
        "flows": hits,
    }


# 不同盘的宫名口径不一：交友/仆役/奴仆 实为同一宫
PALACE_ALIAS = {
    "仆役": ["仆役", "交友", "奴仆"],
    "交友": ["交友", "仆役", "奴仆"],
    "奴仆": ["奴仆", "仆役", "交友"],
}


def resolve_palace_names(chart: dict[str, Any], names: list[str]) -> list[str]:
    """把宫名对齐到本盘实际存在的宫（处理交友/仆役别名），并去重。"""
    have = {str(p.get("name")) for p in _palaces(chart)}
    out: list[str] = []
    for n in names:
        cands = PALACE_ALIAS.get(str(n), [str(n)])
        pick = next((c for c in cands if c in have), None)
        if pick and pick not in out:
            out.append(pick)
    return out


def build_facts(
    chart: dict[str, Any],
    palaces: list[str] | None = None,
    cards_title: str = "与本题直接相关的宫（详卡）",
) -> dict[str, Any]:
    """打包成提示词可直接使用的素材。

    星曜与四化只在「十二宫一览」给一次；详卡只补宫义与三方关系，避免同一份星曜重复两遍。
    """
    names = resolve_palace_names(chart, palaces or [])
    return {
        "twelve": twelve_palaces(chart),
        "cards": palace_cards(chart, names),
        "cards_title": cards_title,
        "sihua_inflows": sihua_inflows(chart),
        "daxian": daxian_facts(chart),
        "palace_life": PALACE_LIFE,
    }


def facts_for(chart: dict[str, Any], focus: dict[str, Any]) -> dict[str, Any]:
    """按事项焦点取事实卡。

    命中关键词：只展开命中的相关宫（≤6），其余宫留在十二宫一览里当背景。
    未命中：不再逐宫铺开 12 张详卡，只给十二宫一览 + 宫义速查，让 LLM 自行取用。
    """
    palaces = list(focus.get("palaces") or [])
    matched = bool(focus.get("matched"))
    if not matched:
        palaces = []
    facts = build_facts(chart, palaces)
    facts["matched"] = matched
    return facts
