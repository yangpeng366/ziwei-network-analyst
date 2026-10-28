#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验静态站数据与代码生成结果一致（按 JSON 语义比较，忽略换行差异）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import OUT, build_payload  # noqa: E402


def parse_committed() -> dict:
    raw = OUT.read_text(encoding="utf-8")
    prefix = "window.ZIWEI_DATA = "
    if not raw.startswith(prefix):
        raise SystemExit("charts.js 格式不对：缺少 window.ZIWEI_DATA = 前缀")
    body = raw[len(prefix):].strip()
    if body.endswith(";"):
        body = body[:-1]
    return json.loads(body)


def main() -> int:
    if not OUT.exists():
        print("缺少", OUT)
        return 1
    committed = parse_committed()
    fresh = build_payload()
    if committed == fresh:
        print("SITE DATA OK")
        return 0
    # 指出第一处差异，便于定位
    if set(committed.get("charts", [])) != {c["id"] for c in fresh["charts"]}:
        print("差异：图表集合不一致")
    else:
        for a, b in zip(committed.get("charts", []), fresh["charts"]):
            if a != b:
                for k in a:
                    if a.get(k) != b.get(k):
                        print(f"差异：chart {a.get('id')} 的 {k}")
                        break
                break
    return 1


if __name__ == "__main__":
    raise SystemExit(main())