#!/usr/bin/env python3
"""
api.py — REST API для Nautilus Portal.

Эндпоинты:
  GET  /api/query?q=<query>[&ranked=1]  — поиск концептов
  GET  /api/health                       — состояние экосистемы
  GET  /api/links                        — валидация ссылок
  GET  /api/describe                     — описание адаптеров

Использование:
  python api.py              # порт 8080
  python api.py --port 9000  # другой порт

Или как WSGI-приложение:
  from api import make_app
  app = make_app()
"""

import json
import argparse
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from portal import NautilusPortal


def make_app() -> NautilusPortal:
    return NautilusPortal()


def _json_response(handler, data: dict, status: int = 200):
    body = json.dumps(data, ensure_ascii=False, indent=2).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def handle_query(portal: NautilusPortal, params: dict) -> dict:
    query = params.get("q", ["knowledge"])[0]
    ranked = params.get("ranked", ["1"])[0] != "0"
    t0 = time.monotonic()
    result = portal.query(query, ranked=ranked)
    elapsed_ms = round((time.monotonic() - t0) * 1000)
    return {
        "query": result.query,
        "elapsed_ms": elapsed_ms,
        "total": len(result.entries),
        "consensus": result.consensus,
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "source": e.source,
                "format_type": e.format_type,
                "content": e.content[:300],
                "metadata": e.metadata,
                "links": e.links,
                "is_fallback": e.is_fallback,
            }
            for e in result.entries
        ],
        "cross_links": result.cross_links[:20],
    }


def handle_health(portal: NautilusPortal) -> dict:
    from health_check import check_adapters, check_passports, check_consensus, score
    adapter_r = check_adapters(portal)
    passport_r = check_passports()
    consensus_r = check_consensus(portal)
    sc, issues = score(adapter_r, passport_r, consensus_r)
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "score": sc,
        "ok": sc >= 70 and not any("❌" in i for i in issues),
        "issues": issues,
        "adapters": adapter_r,
        "passports": passport_r,
        "consensus": consensus_r,
    }


def handle_links(portal: NautilusPortal) -> dict:
    from validate_links import validate
    return validate(portal)


def handle_describe(portal: NautilusPortal) -> dict:
    return portal.describe()


def _make_handler(portal: NautilusPortal):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            path = parsed.path.rstrip("/")

            try:
                if path == "/api/query":
                    _json_response(self, handle_query(portal, params))
                elif path == "/api/health":
                    _json_response(self, handle_health(portal))
                elif path == "/api/links":
                    _json_response(self, handle_links(portal))
                elif path == "/api/describe":
                    _json_response(self, handle_describe(portal))
                elif path in ("/", ""):
                    _json_response(self, {
                        "service": "Nautilus Portal API",
                        "endpoints": [
                            "/api/query?q=<query>&ranked=1",
                            "/api/health",
                            "/api/links",
                            "/api/describe",
                        ],
                    })
                else:
                    _json_response(self, {"error": f"Unknown endpoint: {path}"}, 404)
            except Exception as ex:
                _json_response(self, {"error": str(ex)}, 500)

        def log_message(self, fmt, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Nautilus Portal REST API")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="")
    args = parser.parse_args()

    portal = make_app()
    Handler = _make_handler(portal)
    server = HTTPServer((args.host, args.port), Handler)
    print(f"⬡ Nautilus API → http://localhost:{args.port}/api/query?q=knowledge")
    server.serve_forever()


if __name__ == "__main__":
    main()
