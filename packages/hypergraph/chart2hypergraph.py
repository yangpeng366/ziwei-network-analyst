#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chart2hypergraph: ZiweiChart JSON -> temporal hypergraph + network metrics.

Deterministic L1 layer. No LLM. No fate claims.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import sys

_PACKAGES = Path(__file__).resolve().parents[1]
if str(_PACKAGES) not in sys.path:
    sys.path.insert(0, str(_PACKAGES))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import explain_matter  # noqa: E402
from matter_query.prompt_pack import build_system_prompt, build_user_prompt  # noqa: E402

BRANCHES = list("子丑寅卯辰巳午未申酉戌亥")
BRIGHTNESS_STATE = {
    "庙": 1.0,
    "旺": 0.85,
    "得": 0.7,
    "利": 0.55,
    "平": 0.45,
    "地": 0.4,
    "不": 0.25,
    "闲": 0.2,
    "陷": 0.1,
}
SIHUA_WEIGHT = {"禄": 1.0, "权": 0.85, "科": 0.55, "忌": -1.0}

# Stem index 0=甲 … 9=癸 → (禄, 权, 科, 忌)
SI_HUA_TABLE = {
    0: ("廉贞", "破军", "武曲", "太阳"),
    1: ("天机", "天梁", "紫微", "太阴"),
    2: ("天同", "天机", "文昌", "廉贞"),
    3: ("太阴", "天同", "天机", "巨门"),
    4: ("贪狼", "太阴", "右弼", "天机"),
    5: ("武曲", "贪狼", "天梁", "文曲"),
    6: ("太阳", "武曲", "太阴", "天同"),
    7: ("巨门", "太阳", "文曲", "文昌"),
    8: ("天梁", "紫微", "左辅", "武曲"),
    9: ("破军", "巨门", "太阴", "贪狼"),
}


def sihua_by_stem(stem_index: int | None) -> dict[str, str]:
    if stem_index is None:
        return {}
    try:
        stem = int(stem_index)
    except (TypeError, ValueError):
        return {}
    arr = SI_HUA_TABLE.get(stem)
    if not arr:
        return {}
    return {"禄": arr[0], "权": arr[1], "科": arr[2], "忌": arr[3]}


def year_stem_index(year: int) -> int:
    return ((int(year) - 4) % 10 + 10) % 10


def active_layer_ids(hg: dict[str, Any]) -> set[str]:
    """Only natal + current大限 + 流年 enter F1/F3 scoring.

    Historical daxian layers stay in the hypergraph for timeline views, but
    must not flatten community contrast or saturate fragility.
    """
    ids: set[str] = {"natal"}
    cur = (hg.get("meta") or {}).get("current_daxian_index")
    if isinstance(cur, int):
        ids.add(f"daxian:{cur}")
    for layer in hg.get("layers") or []:
        if layer.get("kind") == "liunian" and layer.get("id"):
            ids.add(str(layer["id"]))
    return ids


def resolve_as_of_year(chart: dict[str, Any]) -> int | None:
    for key in ("asOfYear", "currentYear", "liuNianYear"):
        if chart.get(key) is not None:
            try:
                return int(chart[key])
            except (TypeError, ValueError):
                pass
    birth = chart.get("birthInfo") or {}
    by = birth.get("year")
    age = chart.get("currentAge")
    if by is None or age is None:
        return None
    try:
        # 虚岁近似：出生年 + 当前虚岁 - 1
        return int(by) + int(age) - 1
    except (TypeError, ValueError):
        return None


def append_sihua_edges(
    *,
    nodes: list[dict[str, Any]],
    hyperedges: list[dict[str, Any]],
    transforms: dict[str, str],
    layer_id: str,
    kind: str,
    group: list[str],
    weight_scale: float = 1.0,
) -> None:
    for op, star_name in transforms.items():
        if not star_name:
            continue
        locs = [n for n in nodes if n["kind"] == "star" and n["name"] == star_name]
        for loc in locs:
            hyperedges.append(
                {
                    "id": f"{kind}:{layer_id}:{op}:{star_name}@{loc['branch']}",
                    "kind": kind,
                    "layer": layer_id,
                    "operator": op,
                    "source": loc["id"],
                    "nodes": [loc["id"], *group],
                    "weight": SIHUA_WEIGHT.get(op, 0.0) * weight_scale,
                }
            )


