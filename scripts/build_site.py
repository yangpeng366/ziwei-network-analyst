#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成静态站数据：docs/data/charts.js（双击 index.html 亦可运行，无需服务器）。

同一份数据也用于本地演示与 GitHub Pages，因此生成必须可复现：
- 浮点统一四舍五入到 4 位
- 固定 LF 换行

缺盘纪律（曾经是静默 skip，站点少盘也照样 OK，谁都不知道）：
- required=True：仓内必需的 fixture。缺 → 抛 MissingFixtureError / CLI 退出 1，且不写 charts.js
- required=False：本地私有 fixture（fixtures/real-1990/ 被 .gitignore 排除，CI 上必然没有）。
  缺 → 显式 WARN 并写进产物顶层 missing_charts，让「站点少了哪张盘」变成可 diff 的事实，而不是沉默
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import MATTER_CATALOG, TIME_KEYWORDS, FALLBACK_HINT  # noqa: E402
from matter_query.facts import build_facts, twelve_palaces  # noqa: E402
from matter_query.prompt_pack import render_facts_text  # noqa: E402
from timeline.sweep import sweep_payload, chart_for_year  # noqa: E402
from hypergraph.chart2hypergraph import build_hypergraph, compute_core_factors, compute_metrics  # noqa: E402

OUT = ROOT / "docs" / "data" / "charts.js"

class ChartSpec(NamedTuple):
    """一张要进站点的盘。required 决定缺盘时是打红还是只告警（见模块 docstring）。"""

    id: str
    label: str
    path: Path
    required: bool = True
    note: str = ""


# 演示盘列表：样例盘（仓内必需）+ 两个真实 1990 生盘（本地私有，gitignore，CI 上没有）
CHARTS: list[ChartSpec] = [
    ChartSpec("sample", "演示盘（1990-05-15 辰时）", ROOT / "fixtures" / "sample-chart.json"),
    ChartSpec(
        "real-a",
        "真实盘 A（1990-01-01 子时）",
        ROOT / "fixtures" / "real-1990" / "1990-01-01-0-male.json",
        required=False,
        note="真实生盘，fixtures/real-1990/ 不入仓，仅本地构建可见",
    ),
    ChartSpec(
        "real-b",
        "真实盘 B（1990-09-20 巳时）",
        ROOT / "fixtures" / "real-1990" / "1990-09-20-6-male.json",
        required=False,
        note="真实生盘，fixtures/real-1990/ 不入仓，仅本地构建可见",
    ),
]
SWEEP_FROM, SWEEP_TO = 2015, 2050

MISSING_HINT = "修法：补齐 fixture；确要生成不完整站请显式加 --allow-missing"


class MissingFixtureError(RuntimeError):
    """必需 fixture 缺失：拒绝生成，避免站点静默少盘。"""

    def __init__(self, specs: Sequence[ChartSpec]) -> None:
        self.specs = list(specs)
        super().__init__("缺少必需 fixture：" + "、".join(s.id for s in self.specs))


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def rel_path(path: Path) -> str:
    """仓内相对路径（正斜杠）；仓外路径原样返回。产物里不留机器绝对路径。"""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collect_missing(
    charts: Sequence[ChartSpec] | None = None,
    exists=None,
) -> tuple[list[ChartSpec], list[ChartSpec]]:
    """(必需缺失, 本地私有缺失)。exists 可注入，便于自测不碰磁盘。"""
    specs = tuple(CHARTS if charts is None else charts)
    probe = (lambda p: Path(p).exists()) if exists is None else exists
    required, local = [], []
    for spec in specs:
        if probe(spec.path):
            continue
        (required if spec.required else local).append(spec)
    return required, local


def format_missing(specs: Sequence[ChartSpec]) -> str:
    return "\n".join("  - {}（{}）{}".format(s.id, rel_path(s.path), ("：" + s.note) if s.note else "") for s in specs)


def _round_floats(obj: Any) -> Any:
    """递归四舍五入浮点，保证跨 Python 版本一致。"""
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v) for v in obj]
    return obj


