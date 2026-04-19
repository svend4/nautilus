#!/usr/bin/env python3
"""
api.py — REST API для Nautilus Portal.

Эндпоинты:
  GET  /api/query?q=<query>[&ranked=1]         — поиск концептов
  GET  /api/health                              — состояние экосистемы
  GET  /api/links                               — валидация ссылок
  GET  /api/describe                            — описание адаптеров
  GET  /api/neighbors?q6=<bits>&dist=<n>        — Q6-соседи
  GET  /api/bridge?id=<entry_id>&hops=<n>       — обход графа bridges
  GET  /api/bridge_conflicts                    — Protocol 3: конфликты
  GET  /api/bridge_summary                      — сводка bridges + closure
  GET  /api/annotations?target=<id>[&vis=...][&author=...] — аннотации к записи
  POST /api/annotations                         — добавить аннотацию (JSON body)
  GET  /api/flags[?severity=warning]            — Protocol 3: флаги для ревью

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
import html as _html

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


def handle_bridge(portal: NautilusPortal, params: dict) -> dict:
    """GET /api/bridge?id=<entry_id>&hops=<n> — traverse bridge graph."""
    entry_id = params.get("id", ["pro2:bidir"])[0]
    hops = max(1, min(int(params.get("hops", ["1"])[0]), 3))
    t0 = time.monotonic()
    result = portal.query_by_bridge(entry_id, hops)
    elapsed_ms = round((time.monotonic() - t0) * 1000)
    return {
        "entry_id": entry_id,
        "max_hops": hops,
        "elapsed_ms": elapsed_ms,
        "total": len(result.entries),
        "repos_reached": sorted({e.id.split(":")[0] for e in result.entries}),
        "cross_links": result.cross_links[:20],
        "entries": [
            {"id": e.id, "title": e.title,
             "q6": e.metadata.get("q6", ""),
             "repo": e.id.split(":")[0],
             "is_fallback": e.is_fallback}
            for e in result.entries[:30]
        ],
    }


def handle_bridge_conflicts(portal: NautilusPortal) -> dict:
    """GET /api/bridge_conflicts — Protocol 3 conflict detection."""
    t0 = time.monotonic()
    conflicts = portal.bridge_conflicts()
    elapsed_ms = round((time.monotonic() - t0) * 1000)
    return {
        "elapsed_ms": elapsed_ms,
        "total_conflicts": len(conflicts),
        "conflicts": conflicts,
    }


def handle_bridge_summary(portal: NautilusPortal) -> dict:
    """GET /api/bridge_summary — full bridge registry overview."""
    return portal.bridge_summary()


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


def handle_annotations_get(portal: NautilusPortal, params: dict) -> dict:
    """GET /api/annotations?target=<id>[&vis=...][&author=...]"""
    target = params.get("target", [""])[0]
    if not target:
        return {"error": "target parameter required"}, 400
    vis = params.get("vis", [None])[0]
    author = params.get("author", [None])[0]
    anns = portal.annotations_for(target, visibility=vis, author=author)
    return {"target": target, "total": len(anns), "annotations": anns}


def handle_annotations_post(portal: NautilusPortal, body: bytes) -> dict:
    """POST /api/annotations — add annotation from JSON body."""
    try:
        data = json.loads(body.decode())
    except Exception:
        return {"error": "invalid JSON"}, 400
    target = data.get("target", "").strip()
    author = data.get("author", "").strip()
    content = data.get("content", "").strip()
    if not target or not author or not content:
        return {"error": "target, author, content are required"}, 400
    ann_id = portal.annotate(
        target=target,
        author=_html.escape(author),
        content=_html.escape(content),
        visibility=data.get("visibility", "private"),
        tags=data.get("tags", []),
        thread_parent=data.get("thread_parent"),
    )
    return {"id": ann_id, "target": target}


def handle_flags(portal: NautilusPortal, params: dict) -> dict:
    """GET /api/flags[?severity=warning] — Protocol 3 flags."""
    severity = params.get("severity", [None])[0]
    flags = portal.get_flags(severity)
    return {
        "total": len(flags),
        "severity_filter": severity,
        "flags": flags,
    }


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
                elif path == "/api/bridge":
                    _json_response(self, handle_bridge(portal, params))
                elif path == "/api/bridge_conflicts":
                    _json_response(self, handle_bridge_conflicts(portal))
                elif path == "/api/bridge_summary":
                    _json_response(self, handle_bridge_summary(portal))
                elif path == "/api/annotations":
                    result = handle_annotations_get(portal, params)
                    if isinstance(result, tuple):
                        _json_response(self, result[0], result[1])
                    else:
                        _json_response(self, result)
                elif path == "/api/flags":
                    _json_response(self, handle_flags(portal, params))
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
                            "/api/bridge?id=pro2:bidir&hops=2",
                            "/api/bridge_conflicts",
                            "/api/bridge_summary",
                            "/api/annotations?target=<id>",
                            "/api/flags",
                            "/metrics",
                        ],
                    })
                else:
                    _json_response(self, {"error": f"Unknown endpoint: {path}"}, 404)
            except Exception as ex:
                _json_response(self, {"error": str(ex)}, 500)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                if path == "/api/annotations":
                    result = handle_annotations_post(portal, body)
                    if isinstance(result, tuple):
                        _json_response(self, result[0], result[1])
                    else:
                        _json_response(self, result, 201)
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
