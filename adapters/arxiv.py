"""
ArxivAdapter — адаптер для поиска научных статей через arXiv API.

Использует официальный arXiv Atom API (без ключей). Кэширует результаты.
Маппирует темы на Q6-координаты через CA-классы.

Конфигурация:
  NAUTILUS_ARXIV_CATEGORIES — через запятую, default: cs.AI,cs.LG,cs.IR
  NAUTILUS_ARXIV_MAX        — макс. результатов, default: 8

Использование:
  portal.register("arxiv", ArxivAdapter())
  portal.register("arxiv_physics", ArxivAdapter(categories=["physics.quant-ph"]))
"""

import os
import time
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
from .base import BaseAdapter, PortalEntry
from .cache import CacheManager

_cache = CacheManager(ttl=3600 * 12)  # 12h cache for arxiv

# arXiv category → Q6 coordinate + CA class
_CATEGORY_Q6 = {
    "cs.AI":        ("111110", "IV", +3),
    "cs.LG":        ("101010", "IV", +2),
    "cs.IR":        ("010100", "II",  0),
    "cs.CL":        ("110001", "IV", +2),
    "cs.NE":        ("111111", "IV", +3),
    "math.CO":      ("001001", "II", -1),
    "math.CT":      ("111111", "IV", +3),
    "physics.quant-ph": ("110001", "IV", +3),
    "q-bio":        ("010111", "IV", +2),
}
_DEFAULT_Q6 = ("010100", "II", 0)

NS = "http://www.w3.org/2005/Atom"


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


class ArxivAdapter(BaseAdapter):
    """Searches arXiv for recent papers matching the query. Uses disk cache."""

    name = "arxiv"

    def __init__(self, categories: list[str] | None = None, max_results: int | None = None):
        env_cats = os.environ.get("NAUTILUS_ARXIV_CATEGORIES", "cs.AI,cs.LG,cs.IR")
        env_max = int(os.environ.get("NAUTILUS_ARXIV_MAX", "8"))
        self._categories = categories or env_cats.split(",")
        self._max = max_results or env_max

    def _cache_key(self, query: str) -> str:
        cats = "_".join(sorted(self._categories))
        return f"arxiv_{cats}_{query.replace(' ', '_')[:40]}"

    def _search_arxiv(self, query: str) -> list[dict]:
        cat_filter = " OR ".join(f"cat:{c}" for c in self._categories)
        q_str = f"({urllib.parse.quote(query)}) AND ({urllib.parse.quote(cat_filter)})"
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query={q_str}"
            f"&max_results={self._max}"
            f"&sortBy=relevance&sortOrder=descending"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nautilus-portal/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
            return self._parse_xml(xml_data)
        except Exception:
            return []

    def _parse_xml(self, xml_data: bytes) -> list[dict]:
        root = ET.fromstring(xml_data)
        results = []
        for entry in root.findall(_tag("entry")):
            arxiv_id = (entry.findtext(_tag("id")) or "").split("/abs/")[-1].strip()
            title = (entry.findtext(_tag("title")) or "").replace("\n", " ").strip()
            summary = (entry.findtext(_tag("summary")) or "").replace("\n", " ").strip()
            published = (entry.findtext(_tag("published")) or "")[:10]
            authors = [
                a.findtext(_tag("name")) or ""
                for a in entry.findall(_tag("author"))
            ]
            cats = [
                c.get("term", "")
                for c in entry.findall("{http://arxiv.org/schemas/atom}primary_category")
            ] + [
                c.get("term", "")
                for c in entry.findall("{http://arxiv.org/schemas/atom}category")
            ]
            if not arxiv_id or not title:
                continue
            results.append({
                "id": arxiv_id,
                "title": title,
                "summary": summary[:600],
                "published": published,
                "authors": authors[:3],
                "categories": list(dict.fromkeys(cats)),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
            })
        return results

    def _make_entry(self, paper: dict) -> PortalEntry:
        cats = paper["categories"]
        q6, ca_class, alpha = _DEFAULT_Q6
        for cat in cats:
            if cat in _CATEGORY_Q6:
                q6, ca_class, alpha = _CATEGORY_Q6[cat]
                break
        authors_str = ", ".join(paper["authors"])
        if len(paper["authors"]) == 3:
            authors_str += " et al."
        return PortalEntry(
            id=f"arxiv:{paper['id'].replace('/', '_')}",
            title=paper["title"],
            source=paper["url"],
            format_type="document",
            content=paper["summary"],
            metadata={
                "arxiv_id": paper["id"],
                "published": paper["published"],
                "authors": paper["authors"],
                "categories": paper["categories"],
                "q6": q6,
                "alpha": alpha,
                "ca_class": ca_class,
            },
            links=[f"info1:alpha:{alpha}"],
        )

    def fetch(self, query: str) -> list[PortalEntry]:
        if not query or query in ("all", ""):
            query = " ".join(self._categories[:2])

        cache_key = self._cache_key(query)
        cached = _cache.get(cache_key)
        if cached is not None:
            papers = cached.get("papers", [])
        else:
            papers = self._search_arxiv(query)
            if papers:
                _cache.set(cache_key, {"papers": papers, "query": query})

        return [self._make_entry(p) for p in papers]

    def describe(self) -> dict:
        return {
            "format": "arxiv",
            "native_unit": "Научная статья (preprint)",
            "categories": self._categories,
            "max_results": self._max,
            "api": "https://export.arxiv.org/api/query",
            "cache_ttl_hours": 12,
        }