def palace_by_branch(chart: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(p["branch"]): p for p in chart.get("palaces", [])}


def sanfang_sizheng(branch: int) -> list[int]:
    """命盘常见三方四正：本宫 + 对宫 + 三合两宫。"""
    opposite = (branch + 6) % 12
    triad = sorted({branch % 12, (branch + 4) % 12, (branch + 8) % 12})
    return sorted(set([branch, opposite, *triad]))


def star_state(star: dict[str, Any]) -> float:
    raw = star.get("brightnessRaw") or ""
    if raw in BRIGHTNESS_STATE:
        return BRIGHTNESS_STATE[raw]
    coarse = star.get("brightness")
    return {"bright": 0.85, "normal": 0.45, "dim": 0.15}.get(coarse, 0.45)


def build_hypergraph(chart: dict[str, Any]) -> dict[str, Any]:
    palaces = palace_by_branch(chart)
    nodes: list[dict[str, Any]] = []
    hyperedges: list[dict[str, Any]] = []
    node_index: dict[str, dict[str, Any]] = {}

    # Palace container nodes
    for b in range(12):
        p = palaces.get(b, {"branch": b, "name": BRANCHES[b], "stars": []})
        nid = f"palace:{b}"
        node = {
            "id": nid,
            "kind": "palace",
            "branch": b,
            "name": p.get("name", BRANCHES[b]),
            "is_ming": bool(p.get("isMingGong")),
            "is_shen": bool(p.get("isShenGong")),
            "is_empty": bool(p.get("isEmpty")),
            "state": 0.0,
            "degree_hint": 0,
        }
        nodes.append(node)
        node_index[nid] = node

    # Star nodes
    for b, p in palaces.items():
        for star in p.get("stars", []) or []:
            sid = f"star:{star['name']}@{b}"
            state = star_state(star)
            node = {
                "id": sid,
                "kind": "star",
                "name": star.get("name"),
                "type": star.get("type"),
                "branch": b,
                "palace": p.get("name"),
                "sihua": star.get("siHua"),
                "brightness": star.get("brightnessRaw") or star.get("brightness"),
                "state": state,
            }
            nodes.append(node)
            node_index[sid] = node
            # membership edge palace <-> star
            hyperedges.append(
                {
                    "id": f"member:{sid}",
                    "kind": "membership",
                    "layer": "natal",
                    "nodes": [f"palace:{b}", sid],
                    "weight": state,
                }
            )
            node_index[f"palace:{b}"]["state"] += state

    # Borrowed stars as soft membership
    for b, p in palaces.items():
        if not p.get("isEmpty"):
            continue
        src = p.get("borrowedFromBranch")
        for name in p.get("borrowedStars") or []:
            sid = f"star:{name}@{src}"
            if sid in node_index:
                hyperedges.append(
                    {
                        "id": f"borrow:{name}->{b}",
                        "kind": "borrow",
                        "layer": "natal",
                        "nodes": [sid, f"palace:{b}", f"palace:{src}"],
                        "weight": 0.35,
                    }
                )

    # Sanfang-sizheng hyperedges for each palace
    for b in range(12):
        group = [f"palace:{x}" for x in sanfang_sizheng(b)]
        hyperedges.append(
            {
                "id": f"sanfang:{b}",
                "kind": "sanfang_sizheng",
                "layer": "natal",
                "center": f"palace:{b}",
                "nodes": group,
                "weight": 1.0,
            }
        )

    # Year / palace stem self-sihua as higher-order operator
    for b, p in palaces.items():
        for mark in p.get("selfSihua") or []:
            star_name = mark.get("starName")
            sihua = mark.get("siHua")
            sid = f"star:{star_name}@{b}"
            if sid not in node_index:
                continue
            hyperedges.append(
                {
                    "id": f"selfsihua:{sihua}:{star_name}@{b}",
                    "kind": "self_sihua",
                    "layer": "natal",
                    "operator": sihua,
                    "nodes": [sid, f"palace:{b}", *[f"palace:{x}" for x in sanfang_sizheng(b) if x != b]],
                    "weight": SIHUA_WEIGHT.get(sihua, 0.0),
                }
            )

    # Directed sihua edges: star with siHua influences its palace triad
    for b, p in palaces.items():
        for star in p.get("stars", []) or []:
            sihua = star.get("siHua")
            if not sihua:
                continue
            sid = f"star:{star['name']}@{b}"
            targets = [f"palace:{x}" for x in sanfang_sizheng(b)]
            hyperedges.append(
                {
                    "id": f"sihua:{sihua}:{star['name']}@{b}",
                    "kind": "sihua_flow",
                    "layer": "natal",
                    "operator": sihua,
                    "source": sid,
                    "nodes": [sid, *targets],
                    "weight": SIHUA_WEIGHT.get(sihua, 0.0),
                }
            )

    # DaXian temporal layers
    layers = [
        {
            "id": "natal",
            "kind": "natal",
            "label": "本命",
        }
    ]
    for i, dx in enumerate(chart.get("daXians") or []):
        layer_id = f"daxian:{i}"
        layers.append(
            {
                "id": layer_id,
                "kind": "daxian",
                "index": i,
                "start_age": dx.get("startAge"),
                "end_age": dx.get("endAge"),
                "palace_branch": dx.get("palaceBranch"),
                "palace_name": dx.get("palaceName"),
                "label": f"大限{dx.get('startAge')}-{dx.get('endAge')}·{dx.get('palaceName')}",
            }
        )
        pb = int(dx.get("palaceBranch", 0))
        group = [f"palace:{x}" for x in sanfang_sizheng(pb)]
        hyperedges.append(
            {
                "id": f"daxian-window:{i}",
                "kind": "daxian_window",
                "layer": layer_id,
                "nodes": group,
                "weight": 1.1 if i == chart.get("currentDaXianIndex") else 0.8,
            }
        )
        # 上游可能不再输出 daXians[].siHua；改由大限宫干推四化
        si = dx.get("siHua") or {}
        transforms = {}
        if si.get("lu") or si.get("ji") or si.get("quan") or si.get("ke"):
            transforms = {
                "禄": si.get("lu") or "",
                "权": si.get("quan") or "",
                "科": si.get("ke") or "",
                "忌": si.get("ji") or "",
            }
        else:
            dx_palace = palaces.get(pb) or {}
            transforms = sihua_by_stem(dx_palace.get("stem"))
        append_sihua_edges(
            nodes=nodes,
            hyperedges=hyperedges,
            transforms=transforms,
            layer_id=layer_id,
            kind="daxian_sihua",
            group=group,
            weight_scale=1.0 if i == chart.get("currentDaXianIndex") else 0.75,
        )

    # 流年四化（当前年干）——只挂当前层，拉开 F3
    as_of_year = resolve_as_of_year(chart)
    if as_of_year is not None:
        ln_layer = f"liunian:{as_of_year}"
        layers.append(
            {
                "id": ln_layer,
                "kind": "liunian",
                "year": as_of_year,
                "label": f"流年{as_of_year}",
            }
        )
        # 流年窗口：命宫三方（人生主轴）+ 当前大限宫三方
        ming_b = chart.get("mingGongBranch")
        groups: list[str] = []
        if ming_b is not None:
            groups.extend(f"palace:{x}" for x in sanfang_sizheng(int(ming_b)))
        cur_dx = chart.get("currentDaXianIndex")
        if isinstance(cur_dx, int) and chart.get("daXians"):
            try:
                pb2 = int(chart["daXians"][cur_dx].get("palaceBranch", 0))
                groups.extend(f"palace:{x}" for x in sanfang_sizheng(pb2))
            except (IndexError, TypeError, ValueError):
                pass
        group_u = sorted(set(groups)) or [f"palace:{b}" for b in range(12)]
        hyperedges.append(
            {
                "id": f"liunian-window:{as_of_year}",
                "kind": "liunian_window",
                "layer": ln_layer,
                "nodes": group_u,
                "weight": 1.0,
            }
        )
        ln_transforms = sihua_by_stem(year_stem_index(as_of_year))
        append_sihua_edges(
            nodes=nodes,
            hyperedges=hyperedges,
            transforms=ln_transforms,
            layer_id=ln_layer,
            kind="liunian_sihua",
            group=group_u,
            weight_scale=1.05,
        )

    return {
        "schema": "ziwei.hypergraph.v1",
        "meta": {
            "ming_branch": chart.get("mingGongBranch"),
            "shen_branch": chart.get("shenGongBranch"),
            "wuxing_ju": chart.get("wuxingJuName"),
            "current_age": chart.get("currentAge"),
            "current_daxian_index": chart.get("currentDaXianIndex"),
            "as_of_year": as_of_year,
            "disclaimer": "系统势能推演，非命运断言",
        },
        "nodes": nodes,
        "hyperedges": hyperedges,
        "layers": layers,
    }



