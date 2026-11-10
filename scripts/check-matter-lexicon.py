#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""速查表防漂移：docs/matter-lexicon.md 必须与生成器输出逐字一致。

真源是 packages/matter_query/catalog.json → scripts/gen-matter-lexicon.py。
任何人手改速查表（改词、补一节、调格式）这里立刻打红，并点名首个差异行号。

用法：
  python scripts/check-matter-lexicon.py   # 一致 → OK / 退出 0；不一致 → 退出 1
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "gen-matter-lexicon.py"
OUT = ROOT / "docs" / "matter-lexicon.md"


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_matter_lexicon", GEN)
    if spec is None or spec.loader is None:
        raise SystemExit("无法加载生成器：{}".format(GEN))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _normalize_newlines(data: bytes) -> bytes:
    """把 CRLF / 孤立 CR 归一为 LF。

    Windows 上的 git checkout 默认把仓库里的 LF 转成 CRLF（core.autocrlf），
    这是工作区行为而非内容漂移；CI 的 windows-latest 也这样检出。
    生成器固定输出 LF，所以比对前只归一换行符，其余字节仍逐字比。
    """
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main() -> int:
    _force_utf8_stdout()
    if not GEN.exists():
        print("缺少生成器：{}".format(GEN))
        return 1
    if not OUT.exists():
        print("缺少速查表：{}（先跑 python scripts/gen-matter-lexicon.py）".format(OUT))
        return 1

    expected = _load_generator().render()
    expected_bytes = expected.encode("utf-8")
    actual_bytes = OUT.read_bytes()
    actual_normalized = _normalize_newlines(actual_bytes)
    if expected_bytes == actual_normalized:
        eol_note = "；已忽略 CRLF/LF 差异" if actual_bytes != expected_bytes else ""
        print("MATTER LEXICON OK：docs/matter-lexicon.md 与 catalog 生成结果逐字一致（{} 行 / {} 字节）{}".format(
            expected.count("\n"), len(expected_bytes), eol_note
        ))
        return 0

    print("MATTER LEXICON FAIL：docs/matter-lexicon.md 与生成结果不一致")
    if actual_bytes.startswith(b"\xef\xbb\xbf"):
        print("  注意：磁盘文件带 UTF-8 BOM，生成器输出不带 BOM")
    actual = actual_bytes.decode("utf-8-sig", errors="replace")
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    for i in range(max(len(exp_lines), len(act_lines))):
        e = exp_lines[i] if i < len(exp_lines) else "<文件到此结束>"
        a = act_lines[i] if i < len(act_lines) else "<文件到此结束>"
        if e != a:
            print("  首个差异：第 {} 行".format(i + 1))
            print("    期望: {!r}".format(e))
            print("    实际: {!r}".format(a))
            break
    else:
        print("  各行一致，差异只在行尾换行或末尾空白（生成器固定 LF、无 BOM）")
    print("  修法：改 catalog.json 后跑 python scripts/gen-matter-lexicon.py（不要手改 md）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
