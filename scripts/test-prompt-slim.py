#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提示词瘦身回归：事实卡不许重复铺星曜，宽泛提问不许逐宫铺开。

背景：提示词曾把同一份星曜在「十二宫一览」和「详卡」里各写一遍；问题没命中
关键词时更是把十二张详卡全展开，上下文越喂越肥。本检查锁住三条线：

1. 星曜只在十二宫一览给一次，详卡只补宫义（证据不许丢，也不许重复）
2. 未命中关键词时不铺开十二张详卡，只给十二宫一览 + 宫义速查
3. 宫名不叠字（「命宫宫」）、四化飞入不丢
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from matter_query.facts import build_facts, facts_for  # noqa: E402
from matter_query.prompt_pack import render_facts_text  # noqa: E402

CHART = ROOT / "fixtures" / "sample-chart.json"


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _card_lines(text: str) -> list[str]:
    return [l for l in text.splitlines() if l.startswith("  - ") and "（" in l]


def main() -> int:
    _force_utf8_stdout()
    if not CHART.exists():
        print("缺少 fixtures/sample-chart.json")
        return 1
    chart = json.loads(CHART.read_text(encoding="utf-8"))
    errs: list[str] = []

    focus_hit = {"matched": True, "palaces": ["官禄", "仆役", "财帛", "迁移"], "label": "事业职场"}
    hit = facts_for(chart, focus_hit)
    t_hit = render_facts_text(hit)

    focus_miss = {"matched": False, "palaces": [], "label": "整体态势"}
    miss = facts_for(chart, focus_miss)
    t_miss = render_facts_text(miss)

    # 1) 命中：十二宫齐全，详卡只带相关宫
    if len(hit.get("twelve") or []) != 12:
        errs.append("十二宫一览不齐：{}".format(len(hit.get("twelve") or [])))
    if not hit.get("cards"):
        errs.append("命中时应有相关宫详卡")
    elif len(hit["cards"]) > 6:
        errs.append("相关宫详卡超过 6 个：{}".format(len(hit["cards"])))

    # 2) 详卡不再重复星曜
    for line in _card_lines(t_hit):
        if "主星" in line or "辅星" in line:
            errs.append("详卡仍在重复星曜：" + line.strip())
            break

    # 3) 证据没丢：详卡里的星曜仍能在十二宫一览里找到
    twelve_by_name = {str(r.get("name") or ""): r for r in hit.get("twelve") or []}
    for c in hit.get("cards") or []:
        row = twelve_by_name.get(str(c.get("name") or ""))
        if not row:
            errs.append("详卡宫位不在十二宫一览：" + str(c.get("name")))
            continue
        for s in c.get("major") or []:
            if str(s.get("name")) not in "、".join(row.get("major") or []):
                errs.append("星曜在详卡与一览之间对不上：{} / {}".format(c.get("name"), s.get("name")))

    # 4) 未命中：不铺十二张详卡
    if miss.get("cards"):
        errs.append("未命中关键词时不应铺开详卡：{} 张".format(len(miss["cards"])))
    if "与本题直接相关的宫" in t_miss:
        errs.append("未命中关键词时仍出现相关宫详卡段")
    if "宫义速查" not in t_miss:
        errs.append("未命中关键词时缺宫义速查")
    if "十二宫一览" not in t_miss:
        errs.append("未命中关键词时缺十二宫一览")

    # 5) 体积：未命中口径必须显著短于「十二宫全详卡」口径
    all_names = [str(r.get("name") or "") for r in miss.get("twelve") or []]
    t_all = render_facts_text(build_facts(chart, all_names))
    if len(t_miss) >= len(t_all) * 0.85:
        errs.append(
            "未命中口径未变瘦：{} vs 全详卡 {}".format(len(t_miss), len(t_all))
        )

    # 6) 宫名不叠字、四化飞入不丢
    for name, text in (("命中", t_hit), ("未命中", t_miss)):
        if "宫宫" in text:
            errs.append("{}口径出现叠字「宫宫」".format(name))
        if "生年四化飞入" not in text:
            errs.append("{}口径缺生年四化飞入".format(name))
        if "当前大限" not in text:
            errs.append("{}口径缺当前大限".format(name))

    if errs:
        print("PROMPT SLIM FAIL（{} 项）".format(len(errs)))
        for e in errs:
            print(" - {}".format(e))
        return 1
    print(
        "PROMPT SLIM PASS：命中 {0} 字（详卡 {1} 张）/ 未命中 {2} 字（对比全详卡 {3} 字）".format(
            len(t_hit), len(hit.get("cards") or []), len(t_miss), len(t_all)
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