# 交友在多数盘式中已含仆役/朋友职能；仆役* 仅作别名兼容，不另开第五宫。
COMMUNITY_PALACES = {"交友", "夫妻", "迁移", "仆役", "奴仆", "仆役宫"}
# 社会兴趣更看互惠与缓冲，权控次之
F1_POS_WEIGHT = {"禄": 1.0, "科": 0.9, "权": 0.55}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_core_factors(hg: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Four-factor universal subspace. Keep this small on purpose."""
    nodes = {n["id"]: n for n in hg["nodes"]}
    palaces = [n for n in hg["nodes"] if n["kind"] == "palace"]
    community = [p for p in palaces if p.get("name") in COMMUNITY_PALACES]
    if not community:
        # fallback: branches often mapped; still score by name contains
        community = [p for p in palaces if any(k in str(p.get("name", "")) for k in ("交友", "夫妻", "迁移", "仆"))]

    # F1 Community: reciprocal positive flow into community palaces vs ji cuts
    # Only active temporal layers; natal weighted higher than current rewrite layers.
    pos = 0.0
    neg = 0.0
    community_ids = {p["id"] for p in community}
    evidence_pos = []
    evidence_neg = []
    active = active_layer_ids(hg)
    for e in hg["hyperedges"]:
        if e.get("layer") not in active:
            continue
        op = e.get("operator")
        touched = community_ids.intersection(e.get("nodes", []))
        if not touched:
            continue
        w = abs(float(e.get("weight", 0.0)))
        src = e.get("source")
        src_node = nodes.get(src or "", {})
        direct = src_node.get("palace") in COMMUNITY_PALACES
        layer_w = 1.0 if e.get("layer") == "natal" else 0.7
        if op in F1_POS_WEIGHT:
            # 关系宫内发出的互惠算满权；三方溢出只算弱贡献，防「别处有禄」虚高共同体感
            spill = 1.0 if direct else 0.28
            pos += w * F1_POS_WEIGHT[op] * spill * layer_w
            if direct:
                evidence_pos.append(e.get("id"))
        elif op == "忌":
            # 忌从关系宫星发出 = 直接切割；外宫忌扫到关系宫次之
            neg += w * (1.45 if direct else 0.7) * layer_w
            evidence_neg.append(e.get("id"))
    # empty community palaces that must borrow = belonging friction
    borrow_penalty = 0.0
    for p in community:
        if p.get("is_empty"):
            borrow_penalty += 0.22
    # soft bonus if community has membership stars present (non-empty belonging substrate)
    substrate = sum(1 for p in community if not p.get("is_empty") and p.get("state", 0) > 0)
    substrate_bonus = 0.05 * substrate
    raw = (pos + 0.15 + substrate_bonus) / (pos + neg + borrow_penalty + 0.3)
    # 轻度去饱和：压住大量 1.00，保留序关系（不对语料拟合）
    f1 = round(_clamp01(0.08 + 0.88 * raw), 4)

    # F2 Keystone: top stars already computed
    keystones = metrics.get("keystones") or []
    top = keystones[:3]
    concentration = 0.0
    if keystones:
        total = sum(k.get("score", 0) for k in keystones) or 1.0
        concentration = sum(k.get("score", 0) for k in top) / total
    f2_score = round(_clamp01(0.35 + 0.65 * concentration), 4)

    # F3 Fragility: natal 忌 weighs more; tempo layers add rewrite shock
    frags = metrics.get("ji_fragility") or []
    top3 = sum(float(x.get("ji_pressure") or 0.0) for x in frags[:3])
    active = active_layer_ids(hg)
    natal_ji = 0
    tempo_ji = 0
    for e in hg["hyperedges"]:
        if e.get("operator") != "忌" or e.get("layer") not in active:
            continue
        if e.get("layer") == "natal":
            natal_ji += 1
        else:
            tempo_ji += 1
    n_hot = len(frags)
    community_hit = 0.0
    community_names = {"交友", "夫妻", "迁移", "仆役", "奴仆", "仆役宫"}
    for x in frags[:4]:
        if x.get("palace") in community_names:
            community_hit = 0.08
            break
    raw3 = (
        0.42 * min(natal_ji, 4) / 4.0
        + 0.28 * min(tempo_ji, 4) / 4.0
        + 0.22 * min(top3, 6.0) / 6.0
        + 0.08 * min(n_hot, 6) / 6.0
        + community_hit
    )
    # keep away from automatic 1.00 while preserving rank
    f3 = round(_clamp01(0.12 + 0.78 * raw3), 4)

    # F4 Tempo: phase proximity as rewrite-window score
    f4 = round(_clamp01(float(metrics.get("phase_proximity") or 0.35)), 4)

    return {
        "version": "core-factors.v0",
        "factors": {
            "F1_community": {
                "name": "共同体感",
                "score": f1,
                "reading": "偏协作归属" if f1 >= 0.55 else ("拉锯" if f1 >= 0.35 else "偏割裂"),
                "evidence": {
                    "positive_edges": evidence_pos[:6],
                    "ji_edges": evidence_neg[:6],
                    "community_palaces": [p.get("name") for p in community],
                },
            },
            "F2_keystone": {
                "name": "承重星",
                "score": f2_score,
                "reading": "负荷集中" if f2_score >= 0.7 else "负荷较分散",
                "top": top,
            },
            "F3_fragility": {
                "name": "冲击脆弱",
                "score": f3,
                "reading": "高脆" if f3 >= 0.55 else ("中脆" if f3 >= 0.3 else "低脆"),
                "hotspots": frags[:3],
            },
            "F4_tempo": {
                "name": "节律窗口",
                "score": f4,
                "reading": "接近结构重写" if f4 >= 0.55 else "窗口平稳",
                "current_daxian_index": hg.get("meta", {}).get("current_daxian_index"),
            },
        },
        "one_liner": (
            f"共同体感{f1:.2f} / 承重集中{f2_score:.2f} / 脆弱{f3:.2f} / 节律窗口{f4:.2f}"
        ),
    }

def compute_metrics(hg: dict[str, Any]) -> dict[str, Any]:
    nodes = {n["id"]: n for n in hg["nodes"]}
    incidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in hg["hyperedges"]:
        for nid in e.get("nodes", []):
            incidence[nid].append(e)

    # Palace connectivity = number of distinct hyperedges touching it
    palace_ids = [nid for nid, n in nodes.items() if n["kind"] == "palace"]
    connectivity = {pid: len(incidence[pid]) for pid in palace_ids}
    conn_vals = list(connectivity.values()) or [0]
    connectivity_score = round(sum(conn_vals) / (len(conn_vals) * max(1, max(conn_vals))), 4)

    # Keystone candidates: high state * hyperedge degree among stars
    star_scores = []
    for nid, n in nodes.items():
        if n["kind"] != "star":
            continue
        deg = len(incidence[nid])
        score = n.get("state", 0) * deg
        # boost if carries 忌/权
        if n.get("sihua") == "忌":
            score *= 1.35
        elif n.get("sihua") == "权":
            score *= 1.15
        star_scores.append((score, n, deg))
    star_scores.sort(reverse=True, key=lambda x: x[0])
    keystones = [
        {
            "id": n["id"],
            "name": n["name"],
            "palace": n.get("palace"),
            "state": n.get("state"),
            "degree": deg,
            "sihua": n.get("sihua"),
            "score": round(score, 4),
        }
        for score, n, deg in star_scores[:5]
    ]

    # Ji fragility: active-layer 忌 only (natal + current大限 + 流年)
    active = active_layer_ids(hg)
    ji_edges_all = [e for e in hg["hyperedges"] if e.get("operator") == "忌"]
    ji_edges = [e for e in ji_edges_all if e.get("layer") in active]
    fragile_palaces: dict[str, float] = defaultdict(float)
    for e in ji_edges:
        layer_w = 1.0 if e.get("layer") == "natal" else 0.75
        for nid in e.get("nodes", []):
            if nid.startswith("palace:"):
                fragile_palaces[nodes[nid]["name"]] += abs(float(e.get("weight", -1.0))) * layer_w
    fragility_ranked = sorted(
        ({"palace": k, "ji_pressure": round(v, 4)} for k, v in fragile_palaces.items()),
        key=lambda x: x["ji_pressure"],
        reverse=True,
    )

    # Resilience proxy inspired by d·s : corr-like aggregate of degree*state for stars
    ds_vals = []
    for score, n, deg in star_scores:
        ds_vals.append(n.get("state", 0) * deg)
    if ds_vals:
        mean_ds = sum(ds_vals) / len(ds_vals)
        # normalize roughly into 0..1 via logistic
        resilience = round(1 / (1 + math.exp(-(mean_ds - 2.0))), 4)
    else:
        resilience = 0.5

    # Phase proximity: rewrite-window score.
    # Upstream engine may omit daXian.siHua; do not depend on it.
    cur = hg["meta"].get("current_daxian_index")
    age = hg["meta"].get("current_age")
    phase = 0.35
    daxian_layers = [L for L in hg.get("layers", []) if L.get("kind") == "daxian"]
    if cur is not None and daxian_layers:
        # clamp index
        if isinstance(cur, int) and 0 <= cur < len(daxian_layers):
            L = daxian_layers[cur]
            start = L.get("start_age")
            end = L.get("end_age")
            edge = 0.0
            if age is not None and start is not None and end is not None and end > start:
                # nearer to boundary => higher rewrite pressure
                span = float(end - start)
                pos = float(age - start) / span
                edge = max(0.0, 1.0 - min(pos, 1.0 - pos) / 0.35)
            # community/daxian overlap via window edges
            win = [e for e in hg["hyperedges"] if e.get("id") == f"daxian-window:{cur}"]
            community_names = {"交友", "夫妻", "迁移", "仆役", "奴仆", "仆役宫"}
            overlap = 0.0
            if win:
                nodes = {n["id"]: n for n in hg["nodes"]}
                for nid in win[0].get("nodes", []):
                    nm = nodes.get(nid, {}).get("name")
                    if nm in community_names:
                        overlap = 0.25
                        break
            # natal ji touching current window
            ji_touch = 0.0
            if win:
                wset = set(win[0].get("nodes", []))
                for e in hg["hyperedges"]:
                    if e.get("operator") == "忌" and wset.intersection(e.get("nodes", [])):
                        ji_touch = 0.2
                        break
            phase = round(min(0.95, 0.2 + 0.55 * edge + overlap + ji_touch), 4)

    return {
        "connectivity": connectivity_score,
        "resilience": resilience,
        "phase_proximity": phase,
        "keystones": keystones,
        "ji_fragility": fragility_ranked[:6],
        "counts": {
            "nodes": len(hg["nodes"]),
            "hyperedges": len(hg["hyperedges"]),
            "layers": len(hg["layers"]),
            "ji_edges": len(ji_edges),
            "ji_edges_all": len(ji_edges_all),
            "active_layers": sorted(active),
        },
    }


def to_mermaid(hg: dict[str, Any], metrics: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    # show ming + top keystones only to keep readable
    ming_branch = hg["meta"].get("ming_branch")
    if ming_branch is not None:
        ming = next((n for n in hg["nodes"] if n["id"] == f"palace:{ming_branch}"), None)
        if ming:
            lines.append(f'  ming["命宫·{ming["name"]}"]')
    for ks in metrics.get("keystones", [])[:4]:
        safe = ks["id"].replace("@", "_").replace(":", "_")
        label = f'{ks["name"]}@{ks.get("palace","?")}'
        lines.append(f'  {safe}["{label}"]')
        lines.append(f"  ming --> {safe}")
    for frag in metrics.get("ji_fragility", [])[:3]:
        safe = "frag_" + frag["palace"]
        lines.append(f'  {safe}[["忌压·{frag["palace"]}={frag["ji_pressure"]}"]]')
        lines.append(f"  ming -.-> {safe}")
    return "\n".join(lines)




def _force_utf8_stdout() -> None:
    """Windows CI 控制台默认非 UTF-8，中文输出会抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def main() -> int:
    _force_utf8_stdout()
    ap = argparse.ArgumentParser(description="Convert ZiweiChart JSON to temporal hypergraph")
    ap.add_argument("chart_json", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None, help="output hypergraph json")
    ap.add_argument("--mermaid", type=Path, default=None, help="optional mermaid summary path")
    ap.add_argument("--matter", type=str, default="", help="具体事项，如：今年跳槽合适吗")
    ap.add_argument(
        "--prompt-out",
        type=Path,
        default=None,
        help="写出可粘贴给其他 AI 的提示词文件；默认与 out 同名 .prompt.md",
    )
    ap.add_argument(
        "--no-prompt",
        action="store_true",
        help="不生成 prompt 文件（默认会生成）",
    )
    args = ap.parse_args()

    chart = json.loads(args.chart_json.read_text(encoding="utf-8"))
    hg = build_hypergraph(chart)
    metrics = compute_metrics(hg)
    factors = compute_core_factors(hg, metrics)
    payload = {
        "hypergraph": hg,
        "metrics": metrics,
        "factors": factors,
        "mermaid": to_mermaid(hg, metrics),
    }
    payload["plain"] = explain_payload(payload)
    matter_text = (args.matter or "").strip() or None
    payload["matter"] = explain_matter(payload, matter_text)
    user_prompt = build_user_prompt(payload, matter_text)
    system_prompt = build_system_prompt()
    payload["prompt_pack"] = {
        "system": system_prompt,
        "user": user_prompt,
        "mode": "paste-to-any-ai",
    }

    out = args.out
    if out is None:
        out = args.chart_json.with_name(args.chart_json.stem + ".hypergraph.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.mermaid:
        args.mermaid.write_text(payload["mermaid"] + "\n", encoding="utf-8")

    if not args.no_prompt:
        prompt_path = args.prompt_out
        if prompt_path is None:
            prompt_path = out.with_suffix(".prompt.md")
        prompt_body = (
            "# 可粘贴给任意 AI 的提示包\n\n"
            "## System\n\n"
            f"{system_prompt}\n"
            "## User\n\n"
            f"{user_prompt}"
        )
        prompt_path.write_text(prompt_body, encoding="utf-8")
        print("prompt:", prompt_path)

    print("schema:", hg["schema"])
    print("nodes/edges/layers:", metrics["counts"]["nodes"], metrics["counts"]["hyperedges"], metrics["counts"]["layers"])
    print("connectivity/resilience/phase:", metrics["connectivity"], metrics["resilience"], metrics["phase_proximity"])
    print("keystones:", ", ".join(f"{k['name']}@{k['palace']}" for k in metrics["keystones"][:3]))
    print("factors:", factors["one_liner"])
    if matter_text:
        print("matter:", payload["matter"]["focus"]["label"], "|", (payload["matter"].get("plain") or "")[:80])
    print("wrote:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())