def build_payload(
    charts: Sequence[ChartSpec] | None = None,
    strict: bool = True,
    log: bool = True,
) -> dict:
    """生成站点数据。strict=True 时必需 fixture 缺失直接抛错（默认，不写盘）。"""
    specs = tuple(CHARTS if charts is None else charts)
    missing_required, missing_local = collect_missing(specs)
    if missing_required and strict:
        raise MissingFixtureError(missing_required)
    if log:
        if missing_required:
            print("WARN 缺必需 fixture（--allow-missing 放行，产物不完整）：", file=sys.stderr)
            print(format_missing(missing_required), file=sys.stderr)
        for spec in missing_local:
            print("WARN 缺本地私有 fixture：{}（{}）：已记入 missing_charts".format(
                spec.id, rel_path(spec.path)), file=sys.stderr)
    missing_ids = {s.id for s in missing_required} | {s.id for s in missing_local}

    out_charts = []
    for spec in specs:
        if spec.id in missing_ids:
            continue
        cid, label, path = spec.id, spec.label, spec.path
        chart = json.loads(path.read_text(encoding="utf-8"))
        birth = chart.get("birthInfo") or {}
        base = {
            "id": cid,
            "label": label,
            "birth": {
                "year": birth.get("year"),
                "month": birth.get("month"),
                "day": birth.get("day"),
                "hour": birth.get("hour"),
                "gender": birth.get("gender"),
                "city": birth.get("city"),
            },
            "daXian": [
                {
                    "startAge": dx.get("startAge"),
                    "endAge": dx.get("endAge"),
                    "palaceName": dx.get("palaceName"),
                }
                for dx in (chart.get("daXians") or [])
            ],
        }
        tl = sweep_payload(chart, SWEEP_FROM, SWEEP_TO)
        base["timeline"] = {
            "range": tl["range"],
            "rows": tl["rows"],
            "daxian_transitions": tl["daxian_transitions"],
            "transition_years": tl.get("transition_years") or [],
            "move_years": tl.get("move_years") or [],
            "hold_years": tl.get("hold_years") or [],
            "risk_years": tl.get("risk_years") or [],
            "summary": tl["summary"],
        }
        cur_year = int(birth.get("year") or 2000) + int(chart.get("currentAge") or 30) - 1
        c3 = chart_for_year(chart, cur_year)
        hg = build_hypergraph(c3)
        metrics = compute_metrics(hg)
        factors = compute_core_factors(hg, metrics)
        payload = {"hypergraph": hg, "metrics": metrics, "factors": factors}
        plain = explain_payload(payload)
        all_names = [row["name"] for row in twelve_palaces(chart)]
        facts = build_facts(chart, all_names, cards_title="全盘十二宫（详卡）")
        base["facts_text"] = render_facts_text(facts)
        base["current"] = {
            "year": cur_year,
            "one_liner": factors.get("one_liner"),
            "factors": factors.get("factors"),
            "plain": plain,
            "keystones": metrics.get("keystones") or [],
            "ji_fragility": metrics.get("ji_fragility") or [],
            "metrics": {
                "connectivity": metrics.get("connectivity"),
                "resilience": metrics.get("resilience"),
                "phase_proximity": metrics.get("phase_proximity"),
            },
            "meta": (hg.get("meta") or {}),
        }
        out_charts.append(base)
        if log:
            print("added:", cid, label)

    data = {
        "generated_by": "scripts/build_site.py",
        # 缺盘留痕：站点少了哪张盘、为什么，必须能从产物里看出来（也参与 drift 比对）
        "missing_charts": [
            {"id": s.id, "path": rel_path(s.path), "required": bool(s.required), "note": s.note}
            for s in [*missing_required, *missing_local]
        ],
        "sweep_range": [SWEEP_FROM, SWEEP_TO],
        "time_keywords": list(TIME_KEYWORDS),
        # 兜底提示文案的唯一来源（catalog.json 的 fallback_hint），前端只做渲染
        "matter_hint": dict(FALLBACK_HINT),
        "matters": [
            {
                "id": c["id"],
                "label": c["label"],
                "keywords": c["keywords"],
                "palaces": c["palaces"],
                "focus_factors": c["focus_factors"],
                "lens": c["lens"],
                "fallback": bool(c.get("fallback")),
            }
            for c in MATTER_CATALOG
        ],
        "charts": out_charts,
    }
    return _round_floats(data)


