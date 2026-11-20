#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""速查表防漂移：docs/matter-lexicon.md 必须与生成器输出逐字一致。

真源是 packages/matter_query/catalog.json → scripts/gen-matter-lexicon.py。
任何人手改速查表（改词、补一节、调格式）这里立刻打红，并点名首个差异行号。

用法：
  python scripts/check-matter-lexicon.py             # 一致 → OK / 退出 0；不一致 → 退出 1
  python scripts/check-matter-lexicon.py --selftest  # 规则自测：漂移必须打红且点名行号，换行差异放行
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "gen-matter-lexicon.py"
OUT = ROOT / "docs" / "matter-lexicon.md"

BOM = b"\xef\xbb\xbf"
DIFF_EOF = "<文件到此结束>"


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


class Verdict(NamedTuple):
    """一次比对的判定结果（纯数据，便于自测）。"""

    ok: bool                      # 归一换行后逐字一致
    bom: bool                     # 磁盘文件带 UTF-8 BOM
    eol_only: bool                # 仅换行符不同（CRLF 检出），内容其实一致
    first_diff: tuple[int, str, str] | None   # (1 基行号, 期望行, 实际行)


def _first_diff(expected: str, actual: str) -> tuple[int, str, str] | None:
    """首个差异行；行数不同时缺的一侧用 DIFF_EOF 占位，便于一眼看出「多写/少写」。"""
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    for i in range(max(len(exp_lines), len(act_lines))):
        e = exp_lines[i] if i < len(exp_lines) else DIFF_EOF
        a = act_lines[i] if i < len(act_lines) else DIFF_EOF
        if e != a:
            return (i + 1, e, a)
    return None


def _verdict(expected_text: str, actual_bytes: bytes) -> Verdict:
    """比对生成器输出与磁盘字节。纯函数：自测直接喂字符串，不碰磁盘。"""
    expected_bytes = expected_text.encode("utf-8")
    ok = expected_bytes == _normalize_newlines(actual_bytes)
    return Verdict(
        ok=ok,
        bom=actual_bytes.startswith(BOM),
        eol_only=ok and actual_bytes != expected_bytes,
        first_diff=None if ok else _first_diff(
            expected_text, actual_bytes.decode("utf-8-sig", errors="replace")
        ),
    )


def _selftest() -> int:
    """负例自测：漂移真的会打红？行号真的对？CRLF 真的只当归一、不当漂移？

    只测纯函数 _verdict / _first_diff / _normalize_newlines，不落盘、不依赖 catalog。
    规则被改成「永远 OK」时这里先红，比等真文件被手改更早。
    """
    base = "# 速查表\n\n- a\n- b\n"          # 4 行
    cases: list[tuple[str, str, bytes, bool, bool, tuple[int, str, str] | None]] = [
        # (名称, 期望文本, 磁盘字节, 期望 ok, 期望 bom, 期望 first_diff)
        ("逐字一致 -> 放行", base, base.encode("utf-8"), True, False, None),
        ("CRLF 检出 -> 放行且标 eol", base, base.replace("\n", "\r\n").encode("utf-8"), True, False, None),
        ("孤立 CR -> 放行且标 eol", base, base.replace("\n", "\r").encode("utf-8"), True, False, None),
        ("改一个词 -> 打红并点名行", base, "# 速查表\n\n- A\n- b\n".encode("utf-8"),
         False, False, (3, "- a", "- A")),
        ("手改多一行 -> 打红并点末尾", base, (base + "- c\n").encode("utf-8"),
         False, False, (5, DIFF_EOF, "- c")),
        ("少一行 -> 打红并点缺行", base, "# 速查表\n\n- a\n".encode("utf-8"),
         False, False, (4, "- b", DIFF_EOF)),
        ("带 BOM -> 打红且标 BOM", base, BOM + base.encode("utf-8"), False, True, None),
        ("末尾多空行 -> 打红", "# 速查表\n", "# 速查表\n\n".encode("utf-8"),
         False, False, (2, DIFF_EOF, "")),
        ("行内多空格 -> 打红", base, "#  速查表\n\n- a\n- b\n".encode("utf-8"),
         False, False, (1, "# 速查表", "#  速查表")),
    ]

    failures: list[str] = []
    total = 0

    def expect(name: str, got, want) -> None:
        nonlocal total
        total += 1
        if got != want:
            failures.append("{}：期望 {!r}，实际 {!r}".format(name, want, got))

    for name, exp_text, act_bytes, want_ok, want_bom, want_diff in cases:
        v = _verdict(exp_text, act_bytes)
        expect(name + "（ok）", v.ok, want_ok)
        expect(name + "（bom）", v.bom, want_bom)
        expect(name + "（行号/内容）", v.first_diff, want_diff)
        if want_ok:
            expect(name + "（eol 标记）", v.eol_only, act_bytes != exp_text.encode("utf-8"))
        else:
            expect(name + "（失败时不得标 eol）", v.eol_only, False)

    if failures:
        print("MATTER LEXICON SELFTEST FAIL：{}/{} 条不符".format(len(failures), total))
        for item in failures:
            print("  - {}".format(item))
        return 1
    print("MATTER LEXICON SELFTEST OK：{} 项（改词/多行/少行/末尾空行/空白/BOM 打红并点名，CRLF 仅归一）".format(total))
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        if args[0] in ("--selftest", "selftest"):
            return _selftest()
        print("未知参数：{}（用法：python scripts/check-matter-lexicon.py [--selftest]）".format(" ".join(args)))
        return 2

    if not GEN.exists():
        print("缺少生成器：{}".format(GEN))
        return 1
    if not OUT.exists():
        print("缺少速查表：{}（先跑 python scripts/gen-matter-lexicon.py）".format(OUT))
        return 1

    expected = _load_generator().render()
    verdict = _verdict(expected, OUT.read_bytes())
    if verdict.ok:
        eol_note = "；已忽略 CRLF/LF 差异" if verdict.eol_only else ""
        print("MATTER LEXICON OK：docs/matter-lexicon.md 与 catalog 生成结果逐字一致（{} 行 / {} 字节）{}".format(
            expected.count("\n"), len(expected.encode("utf-8")), eol_note
        ))
        return 0

    print("MATTER LEXICON FAIL：docs/matter-lexicon.md 与生成结果不一致")
    if verdict.bom:
        print("  注意：磁盘文件带 UTF-8 BOM，生成器输出不带 BOM")
    if verdict.first_diff is not None:
        lineno, exp_line, act_line = verdict.first_diff
        print("  首个差异：第 {} 行".format(lineno))
        print("    期望: {!r}".format(exp_line))
        print("    实际: {!r}".format(act_line))
    else:
        print("  各行一致，差异只在行尾换行或末尾空白（生成器固定 LF、无 BOM）")
    print("  修法：改 catalog.json 后跑 python scripts/gen-matter-lexicon.py（不要手改 md）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
