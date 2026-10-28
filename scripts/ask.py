#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ask.py - 一句话问事，产出可粘贴给任意 AI 的提示包。

用法示例：
  python scripts/ask.py --birth 1990-01-01-0-male --matter "今年适合跳槽吗"
  python scripts/ask.py --chart path/to/chart.json --matter "这段感情能长久吗"
  python scripts/ask.py --demo --matter "今年身体要注意什么"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import explain_matter  # noqa: E402
from matter_query.facts import facts_for  # noqa: E402
from matter_query.prompt_pack import build_system_prompt, build_user_prompt  # noqa: E402

CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
ENGINE = Path(os.environ.get("ZIWEI_ENGINE_ROOT", r"F:\github\ziwei-doushu"))
GEN = ENGINE / "scripts" / "gen-one-for-ui.ts"


def _run_engine(y: int, m: int, d: int, h: int, gender: str, age: int | None) -> dict:
    tsx = ENGINE / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform.startswith("win") else "tsx")
    if tsx.exists():
        cmd = [str(tsx), str(GEN), str(y), str(m), str(d), str(h), gender]
    else:
        npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
        cmd = [npm, "exec", "--yes", "--", "tsx@4.19.4", str(GEN), str(y), str(m), str(d), str(h), gender]
    if age is not None:
        cmd.append(str(age))
    proc = subprocess.run(cmd, cwd=str(ENGINE), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", shell=False)
    if proc.returncode != 0:
        raise SystemExit("排盘引擎失败：\n" + (proc.stderr or proc.stdout)[-2000:])
    chart = json.loads(proc.stdout)
    if age is not None:
        chart["currentAge"] = int(age)
    return chart


def _convert(chart: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "chart.json"
        tmp.write_text(json.dumps(chart, ensure_ascii=False), encoding="utf-8")
        subprocess.check_call([sys.executable, str(CONV), str(tmp), "--no-prompt"],
                              cwd=str(ROOT), stdout=subprocess.DEVNULL)
        return json.loads((tmp.with_name("chart.hypergraph.json")).read_text(encoding="utf-8"))


def parse_birth(spec: str) -> tuple[int, int, int, int, str, int | None]:
    parts = spec.split("-")
    if len(parts) < 5:
        raise SystemExit("生辰格式应为 YYYY-MM-DD-H-gender[-age]，例：1990-01-01-0-male")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    h = int(parts[3])
    gender = parts[4]
    age = int(parts[5]) if len(parts) > 5 and parts[5] else None
    return y, m, d, h, gender, age


def _force_utf8_stdout() -> None:
    """Windows CI 控制台默认非 UTF-8，中文输出会抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def main() -> int:
    _force_utf8_stdout()
    ap = argparse.ArgumentParser(description="问事：生成可粘贴给任意 AI 的提示包")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--birth", help="生辰 YYYY-MM-DD-H-gender[-age]")
    src.add_argument("--chart", type=Path, help="已有 chart.json")
    src.add_argument("--demo", action="store_true", help="用演示盘")
    ap.add_argument("--matter", default="", help="想问的事")
    ap.add_argument("--as-of", type=int, default=None, help="流年")
    ap.add_argument("--sweep", default="", help="逐年区间，如 2020-2035；产出 F3/F4 曲线")
    ap.add_argument("--out", type=Path, default=None, help="写出提示包文件")
    ap.add_argument("--print-only", action="store_true", help="只打印，不写文件")
    args = ap.parse_args()

    if args.birth:
        y, m, d, h, gender, age = parse_birth(args.birth)
        chart = _run_engine(y, m, d, h, gender, age)
    elif args.chart:
        chart = json.loads(args.chart.read_text(encoding="utf-8"))
    else:
        chart = json.loads((ROOT / "fixtures" / "sample-chart.json").read_text(encoding="utf-8"))

    if args.as_of is not None:
        chart["asOfYear"] = int(args.as_of)

    payload = _convert(chart)
    payload["plain"] = explain_payload(payload)
    payload["matter"] = explain_matter(payload, (args.matter or "").strip() or None)
    payload["facts"] = facts_for(chart, payload["matter"].get("focus") or {})
    if args.sweep:
        from timeline.sweep import sweep_payload  # noqa: PLC0415

        try:
            frm, to = args.sweep.split("-", 1)
            payload["timeline"] = sweep_payload(chart, int(frm), int(to))
        except (ValueError, TypeError) as e:
            raise SystemExit(f"--sweep 格式应为 FROM-TO：{e}")
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(payload, args.matter, payload.get("timeline"))
    combined = f"# 可粘贴给任意 AI 的提示包\n\n## System\n\n{system_prompt}\n## User\n\n{user_prompt}"

    if args.print_only:
        print(combined)
        return 0

    out = args.out or (ROOT / "out" / "ask.prompt.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(combined, encoding="utf-8")
    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"提示包：{out}")
    print(f"结构盘：{json_out}")
    print(f"事项：{payload['matter']['focus']['label']}")
    if payload.get("timeline"):
        rng = payload["timeline"].get("range") or []
        print(f"逐年推演：{rng[0]}-{rng[1] if len(rng) > 1 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())