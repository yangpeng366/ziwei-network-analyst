#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验静态站数据与代码生成结果一致（按 JSON 语义比较，忽略换行差异）。

用法：
  python scripts/check-site-drift.py             # 一致 → OK / 退出 0；不一致 → 退出 1 并点名首个差异
  python scripts/check-site-drift.py --selftest  # 规则自测：集合/顺序/字段/顶层/缺盘/格式负例必须打红

缺盘纪律：必需 fixture 缺失 → 直接打红（不再等 build_payload 静默 skip 后比出一个「一致」）；
本地私有盘缺失 → 显式 WARN：它必须出现在产物 missing_charts 里，少盘才会被 diff 看见。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import (  # noqa: E402
    OUT,
    MissingFixtureError,
    build_payload,
    collect_missing,
    format_missing,
    rel_path,
)

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
            "missing_charts": [],
            "charts": [ch("sample"), ch("real-a")]}
    lost = {"id": "real-a", "path": "fixtures/real-1990/1990-01-01-0-male.json",
            "required": False, "note": "真实生盘"}

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
        # 缺盘留痕：少一张盘 + missing_charts 跟着变，必须打红（先点集合，再点顶层）
        ("缺盘且 missing_charts 变化 -> 打红", base,
         {**base, "charts": [ch("sample")], "missing_charts": [lost]},
         "图表集合不一致（多 real-a）"),
        ("盘没少但 missing_charts 变了 -> 打红", base,
         {**base, "missing_charts": [lost]}, "顶层字段 missing_charts"),
        ("missing_charts 同为空 -> 放行", base, json.loads(json.dumps(base)), None),
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

    # 缺盘肥则：必需缺 -> 必红且点名；本地私有缺 -> 必进缺盘清单（不能被静默 skip 掉）
    missing_required, missing_local = collect_missing()
    expect("必需 fixture 缺失时点名可读",
           all(rel_path(s.path).startswith("fixtures/") for s in missing_required), True)
    expect("缺盘分类不重叠",
           sorted({s.id for s in missing_required} & {s.id for s in missing_local}), [])
    try:
        build_payload(strict=True, log=False)
        got_strict: object = "未抛错"
    except MissingFixtureError as exc:
        got_strict = sorted(s.id for s in exc.specs) == sorted(s.id for s in missing_required)
    expect("strict 构建与缺盘清单一致", got_strict, True if missing_required else "未抛错")
    expect("缺盘清单必须含在产物里（本地私有盘不静默）",
           all(s.id in {m["id"] for m in build_payload(strict=False, log=False)["missing_charts"]}
               for s in [*missing_required, *missing_local]), True)

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
        print("缺少", rel_path(OUT))
        return 1

    # 先查缺盘：必需缺盘时连「一致」都谈不上（以前是 build_payload 静默 skip，然后比出一个假 OK）
    missing_required, missing_local = collect_missing()
    if missing_required:
        print("SITE DATA FAIL：缺少必需 fixture，无法生成完整站点数据")
        print(format_missing(missing_required))
        print("  修法：补齐 fixture 后重跑 python scripts/build_site.py（勿手改 charts.js）")
        return 1
    for spec in missing_local:
        print("WARN 缺本地私有 fixture：{}（{}）—— 站点少这张盘，已记入 missing_charts".format(
            spec.id, rel_path(spec.path)), file=sys.stderr)

    try:
        committed = parse_payload_text(OUT.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        print("SITE DATA FAIL：{}".format(exc))
        return 1
    try:
        fresh = build_payload()
    except MissingFixtureError as exc:
        print("SITE DATA FAIL：{}".format(exc))
        return 1
    diff = describe_diff(committed, fresh)
    if diff is None:
        print("SITE DATA OK")
        return 0
    print("SITE DATA FAIL：差异：{}".format(diff))
    print("  修法：python scripts/build_site.py 重新生成 docs/data/charts.js（勿手改生成物）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
