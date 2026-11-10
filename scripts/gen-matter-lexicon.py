#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 catalog.json 生成「问法 → 宫位」速查表 docs/matter-lexicon.md。

唯一真源是 packages/matter_query/catalog.json：本脚本只做确定性渲染，
不手写任何类别事实（类别名 / 宫位 / 因子 / 镜头 / 关键词全部来自目录）。
suggestions 与提示文案直接复用 packages/matter_query/map.py 的实现，
保证速查表、CLI、静态站看到的是同一套词与同一句话。

手改 docs/matter-lexicon.md 会被 scripts/check-matter-lexicon.py 打红。

用法：
  python scripts/gen-matter-lexicon.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from matter_query.map import fallback_hint_text, matter_suggestions  # noqa: E402

CATALOG = ROOT / "packages" / "matter_query" / "catalog.json"
OUT = ROOT / "docs" / "matter-lexicon.md"

HEADER = "本文件由 scripts/gen-matter-lexicon.py 生成，勿手改。"

FACTOR_LABELS = {
    "F1_community": "共同体感",
    "F2_keystone": "承重集中",
    "F3_fragility": "冲击脆弱",
    "F4_tempo": "节律窗口",
}

SEP = " / "
KW_SEP = "、"


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _factors(ids: list[str] | None) -> str:
    return SEP.join(FACTOR_LABELS.get(str(f), str(f)) for f in (ids or []))


def _keywords(cat: dict[str, Any]) -> list[str]:
    return [k for k in (cat.get("keywords") or []) if k]


def _examples(cat: dict[str, Any]) -> list[str]:
    """示例问法：只由本类关键词拼装，不引入目录外的词。"""
    kws = _keywords(cat)
    if not kws:
        return []

    def pick(i: int) -> str:
        return kws[i % len(kws)]

    return [
        "今年{}怎么样？".format(pick(0)),
        "想问问{}的事，什么时候合适？".format(pick(1)),
        "{}和{}，哪个更该先动？".format(pick(2), pick(3)),
    ]


def render(data: dict[str, Any] | None = None) -> str:
    data = data or load_catalog()
    cats = data.get("categories") or []
    suggestions = matter_suggestions()
    hint = fallback_hint_text(suggestions)
    max_examples = int((data.get("fallback_hint") or {}).get("max_examples") or 0)

    L: list[str] = []
    L.append("# 事项问法 → 宫位速查表")
    L.append("")
    L.append("> " + HEADER)
    L.append("> 唯一数据源：`packages/matter_query/catalog.json`（version {}）。".format(data.get("version")))
    L.append("> 改词请改目录后重跑 `python scripts/gen-matter-lexicon.py`；")
    L.append("> 手改本文件会被 `python scripts/check-matter-lexicon.py` 打红。")
    L.append("")
    L.append("打分口径与阈值见 `docs/matter-query.md`；两端实现为 `packages/matter_query/map.py`（Python）")
    L.append("与 `docs/matter.js`（静态站），同一份目录、同一套规则。")
    L.append("")

    L.append("## 总览（按目录顺序）")
    L.append("")
    L.append("| # | 类别 | id | 相关宫位 | 关注因子 | 关键词数 |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for i, cat in enumerate(cats, 1):
        tag = "（兜底）" if cat.get("fallback") else ""
        L.append(
            "| {} | {}{} | {} | {} | {} | {} |".format(
                i,
                cat.get("label"),
                tag,
                cat.get("id"),
                SEP.join(str(p) for p in (cat.get("palaces") or [])),
                _factors(cat.get("focus_factors")),
                len(_keywords(cat)),
            )
        )
    L.append("")

    L.append("## 兜底：问法没被识别时")
    L.append("")
    L.append("问题落到 `general`（`matched=false`）时，CLI 与静态站显示同一句话，")
    L.append("模板唯一存放于 catalog.json 的 `fallback_hint`：")
    L.append("")
    L.append("> " + hint)
    L.append("")
    L.append("可试说法按目录顺序取各类前 4 个关键词（原序），提示里截前 {} 个：".format(max_examples or "全部"))
    L.append("")
    for s in suggestions:
        L.append("- {}（{}）：{}".format(s["label"], s["matter_id"], KW_SEP.join(s["keywords"])))
    L.append("")

    for cat in cats:
        if cat.get("fallback"):
            continue
        kws = _keywords(cat)
        L.append("## {}（{}）".format(cat.get("label"), cat.get("id")))
        L.append("")
        L.append("- 相关宫位：" + SEP.join(str(p) for p in (cat.get("palaces") or [])))
        L.append("- 关注因子：" + _factors(cat.get("focus_factors")))
        L.append("- 关注镜头：" + str(cat.get("lens") or ""))
        L.append("- 关键词（{} 个）：{}".format(len(kws), KW_SEP.join(kws)))
        L.append("")
        L.append("示例问法（词均取自本类关键词）：")
        L.append("")
        for i, ex in enumerate(_examples(cat), 1):
            L.append("{}. {}".format(i, ex))
        L.append("")

    general = next((c for c in cats if c.get("fallback")), None)
    if general is not None:
        kws = _keywords(general)
        L.append("## {}（{}）· 兜底类".format(general.get("label"), general.get("id")))
        L.append("")
        L.append(
            "- 兜底身份：`fallback=true`。打分阶段**跳过**该类的关键词，"
            "只有其他类别一个都没命中（含问题为空、只有时间词）时才启用。"
        )
        L.append(
            "- 启用后的口径：`matched=false`，事实卡只给十二宫一览 + 宫义速查，不再逐宫铺开；"
            "并附 `suggestions`（可试说法）与 `hint`（问法没被识别的提示）。"
        )
        L.append("- 相关宫位：" + SEP.join(str(p) for p in (general.get("palaces") or [])))
        L.append("- 关注因子：" + _factors(general.get("focus_factors")))
        L.append("- 关注镜头：" + str(general.get("lens") or ""))
        L.append(
            "- 关键词（{} 个，仅作文案参考：打分阶段跳过兜底类，这些词不会命中任何类别）：{}".format(
                len(kws), KW_SEP.join(kws)
            )
        )
        L.append("")
        L.append("示例问法（词均取自本类关键词）：")
        L.append("")
        for i, ex in enumerate(_examples(general), 1):
            L.append("{}. {}".format(i, ex))
        L.append("")

    return "\n".join(L).rstrip("\n") + "\n"


def write_text(text: str, path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def main() -> int:
    _force_utf8_stdout()
    text = render()
    path = write_text(text)
    print("wrote: {} ({} bytes)".format(path, path.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
