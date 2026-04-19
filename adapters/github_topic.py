"""
GitHubTopicAdapter — автоматически обнаруживает репозитории
с топиком 'nautilus-compatible' через GitHub Search API.

Для каждого найденного репо пытается загрузить nautilus.json,
если есть — делегирует AutoAdapter. Если нет — создаёт базовую запись.

Конфигурация:
  GITHUB_TOKEN               — для увеличения rate limit
  NAUTILUS_TOPIC             — топик для поиска, default: nautilus-compatible
  NAUTILUS_TOPIC_MAX         — макс. репо, default: 10

Использование:
  portal.register("discovered", GitHubTopicAdapter())
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Any, cast
from .base import BaseAdapter, PortalEntry
from .cache import CacheManager

_cache = CacheManager(ttl=3600 * 6)  # 6h


class GitHubTopicAdapter(BaseAdapter):
    """Discovers repos via GitHub topic search and wraps them as entries."""

    name = "github_topic"

    def __init__(self, topic: str | None = None, max_repos: int | None = None):
        self._topic = topic or os.environ.get("NAUTILUS_TOPIC", "nautilus-compatible")
        self._max = max_repos or int(os.environ.get("NAUTILUS_TOPIC_MAX", "10"))
        self._repos: list[dict] | None = None

    def _headers(self) -> dict:
        h = {"User-Agent": "nautilus-portal/1.0",
             "Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _search_repos(self) -> list[dict]:
        cache_key = f"github_topic_{self._topic}"
        cached = _cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached.get("repos", []))

        url = (
            "https://api.github.com/search/repositories"
            f"?q=topic:{urllib.parse.quote(self._topic)}"
            f"&per_page={self._max}&sort=stars"
        )
        try:
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read())
            repos = [
                {
                    "full_name": r["full_name"],
                    "description": r.get("description") or "",
                    "stars": r.get("stargazers_count", 0),
                    "language": r.get("language") or "unknown",
                    "url": r["html_url"],
                    "topics": r.get("topics", []),
                }
                for r in data.get("items", [])
            ]
            _cache.set(cache_key, {"repos": repos})
            return repos
        except Exception:
            return []

    def _fetch_nautilus_json(self, full_name: str) -> dict:
        cache_key = f"nautilus_json_{full_name.replace('/', '_')}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        for branch in ("main", "master"):
            url = f"https://raw.githubusercontent.com/{full_name}/{branch}/nautilus.json"
            try:
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = cast(dict[str, Any], json.loads(resp.read()))
                _cache.set(cache_key, data)
                return data
            except Exception:
                continue
        _cache.set(cache_key, {})
        return {}

    def _make_entry(self, repo: dict) -> PortalEntry:
        nj = self._fetch_nautilus_json(repo["full_name"])
        name = repo["full_name"].split("/")[-1]

        if nj:
            compat = nj.get("compatibility", 0)
            description = nj.get("description") or repo["description"]
            fmt = nj.get("format", name)
            q6 = nj.get("q6") or "010100"
        else:
            compat = 0
            description = repo["description"]
            fmt = name
            q6 = "010100"

        return PortalEntry(
            id=f"discovered:{name}",
            title=f"{repo['full_name']} ★{repo['stars']}",
            source=repo["url"],
            format_type="document",
            content=description[:400],
            metadata={
                "repo": repo["full_name"],
                "stars": repo["stars"],
                "language": repo["language"],
                "topics": repo["topics"],
                "has_nautilus_json": bool(nj),
                "compatibility": compat,
                "q6": q6,
                "alpha": 0,
            },
            links=[],
            is_fallback=not bool(nj),
        )

    def fetch(self, query: str) -> list[PortalEntry]:
        repos = self._search_repos()
        if not repos:
            return []
        q = query.lower()
        entries = [self._make_entry(r) for r in repos]
        if not q or q in ("all", ""):
            return entries
        return [
            e for e in entries
            if q in e.title.lower() or q in e.content.lower()
               or any(q in t for t in e.metadata.get("topics", []))
        ] or entries[:3]

    def describe(self) -> dict:
        repos = self._search_repos()
        return {
            "format": "github_topic",
            "native_unit": "GitHub-репозиторий",
            "topic": self._topic,
            "discovered": len(repos),
            "with_nautilus_json": sum(
                1 for r in repos
                if self._fetch_nautilus_json(r["full_name"])
            ),
        }
