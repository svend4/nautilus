"""
CacheManager — дисковый кэш для AutoAdapter.

Хранит снимки nautilus.json из внешних репо в cache/.
TTL по умолчанию: 24 часа. Offline-режим: возвращает устаревший кэш.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, cast

CACHE_DIR = Path(__file__).parent.parent / "cache"
DEFAULT_TTL = int(os.environ.get("NAUTILUS_CACHE_TTL", 86400))  # 24ч


class CacheManager:
    def __init__(self, ttl: int = DEFAULT_TTL):
        self.ttl = ttl
        CACHE_DIR.mkdir(exist_ok=True)

    def _key(self, repo: str) -> str:
        return repo.replace("/", "_")

    def _data_path(self, repo: str) -> Path:
        return CACHE_DIR / f"{self._key(repo)}.json"

    def _meta_path(self, repo: str) -> Path:
        return CACHE_DIR / f"{self._key(repo)}.meta.json"

    def get(self, repo: str) -> dict | None:
        """Вернуть кэш если свежий, иначе None."""
        data_path = self._data_path(repo)
        meta_path = self._meta_path(repo)
        if not data_path.exists() or not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text())
            age = time.time() - meta.get("fetched_at", 0)
            if age <= self.ttl:
                return cast(dict[str, Any], json.loads(data_path.read_text()))
        except Exception:
            pass
        return None

    def get_stale(self, repo: str) -> dict | None:
        """Вернуть кэш даже если устаревший (для offline-режима)."""
        data_path = self._data_path(repo)
        if not data_path.exists():
            return None
        try:
            return cast(dict[str, Any], json.loads(data_path.read_text()))
        except Exception:
            return None

    def set(self, repo: str, data: dict) -> None:
        """Сохранить данные в кэш."""
        try:
            self._data_path(repo).write_text(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            self._meta_path(repo).write_text(
                json.dumps({"fetched_at": time.time(), "repo": repo})
            )
        except Exception:
            pass

    def invalidate(self, repo: str) -> None:
        """Сбросить кэш для репо."""
        for p in (self._data_path(repo), self._meta_path(repo)):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

    def age_hours(self, repo: str) -> float | None:
        """Возраст кэша в часах, None если нет."""
        meta_path = self._meta_path(repo)
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text())
            return (time.time() - float(meta.get("fetched_at", 0))) / 3600
        except Exception:
            return None

    def list_cached(self) -> list[dict]:
        """Список всех закэшированных репо с метаданными."""
        result = []
        for meta_file in sorted(CACHE_DIR.glob("*.meta.json")):
            try:
                meta = json.loads(meta_file.read_text())
                age_h = (time.time() - meta.get("fetched_at", 0)) / 3600
                data_file = meta_file.with_suffix("").with_suffix(".json")
                size = data_file.stat().st_size if data_file.exists() else 0
                result.append({
                    "repo": meta.get("repo", "?"),
                    "age_hours": round(age_h, 1),
                    "fresh": age_h <= self.ttl / 3600,
                    "size_bytes": size,
                })
            except Exception:
                pass
        return result
