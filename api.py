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
from typing import Any

from portal import NautilusPortal

# Simple cache so /metrics doesn't hammer health_check on every Prometheus scrape
_metrics_cache: dict[str, Any] = {}
_METRICS_TTL = 30  # seconds


def make_app() -> NautilusPortal:
    return NautilusPortal()


def _json_response(handler: Any, data: dict, status: int = 200) -> None:
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


def handle_neighbors(portal: NautilusPortal, params: dict) -> dict:
    bits = params.get("q6", ["000000"])[0]
    dist = int(params.get("dist", ["1"])[0])
    dist = max(1, min(dist, 3))
    from portal import q6_neighbors
    neighbors = q6_neighbors(bits, dist)
    t0 = time.monotonic()
    result = portal.query_neighbors(bits, dist)
    elapsed_ms = round((time.monotonic() - t0) * 1000)
    return {
        "q6": bits,
        "max_distance": dist,
        "neighbors": neighbors,
        "elapsed_ms": elapsed_ms,
        "total": len(result.entries),
        "entries": [
            {"id": e.id, "title": e.title, "q6": e.metadata.get("q6", ""),
             "distance": sum(a != b for a, b in zip(e.metadata.get("q6", bits), bits)),
             "is_fallback": e.is_fallback}
            for e in result.entries
        ],
    }


def handle_metrics(portal: NautilusPortal) -> str:
    """Return Prometheus text exposition format metrics."""
    now = time.time()
    if now - _metrics_cache.get("_ts", 0) > _METRICS_TTL:
        _metrics_cache.clear()
        _metrics_cache["_ts"] = now

        # Health score
        try:
            from health_check import check_adapters, check_passports, check_consensus, score
            sc, _ = score(check_adapters(portal), check_passports(), check_consensus(portal))
            _metrics_cache["health_score"] = sc
        except Exception:
            _metrics_cache["health_score"] = -1

        # Adapter entry counts: parse any total_* numeric from describe()
        try:
            desc = portal.describe()
            counts: dict[str, int] = {}
            for name, info in desc.items():
                val = 0
                for k, v in info.items() if isinstance(info, dict) else []:
                    if "total" in k.lower():
                        try:
                            val = int(str(v).rstrip("+").split(".")[0])
                            break
                        except (ValueError, TypeError):
                            pass
                counts[name] = val
            _metrics_cache["adapters"] = counts
        except Exception:
            _metrics_cache["adapters"] = {}

        # Cache ages
        try:
            from adapters.cache import CacheManager
            cm = CacheManager()
            _metrics_cache["cache"] = {
                item["repo"]: item["age_hours"]
                for item in cm.list_cached()
            }
        except Exception:
            _metrics_cache["cache"] = {}

    lines = [
        "# HELP nautilus_health_score Overall ecosystem health score (0-100)",
        "# TYPE nautilus_health_score gauge",
        f"nautilus_health_score {_metrics_cache.get('health_score', -1)}",
        "",
        "# HELP nautilus_adapters_count Number of registered adapters",
        "# TYPE nautilus_adapters_count gauge",
        f"nautilus_adapters_count {len(portal.adapters)}",
        "",
        "# HELP nautilus_adapter_entries Number of entries per adapter",
        "# TYPE nautilus_adapter_entries gauge",
    ]
    for name, count in _metrics_cache.get("adapters", {}).items():
        lines.append(f'nautilus_adapter_entries{{adapter="{name}"}} {count}')

    lines += [
        "",
        "# HELP nautilus_cache_age_hours Cache age in hours per repo",
        "# TYPE nautilus_cache_age_hours gauge",
    ]
    for repo, age_h in _metrics_cache.get("cache", {}).items():
        safe_repo = repo.replace("/", "_").replace("-", "_")
        lines.append(f'nautilus_cache_age_hours{{repo="{safe_repo}"}} {age_h:.2f}')

    lines.append("")
    return "\n".join(lines)


def handle_describe(portal: NautilusPortal) -> dict:
    return portal.describe()


def _text_response(handler: Any, body: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
    encoded = body.encode()
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _make_handler(portal: NautilusPortal) -> type:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
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
                elif path == "/api/neighbors":
                    _json_response(self, handle_neighbors(portal, params))
                elif path == "/metrics":
                    _text_response(self, handle_metrics(portal),
                                   content_type="text/plain; version=0.0.4; charset=utf-8")
                elif path in ("/", ""):
                    _json_response(self, {
                        "service": "Nautilus Portal API",
                        "endpoints": [
                            "/api/query?q=<query>&ranked=1",
                            "/api/health",
                            "/api/links",
                            "/api/describe",
                            "/api/neighbors?q6=110001&dist=1",
                            "/metrics",
                        ],
                    })
                else:
                    _json_response(self, {"error": f"Unknown endpoint: {path}"}, 404)
            except Exception as ex:
                _json_response(self, {"error": str(ex)}, 500)

        def log_message(self, fmt: str, *args: object) -> None:
            pass

    return Handler


def main() -> None:
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
