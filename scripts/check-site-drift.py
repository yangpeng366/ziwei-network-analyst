#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验静态站数据与代码生成结果一致（按 JSON 语义比较，忽略换行差异）。

用法：
  python scripts/check-site-drift.py             # 一致 → OK / 退出 0；不一致 → 退出 1 并点名首个差异
  python scripts/check-site-drift.py --selftest  # 规则自测：集合/顺序/字段/顶层/格式负例必须打红
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import OUT, build_payload  # noqa: E402

PREFIX = "window.ZIWEI_DATA = "


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def parse_payload_text(raw: str) -> dict:
    """把 charts.js 文本解成 dict；格式不对抛 ValueError（自测直接喂字符串，不碰磁盘）。"""
    text = raw.lstrip("\ufeff").lstrip()
    if not text.startswith(PREFIX):
        raise ValueError("charts.js 格式不对：缺少 window.ZIWEI_DATA = 前缀")
    body = text[len(PREFIX):].strip()
    if body.endswith(";"):
        body = body[:-1]
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("charts.js 内容不是合法 JSON：{}".format(exc)) from exc
    if not isinstance(data, dict):
        raise ValueError("charts.js 顶层不是对象")
    return data


def _chart_ids(data: dict) -> list:
    charts = data.get("charts")
    if not isinstance(charts, list):
        return []
    return [c.get("id") if isinstance(c, dict) else c for c in charts]


def describe_diff(committed: dict, fresh: dict) -> str | None:
    """返回首个差异的一句话描述；完全一致返回 None。空字符串不返回。

    比较顺序：图表集合 → 图表顺序 → 逐图逐字段 → 其余顶层字段。
    """
    if committed == fresh:
        return None

    old_ids, new_ids = _chart_ids(committed), _chart_ids(fresh)
    if set(old_ids) != set(new_ids):
        missing = [i for i in new_ids if i not in set(old_ids)]
        extra = [i for i in old_ids if i not in set(new_ids)]
        parts = []
        if missing:
            parts.append("缺 " + ", ".join(str(i) for i in missing))
        if extra:
            parts.append("多 " + ", ".join(str(i) for i in extra))
        return "图表集合不一致（{}）".format("；".join(parts) or "数量不同")
    if old_ids != new_ids:
        return "图表顺序不一致（committed: {} / fresh: {}）".format(old_ids, new_ids)

    for a, b in zip(committed.get("charts") or [], fresh.get("charts") or []):
        if not isinstance(a, dict) or not isinstance(b, dict):
            return "chart 数据不是对象"
        for k in list(a.keys()) + [k for k in b if k not in a]:
            if a.get(k) != b.get(k):
                return "chart {} 的 {}".format(a.get("id"), k)

    for k in list(committed.keys()) + [k for k in fresh if k not in committed]:
        if committed.get(k) != fresh.get(k):
            return "顶层字段 {}".format(k)

    return "内容不同但未能定位（可能是列表元素顺序不同）"


def _selftest() -> int:
    """负例自测：漂移真的会打红？差异定位真的指到对的地方？格式异常真的报错？

    只测纯函数 parse_payload_text / describe_diff / _chart_ids，不落盘、不跑 build_payload。
    规则被改成「永远 OK」时这里先红，比等真文件漂移更早。
    """
    def ch(cid: str, label: str = "x") -> dict:
        return {"id": cid, "label": label, "daXian": [{"startAge": 3}]}

    base = {"generated_by": "scripts/build_site.py", "matters": [{"id": "m"}],
            "charts": [ch("sample"), ch("real-a")]}

    diff_cases: list[tuple[str, dict, dict, str | None]] = [
        ("完全相同 -> 放行", base, json.loads(json.dumps(base)), None),
        ("图表多一张 -> 打红并点名", base,
         {**base, "charts": base["charts"] + [ch("real-b")]}, "图表集合不一致（缺 real-b）"),
        ("图表少一张 -> 打红并点名", base,
         {**base, "charts": [ch("sample")]}, "图表集合不一致（多 real-a）"),
        ("同集合换顺序 -> 打红", base,
         {**base, "charts": [ch("real-a"), ch("sample")]}, "图表顺序不一致（committed: ['sample', 'real-a'] / fresh: ['real-a', 'sample']）"),
        ("图表字段变化 -> 打红并点名字段", base,
         {**base, "charts": [ch("sample", "改过的标签"), ch("real-a")]}, "chart sample 的 label"),
        ("图表新增字段 -> 打红并点名字段", base,
         {**base, "charts": [{**ch("sample"), "extra": 1}, ch("real-a")]}, "chart sample 的 extra"),
        ("顶层字段变化 -> 打红并点名", base,
         {**base, "matters": [{"id": "m2"}]}, "顶层字段 matters"),
        ("顶层新增字段 -> 打红并点名", base,
         {**base, "sweep_range": [2015, 2050]}, "顶层字段 sweep_range"),
        ("图表不是对象 -> 打红", {"charts": [ch("sample")]},
         {"charts": ["sample"]}, "chart 数据不是对象"),
    ]

    parse_cases: list[tuple[str, str, bool]] = [
        ("标准前缀 + 分号", PREFIX + '{"a":1};\n', True),
        ("无分号", PREFIX + '{"a":1}', True),
        ("多余空白/换行 -> 仍解析", "\n" + PREFIX + '\n{"a": 1}\n\n', True),
        ("带 BOM -> 仍解析", "\ufeff" + PREFIX + '{"a":1};\n', True),
        ("缺前缀 -> 报错", '{"a":1};', False),
        ("前缀对但 JSON 坏 -> 报错", PREFIX + "{a:1};", False),
        ("顶层是数组 -> 报错", PREFIX + "[1,2];", False),
    ]

    failures: list[str] = []
    total = 0

    def expect(name: str, got, want) -> None:
        nonlocal total
        total += 1
        if got != want:
            failures.append("{}：期望 {!r}，实际 {!r}".format(name, want, got))

    for name, committed, fresh, want in diff_cases:
        try:
            got = describe_diff(committed, fresh)
        except Exception as exc:  # 规则崩了也算失败（例如把 dict 丢进 set）
            got = "崩溃：{}: {}".format(type(exc).__name__, exc)
        expect(name, got, want)

    for name, raw, ok in parse_cases:
        try:
            parse_payload_text(raw)
            got_ok = True
        except ValueError:
            got_ok = False
        except Exception as exc:
            got_ok = "非 ValueError：{}".format(type(exc).__name__)
        expect(name, got_ok, ok)

    if failures:
        print("SITE DRIFT SELFTEST FAIL：{}/{} 条不符".format(len(failures), total))
        for item in failures:
            print("  - {}".format(item))
        return 1
    print("SITE DRIFT SELFTEST OK：{} 项（集合/顺序/字段/顶层/格式负例打红，格式变体放行）".format(total))
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        if args[0] in ("--selftest", "selftest"):
            return _selftest()
        print("未知参数：{}（用法：python scripts/check-site-drift.py [--selftest]）".format(" ".join(args)))
        return 2

    if not OUT.exists():
        print("缺少", OUT)
        return 1
    try:
        committed = parse_payload_text(OUT.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        print("SITE DATA FAIL：{}".format(exc))
        return 1
    fresh = build_payload()
    diff = describe_diff(committed, fresh)
    if diff is None:
        print("SITE DATA OK")
        return 0
    print("SITE DATA FAIL：差异：{}".format(diff))
    print("  修法：python scripts/build_site.py 重新生成 docs/data/charts.js（勿手改生成物）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
