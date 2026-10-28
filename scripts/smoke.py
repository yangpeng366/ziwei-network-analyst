#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冒烟测试：出盘 -> 四因子 -> 白话 -> 事项 -> 提示包，任一环节缺失即失败。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import explain_matter  # noqa: E402
from matter_query.prompt_pack import build_system_prompt, build_user_prompt  # noqa: E402
from timeline.sweep import sweep_payload  # noqa: E402
from matter_query.facts import facts_for  # noqa: E402

CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
CHART = ROOT / "fixtures" / "sample-chart.json"

CASES = [
    ("今年适合跳槽吗", "事业职场"),
    ("这段感情能长久吗", "亲密关系"),
    ("今年身体要注意什么", "身体消耗"),
    ("什么时候适合换房", "安家置业"),
    ("要不要辞职去外地发展", "事业职场＋外出变动"),
    ("", "整体态势"),
]


def _force_utf8_stdout() -> None:
    """Windows CI 控制台默认非 UTF-8，中文输出会抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def main() -> int:
    _force_utf8_stdout()
    if not CHART.exists():
        print("缺少 fixtures/sample-chart.json"); return 1
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "chart.json"
        tmp.write_text(CHART.read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.check_call([sys.executable, str(CONV), str(tmp), "--no-prompt"],
                              cwd=str(ROOT), stdout=subprocess.DEVNULL)
        payload = json.loads((tmp.with_name("chart.hypergraph.json")).read_text(encoding="utf-8"))

    factors = payload.get("factors", {}).get("factors", {})
    for key in ("F1_community", "F2_keystone", "F3_fragility", "F4_tempo"):
        if key not in factors:
            print("缺因子", key); return 1
        if factors[key].get("reading") is None:
            print("因子无读法", key); return 1

    payload["plain"] = explain_payload(payload)
    if not payload["plain"].get("summary"):
        print("缺白话摘要"); return 1
    if len(payload["plain"].get("factors_plain") or {}) != 4:
        print("白话因子数不对"); return 1

    for query, expect_label in CASES:
        matter = explain_matter(payload, query or None)
        label = matter["focus"]["label"]
        if label != expect_label:
            print(f"事项归类错：{query!r} -> {label}，期望 {expect_label}"); return 1
        if not matter.get("plain"):
            print("缺事项白话", query); return 1

    chart = json.loads(CHART.read_text(encoding="utf-8"))
    facts = facts_for(chart, payload["matter"].get("focus") or {})
    if len(facts.get("twelve") or []) != 12:
        print("十二宫一览不齐", len(facts.get("twelve") or [])); return 1
    if not facts.get("cards"):
        print("缺相关宫详卡"); return 1
    payload["facts"] = facts
    p0 = build_user_prompt(payload, "今年适合跳槽吗")
    if "盘面事实" not in p0 or "十二宫一览" not in p0:
        print("提示词缺事实卡"); return 1

    tl = sweep_payload(chart, 2020, 2032)
    if len(tl.get("rows") or []) != 13:
        print("逐年推演行数不对", len(tl.get("rows") or [])); return 1
    if not tl.get("plain", {}).get("summary"):
        print("缺逐年白话"); return 1
    if not (tl.get("transition_years") or tl.get("move_years") is not None):
        print("缺交接年信息"); return 1

    prompt = build_user_prompt(payload, "今年适合跳槽吗", tl)
    if "逐年推演" not in prompt:
        print("提示包未带逐年推演"); return 1

    prompt = build_user_prompt(payload, "今年适合跳槽吗")
    if "今年适合跳槽吗" not in prompt:
        print("提示包未带事项"); return 1
    if not build_system_prompt().strip():
        print("缺 system 提示"); return 1

    print("SMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())