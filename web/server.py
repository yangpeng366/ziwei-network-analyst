#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local demo UI for ziwei-network-analyst four factors."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "packages"))
from plain_reading.explain import explain_payload  # noqa: E402
from matter_query.map import explain_matter  # noqa: E402
from matter_query.prompt_pack import build_system_prompt, build_user_prompt  # noqa: E402

CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
ENGINE = Path(os.environ.get("ZIWEI_ENGINE_ROOT", r"F:\github\ziwei-doushu"))
GEN = ENGINE / "scripts" / "gen-one-for-ui.ts"
FIXTURES = ROOT / "fixtures"
HOST = "127.0.0.1"
PORT = int(os.environ.get("ZIWEI_DEMO_PORT", "8765"))


def list_fixtures() -> list[dict]:
    items = []
    sample = FIXTURES / "sample-chart.json"
    if sample.exists():
        items.append({"id": "sample-chart", "label": "演示盘 sample-chart", "path": str(sample)})
    for p in sorted((FIXTURES / "calibration").glob("community-*.json")):
        items.append({"id": p.stem, "label": f"校准 {p.stem}", "path": str(p)})
    real = FIXTURES / "real-1990"
    if real.exists():
        for p in sorted(real.glob("1990-*.json"))[:36]:
            if "hypergraph" in p.name:
                continue
            items.append({"id": p.stem, "label": p.stem, "path": str(p)})
    return items


def enrich(payload: dict, matter: str | None = None) -> dict:
    payload["plain"] = explain_payload(payload)
    payload["matter"] = explain_matter(payload, matter)
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(payload, matter)
    payload["prompt_pack"] = {
        "system": system_prompt,
        "user": user_prompt,
        "mode": "paste-to-any-ai",
        "combined_markdown": (
            "# 可粘贴给任意 AI 的提示包\n\n"
            "## System\n\n"
            f"{system_prompt}\n"
            "## User\n\n"
            f"{user_prompt}"
        ),
    }
    return payload


def analyze_chart_file(chart_path: Path, as_of_year: int | None = None, matter: str | None = None) -> dict:
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    if as_of_year is not None:
        chart["asOfYear"] = int(as_of_year)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "chart.json"
        tmp.write_text(json.dumps(chart, ensure_ascii=False), encoding="utf-8")
        subprocess.check_call([sys.executable, str(CONV), str(tmp), "--no-prompt"], cwd=str(ROOT), stdout=subprocess.DEVNULL)
        payload = json.loads((tmp.with_name("chart.hypergraph.json")).read_text(encoding="utf-8"))
    payload["source"] = {"kind": "fixture", "path": str(chart_path)}
    return enrich(payload, matter)


def analyze_birth(y: int, m: int, d: int, h: int, gender: str, age: int | None, as_of_year: int | None, matter: str | None = None) -> dict:
    tsx_cmd = ENGINE / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform.startswith("win") else "tsx")
    if tsx_cmd.exists():
        cmd = [str(tsx_cmd), str(GEN), str(y), str(m), str(d), str(h), gender]
    else:
        npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
        cmd = [npm, "exec", "--yes", "--", "tsx@4.19.4", str(GEN), str(y), str(m), str(d), str(h), gender]
    if age is not None:
        cmd.append(str(age))
    proc = subprocess.run(
        cmd,
        cwd=str(ENGINE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "generateChart failed")[-2000:])
    chart = json.loads(proc.stdout)
    if age is not None:
        chart["currentAge"] = int(age)
    if as_of_year is not None:
        chart["asOfYear"] = int(as_of_year)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "chart.json"
        tmp.write_text(json.dumps(chart, ensure_ascii=False), encoding="utf-8")
        subprocess.check_call([sys.executable, str(CONV), str(tmp), "--no-prompt"], cwd=str(ROOT), stdout=subprocess.DEVNULL)
        payload = json.loads((tmp.with_name("chart.hypergraph.json")).read_text(encoding="utf-8"))
    payload["source"] = {
        "kind": "birth",
        "year": y,
        "month": m,
        "day": d,
        "hour": h,
        "gender": gender,
        "age": age,
        "asOfYear": as_of_year,
    }
    return enrich(payload, matter)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict | list) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            html = (WEB / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if u.path == "/api/health":
            self._json(
                200,
                {
                    "ok": True,
                    "engine": ENGINE.exists(),
                    "conv": CONV.exists(),
                    "engine_root": str(ENGINE),
                },
            )
            return
        if u.path == "/api/fixtures":
            self._json(200, {"items": list_fixtures()})
            return
        if u.path == "/api/analyze":
            qs = parse_qs(u.query)
            fid = (qs.get("id") or [None])[0]
            as_of = (qs.get("asOfYear") or [None])[0]
            matter = (qs.get("matter") or [""])[0].strip() or None
            as_of_i = int(as_of) if as_of not in (None, "") else None
            items = {x["id"]: x for x in list_fixtures()}
            if not fid or fid not in items:
                self._json(400, {"error": "unknown fixture id"})
                return
            try:
                payload = analyze_chart_file(Path(items[fid]["path"]), as_of_i, matter)
                self._json(200, payload)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path != "/api/analyze-birth":
            self._json(404, {"error": "not found"})
            return
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
            y = int(body["year"])
            m = int(body["month"])
            d = int(body["day"])
            h = int(body["hour"])
            gender = str(body.get("gender") or "male")
            age = body.get("age")
            age_i = int(age) if age not in (None, "") else None
            as_of = body.get("asOfYear")
            as_of_i = int(as_of) if as_of not in (None, "") else None
            matter = str(body.get("matter") or "").strip() or None
            payload = analyze_birth(y, m, d, h, gender, age_i, as_of_i, matter)
            self._json(200, payload)
        except Exception as e:
            self._json(500, {"error": str(e)})


def _force_utf8_stdout() -> None:
    """Windows CI 控制台默认非 UTF-8，中文输出会抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def main() -> int:
    _force_utf8_stdout()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ziwei-network-analyst demo: http://{HOST}:{PORT}/")
    print("Ctrl+C to stop")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())