def serialize(data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return "window.ZIWEI_DATA = " + body + ";\n"


def write_payload(data: dict, path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(data), encoding="utf-8", newline="\n")
    return path


USAGE = """用法：
  python scripts/build_site.py                  # 缺必需 fixture -> 打红退出 1，且不写 charts.js
  python scripts/build_site.py --strict         # 本地私有盘（real-1990）也缺 -> 打红（全量站构建用）
  python scripts/build_site.py --allow-missing  # 显式放行缺盘（产物不完整，仅应急；会打印 WARN）
  python scripts/build_site.py --selftest       # 规则自测：缺必需盘必打红、缺本地盘必入 missing_charts
"""


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = list(sys.argv[1:] if argv is None else argv)
    strict_local = allow_missing = False
    for arg in args:
        if arg in ("--selftest", "selftest"):
            return _selftest()
        if arg in ("-h", "--help", "help"):
            print(USAGE)
            return 0
        if arg == "--strict":
            strict_local = True
        elif arg == "--allow-missing":
            allow_missing = True
        else:
            print("未知参数：{}".format(arg))
            print(USAGE)
            return 2

    missing_required, missing_local = collect_missing()
    if missing_required and not allow_missing:
        print("BUILD FAIL：缺少必需 fixture，拒绝写 {}".format(rel_path(OUT)))
        print(format_missing(missing_required))
        print("  " + MISSING_HINT)
        return 1
    if missing_local and strict_local:
        print("BUILD FAIL（--strict）：本地私有 fixture 缺失，站点会少盘")
        print(format_missing(missing_local))
        print("  {}；或去掉 --strict 只告警".format(MISSING_HINT))
        return 1

    data = build_payload(strict=not allow_missing)
    path = write_payload(data)
    print("wrote:", rel_path(path), path.stat().st_size, "bytes")
    if data.get("missing_charts"):
        print("note: 产物缺 {} 张盘，见 missing_charts".format(len(data["missing_charts"])))
    return 0


def _selftest() -> int:
    """负例自测：缺必需盘必须打红且点名；缺本地私有盘必须入 missing_charts；齐备时不得误报。

    规则哪天被改成「缺盘照样安静跳过」，这里先红。
    """
    ok_path = ROOT / "fixtures" / "sample-chart.json"
    ghost = ROOT / "fixtures" / "__selftest_missing__.json"
    specs = [
        ChartSpec("ok", "仓内盘", ok_path),
        ChartSpec("ghost-required", "必需但缺", ghost),
        ChartSpec("ghost-local", "本地私有且缺", ghost.with_name("__selftest_local__.json"),
                  required=False, note="selftest"),
    ]

    failures: list[str] = []
    total = 0

    def expect(name: str, got, want) -> None:
        nonlocal total
        total += 1
        if got != want:
            failures.append("{}：期望 {!r}，实际 {!r}".format(name, want, got))

    required, local = collect_missing(specs)
    expect("必需缺失归入 required", [s.id for s in required], ["ghost-required"])
    expect("可选缺失归入 local", [s.id for s in local], ["ghost-local"])
    expect("全部存在时无缺失", collect_missing(specs, exists=lambda p: True), ([], []))
    expect("全缺时按 required 分流",
           [len(x) for x in collect_missing(specs, exists=lambda p: False)], [2, 1])

    try:
        build_payload(specs, strict=True, log=False)
        got: object = "未抛错"
    except MissingFixtureError as exc:
        got = [s.id for s in exc.specs]
    expect("strict 缺必需盘 -> 抛 MissingFixtureError 且点名", got, ["ghost-required"])

    data = build_payload(specs, strict=False, log=False)
    expect("放行后缺盘计入 missing_charts",
           [(m["id"], m["required"]) for m in data["missing_charts"]],
           [("ghost-required", True), ("ghost-local", False)])
    expect("放行后 charts 只含齐备盘", [c["id"] for c in data["charts"]], ["ok"])
    expect("missing_charts 用仓内相对路径（无盘符/绝对路径）",
           all(not m["path"].startswith(("/", "\\")) and ":" not in m["path"]
               for m in data["missing_charts"]), True)

    if failures:
        print("SITE BUILD SELFTEST FAIL：{}/{} 条不符".format(len(failures), total))
        for item in failures:
            print("  - " + item)
        return 1
    print("SITE BUILD SELFTEST OK：{} 项（缺必需盘打红、缺本地盘入 missing_charts、齐备不误报）".format(total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
