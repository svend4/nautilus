"""
nautilus_sdk.py — тонкий клиент для Nautilus Portal API.

Поддерживает два режима:
  1. Прямой (local): импортирует portal.py напрямую — для использования внутри монорепо.
  2. HTTP (remote): обращается к REST API через nautilus_sdk.NautilusClient(url=...).

Использование (local):
    from nautilus_sdk import NautilusSDK
    sdk = NautilusSDK()
    result = sdk.query("синтез")
    for entry in result.entries:
        print(entry.title, entry.metadata.get("q6"))

Использование (remote):
    from nautilus_sdk import NautilusClient
    client = NautilusClient("http://localhost:8080")
    result = client.query("котёл")
    print(result["consensus"]["coverage"])
"""

from __future__ import annotations
import json
import urllib.request
from typing import Optional
from dataclasses import dataclass


# ── Local SDK ────────────────────────────────────────────────────────────────

class NautilusSDK:
    """Direct Python interface — no HTTP, no serialization overhead."""

    def __init__(self):
        from portal import NautilusPortal
        self._portal = NautilusPortal()

    def query(self, concept: str, ranked: bool = True):
        return self._portal.query(concept, ranked=ranked)

    def describe(self) -> dict:
        return self._portal.describe()

    def register(self, name: str, adapter) -> None:
        self._portal.register(name, adapter)

    def adapters(self) -> list[str]:
        return list(self._portal.adapters.keys())

    def health(self) -> dict:
        from health_check import check_adapters, check_passports, check_consensus, score
        ar = check_adapters(self._portal)
        pr = check_passports()
        cr = check_consensus(self._portal)
        sc, issues = score(ar, pr, cr)
        return {"score": sc, "issues": issues, "ok": sc >= 70}

    def links_valid(self) -> dict:
        from validate_links import validate
        return validate(self._portal)


# ── HTTP Client ───────────────────────────────────────────────────────────────

@dataclass
class RemoteEntry:
    id: str
    title: str
    source: str
    format_type: str
    content: str
    metadata: dict
    links: list
    is_fallback: bool


@dataclass
class RemoteResult:
    query: str
    entries: list[RemoteEntry]
    cross_links: list
    consensus: Optional[dict]
    elapsed_ms: int
    total: int


class NautilusClient:
    """HTTP client for Nautilus REST API (api.py)."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "nautilus-sdk/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def query(self, concept: str, ranked: bool = True) -> RemoteResult:
        data = self._get("/api/query", {"q": concept, "ranked": "1" if ranked else "0"})
        entries = [
            RemoteEntry(
                id=e["id"], title=e["title"], source=e["source"],
                format_type=e["format_type"], content=e["content"],
                metadata=e["metadata"], links=e["links"],
                is_fallback=e["is_fallback"],
            )
            for e in data.get("entries", [])
        ]
        return RemoteResult(
            query=data["query"],
            entries=entries,
            cross_links=data.get("cross_links", []),
            consensus=data.get("consensus"),
            elapsed_ms=data.get("elapsed_ms", 0),
            total=data.get("total", len(entries)),
        )

    def health(self) -> dict:
        return self._get("/api/health")

    def links(self) -> dict:
        return self._get("/api/links")

    def describe(self) -> dict:
        return self._get("/api/describe")

    def ping(self) -> bool:
        try:
            self._get("/")
            return True
        except Exception:
            return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Nautilus SDK CLI")
    parser.add_argument("query", nargs="?", default="knowledge")
    parser.add_argument("--url", help="Remote API URL (local mode if not set)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--health", action="store_true")
    args = parser.parse_args()

    if args.url:
        client = NautilusClient(args.url)
        if args.health:
            data = client.health()
        else:
            data = client.query(args.query).__dict__
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        else:
            print(f"Score: {data.get('score', '?')}" if args.health
                  else f"Query '{args.query}': {data.get('total', '?')} entries")
    else:
        sdk = NautilusSDK()
        if args.health:
            h = sdk.health()
            if args.json:
                print(json.dumps(h, ensure_ascii=False, indent=2))
            else:
                print(f"Health score: {h['score']}/100  {'✅' if h['ok'] else '⚠️'}")
        else:
            result = sdk.query(args.query)
            if args.json:
                print(json.dumps([
                    {"id": e.id, "title": e.title, "q6": e.metadata.get("q6"),
                     "is_fallback": e.is_fallback}
                    for e in result.entries
                ], ensure_ascii=False, indent=2))
            else:
                print(f"\nQuery: '{args.query}'  →  {len(result.entries)} entries")
                for e in result.entries[:10]:
                    fb = " [fb]" if e.is_fallback else ""
                    q6 = f"  Q6={e.metadata.get('q6', '?')}" if e.metadata.get('q6') else ""
                    print(f"  [{e.id.split(':')[0].upper()}] {e.title}{q6}{fb}")
                c = result.consensus or {}
                print(f"\nConsensus: {int(c.get('coverage', 0)*100)}% real  "
                      f"+{int(c.get('coverage_with_fallback', 0)*100)}% fallback")


if __name__ == "__main__":
    main()
