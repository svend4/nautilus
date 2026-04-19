"""
JSONLAdapter — читает локальные .jsonl (JSON Lines) файлы как поток записей.

Каждая строка файла = один JSON-объект → один PortalEntry.
Полезно для: LLM-output, логов bidir_train.py, экспорта из других систем.

Ожидаемые поля (все опциональны кроме одного из id/title):
  id, title, content, source, format_type,
  q6, alpha, tags, links

Конфигурация:
  NAUTILUS_JSONL_PATH — путь к файлу или директории (glob *.jsonl)
  NAUTILUS_JSONL_MAX  — максимум записей, default: 200

Использование:
  portal.register("corpus", JSONLAdapter("corpus/knowledge.jsonl"))
  portal.register("corpus", JSONLAdapter("data/"))  # все *.jsonl в папке
"""

import json
import os
import re
from pathlib import Path
from .base import BaseAdapter, PortalEntry, fuzzy_match


def _slugify(text: str, maxlen: int = 32) -> str:
    return re.sub(r"[^a-zA-Z0-9_а-яА-Я]", "_", text)[:maxlen]


class JSONLAdapter(BaseAdapter):
    """Reads JSON Lines files as PortalEntry streams."""

    name = "jsonl"

    def __init__(self, path: str | None = None, max_entries: int | None = None):
        env_path = os.environ.get("NAUTILUS_JSONL_PATH", ".")
        env_max = int(os.environ.get("NAUTILUS_JSONL_MAX", "200"))
        self._path = Path(path or env_path)
        self._max = max_entries or env_max
        self._entries_cache: list[PortalEntry] | None = None

    def _find_files(self) -> list[Path]:
        if self._path.is_file():
            return [self._path]
        if self._path.is_dir():
            return sorted(self._path.rglob("*.jsonl"))[:20]
        return []

    def _load_all(self) -> list[PortalEntry]:
        if self._entries_cache is not None:
            return self._entries_cache

        entries = []
        for file in self._find_files():
            try:
                for line in file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    entry = self._obj_to_entry(obj, file.stem)
                    if entry:
                        entries.append(entry)
                    if len(entries) >= self._max:
                        break
            except Exception:
                continue
            if len(entries) >= self._max:
                break

        self._entries_cache = entries
        return entries

    def _obj_to_entry(self, obj: dict, source_file: str) -> PortalEntry | None:
        if not isinstance(obj, dict):
            return None

        # ID
        entry_id = obj.get("id") or obj.get("entry_id")
        if not entry_id:
            title_raw = obj.get("title") or obj.get("name") or obj.get("text", "")[:30]
            if not title_raw:
                return None
            entry_id = f"jsonl:{source_file}:{_slugify(str(title_raw))}"
        elif not str(entry_id).startswith("jsonl:"):
            entry_id = f"jsonl:{entry_id}"

        title = str(obj.get("title") or obj.get("name") or entry_id)
        content = str(obj.get("content") or obj.get("text") or obj.get("summary") or "")
        source = str(obj.get("source") or obj.get("repo") or source_file)
        fmt = str(obj.get("format_type") or obj.get("type") or "document")
        q6 = str(obj.get("q6") or "")
        alpha = obj.get("alpha")
        tags = obj.get("tags") or obj.get("labels") or []
        links = obj.get("links") or []
        is_fb = bool(obj.get("is_fallback", False))

        meta: dict = {}
        if q6 and len(q6) == 6:
            meta["q6"] = q6
        if alpha is not None:
            meta["alpha"] = alpha
        if tags:
            meta["tags"] = tags
        # Copy any extra keys
        for k, v in obj.items():
            if k not in ("id", "entry_id", "title", "name", "content", "text",
                         "summary", "source", "repo", "format_type", "type",
                         "q6", "alpha", "tags", "labels", "links", "is_fallback"):
                meta[k] = v

        return PortalEntry(
            id=entry_id,
            title=title[:200],
            source=source,
            format_type=fmt,
            content=content[:1000],
            metadata=meta,
            links=[str(l) for l in links[:10]],
            is_fallback=is_fb,
        )

    def fetch(self, query: str) -> list[PortalEntry]:
        all_entries = self._load_all()
        if not all_entries:
            return []
        q = query.lower()
        if not q:
            return all_entries[:10]
        results = [
            e for e in all_entries
            if fuzzy_match(q, e.title) or fuzzy_match(q, e.content)
        ]
        return results[:10] if results else all_entries[:3]

    def reload(self) -> None:
        """Force re-read all files (clears cache)."""
        self._entries_cache = None

    def describe(self) -> dict:
        files = self._find_files()
        all_entries = self._load_all()
        return {
            "format": "jsonl",
            "native_unit": "JSON Lines запись",
            "path": str(self._path),
            "files": [str(f) for f in files],
            "total_entries": len(all_entries),
            "max_entries": self._max,
        }
