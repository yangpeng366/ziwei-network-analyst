#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fixture 转换可复现回归。

本仓把「排盘 → 超图 → 四因子」当确定性层，LLM 只做翻译。所以同一张盘转两次
必须一模一样，且与仓库里的基准件一致。本检查锁两件事：

1. 连转两次字节级一致 —— 证明没有时间戳/随机序/浮点噪声混进产物
2. 与仓库基准件 *.hypergraph.json 一致 —— 算法或上游一改就立刻红

对应本周衡量指标：fixture 转换稳定可复现。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"

CASES = [
    ("sample", ROOT / "fixtures" / "sample-chart.json"),
    ("high", ROOT / "fixtures" / "calibration" / "community-high.json"),
    ("low", ROOT / "fixtures" / "calibration" / "community-low.json"),
]


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _convert(chart: Path, out: Path) -> bytes:
    proc = subprocess.run(
        [sys.executable, str(CONV), str(chart), "-o", str(out), "--no-prompt"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(
            "转换失败：{}\n{}\n{}".format(chart, (proc.stdout or "")[-1500:], (proc.stderr or "")[-1500:])
        )
    return out.read_bytes()


def main() -> int:
    _force_utf8_stdout()
    errs: list[str] = []
    for name, chart in CASES:
        baseline = chart.with_name(chart.stem + ".hypergraph.json")
        if not chart.exists():
            errs.append("缺 fixture：{}".format(chart))
            continue
        if not baseline.exists():
            errs.append("缺基准件：{}".format(baseline))
            continue
        with tempfile.TemporaryDirectory() as td:
            a = _convert(chart, Path(td) / "run1.json")
            b = _convert(chart, Path(td) / "run2.json")
        base_bytes = baseline.read_bytes()
        if a != b:
            errs.append("{}：两次转换结果不一致（{} vs {} 字节）".format(name, len(a), len(b)))
        if a != base_bytes:
            errs.append(
                "{}：与基准件不一致（本次 {} 字节 / 基准 {} 字节）——算法或上游已改，需复核后更新基准件".format(
                    name, len(a), len(base_bytes)
                )
            )
        else:
            print("{}：两次转换一致，且与基准件一致（{} 字节）".format(name, len(a)))
    if errs:
        print("FIXTURE REPRO FAIL（{} 项）".format(len(errs)))
        for e in errs:
            print(" - {}".format(e))
        return 1
    print("FIXTURE REPRO PASS：{} 张 fixture 转换稳定可复现".format(len(CASES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
