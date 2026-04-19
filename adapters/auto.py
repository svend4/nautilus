"""
AutoAdapter — универсальный адаптер для репозиториев с nautilus.json.

Читает nautilus.json из корня GitHub-репо и строит записи по полю index[].
Не требует изменений в nautilus — репо регистрирует себя сам.

Использование:
    adapter = AutoAdapter("owner/myrepo")
    entries = adapter.fetch("knowledge")
"""

import json
import os
import urllib.request
from .base import BaseAdapter, PortalEntry


class AutoAdapter(BaseAdapter):
    """Читает nautilus.json из корня любого GitHub-репо."""

    def __init__(self, repo: str):
        self.name = repo.split("/")[-1]
        self.REPO = repo
        self._data: dict = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        self._data = self._fetch_nautilus_json()

    def _fetch_nautilus_json(self) -> dict:
        for branch in ("main", "master"):
            url = f"https://raw.githubusercontent.com/{self.REPO}/{branch}/nautilus.json"
            try:
                headers = {"User-Agent": "nautilus-portal/1.0"}
                token = os.environ.get("GITHUB_TOKEN")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as r:
                    return json.loads(r.read())
            except Exception:
                continue
        return {}

    def fetch(self, query: str) -> list[PortalEntry]:
        self._load()
        q = query.lower()
        index = self._data.get("index", [])

        results = [
            self._make_entry(item)
            for item in index
            if q in item.get("title", "").lower()
            or q in item.get("content", "").lower()
            or q in item.get("tags", [])
        ]

        return results or self._fallback_entries()

    def _make_entry(self, item: dict) -> PortalEntry:
        fmt = self._data.get("format", self.name)
        return PortalEntry(
            id=item.get("id", f"{fmt}:{item.get('title','?')[:20]}"),
            title=item.get("title", ""),
            source=self.REPO,
            format_type=item.get("type", "document"),
            content=item.get("content", ""),
            metadata={
                "q6": item.get("q6", ""),
                "alpha": item.get("alpha"),
                "tags": item.get("tags", []),
            },
            links=item.get("links", []),
        )

    def _fallback_entries(self) -> list[PortalEntry]:
        self._load()
        if not self._data:
            return []
        fmt = self._data.get("format", self.name)
        return [
            PortalEntry(
                id=f"{fmt}:overview",
                title=f"{self.REPO} — обзор",
                source=self.REPO,
                format_type="document",
                content=self._data.get("description", ""),
                metadata={
                    "format": fmt,
                    "compatibility": self._data.get("compatibility", 0),
                    "total_items": self._data.get("total_items", "?"),
                },
                links=[],
            )
        ]

    def describe(self) -> dict:
        self._load()
        d = {k: v for k, v in self._data.items() if k != "index"}
        d.setdefault("repo", self.REPO)
        d.setdefault("format", self.name)
        d.setdefault("native_unit", "документ")
        return d

    def is_available(self) -> bool:
        """Проверить что репо содержит nautilus.json."""
        self._load()
        return bool(self._data)
