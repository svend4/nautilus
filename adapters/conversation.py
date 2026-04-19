"""
ConversationAdapter — читает экспорты разговоров Claude/LLM как поток записей.

Поддерживаемые форматы:
  .md   — Markdown (разбивается по заголовкам ## / ###)
  .txt  — plain text (разбивается по абзацам)
  .json — JSON-объект, массив, или raw text внутри JSON
  (без расширения) — пробует JSON, затем text

Каждый раздел / абзац-блок → один PortalEntry.
Q6-координата назначается автоматически по ключевым словам темы.

Конфигурация:
  path       — путь к файлу или директории (default: docs/)
  max_entries — максимум записей на файл (default: 80)
  chunk_size  — максимум символов в одной записи (default: 700)

Использование:
  from adapters.conversation import ConversationAdapter
  portal.register("conversations", ConversationAdapter("docs/"))
  portal.register("sessions",     ConversationAdapter("exports/session.md"))
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .base import BaseAdapter, PortalEntry, fuzzy_match

# ---------------------------------------------------------------------------
# Topic → Q6 mapping (ordered: first match wins)
# ---------------------------------------------------------------------------

_TOPIC_Q6: list[tuple[list[str], str]] = [
    (["multi-agent", "мультиагент", "sub-agent", "orchestrat", "мета-агент",
      "meta-agent", "иерархич"], "110100"),
    (["architecture", "архитектур", "infrastructure", "инфраструктур",
      "layer", "слой", "pipeline", "конвейер"], "101010"),
    (["strategy", "стратег", "roadmap", "дорожная карта", "planning",
      "планирован", "консолидац"], "111110"),
    (["implement", "реализ", "algorithm", "алгоритм", "code", "код",
      "programming", "программирован"], "010101"),
    (["research", "исследован", "theory", "теори", "concept", "концепт",
      "formal", "formali"], "010100"),
    (["knowledge", "знание", "ontolog", "онтолог", "semantic", "семантик",
      "meta", "мета"], "110001"),
    (["analysis", "анализ", "evaluation", "оценк", "cluster", "кластер",
      "review", "обзор"], "100101"),
    (["agent", "агент", "llm", "model", "модель", "prompt", "ai", "ии"],
     "000001"),
]

_SUPPORTED_EXT: frozenset[str] = frozenset({".md", ".txt", ".json", ""})
_MAX_FILE_BYTES = 3 * 1024 * 1024  # skip files > 3 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_q6(text: str) -> str:
    tl = text.lower()
    for keywords, q6 in _TOPIC_Q6:
        if any(kw in tl for kw in keywords):
            return q6
    return "000000"


def _slugify(text: str, maxlen: int = 40) -> str:
    return re.sub(r"[^a-zA-Z0-9_а-яА-Я]", "_", text.strip())[:maxlen]


def _first_sentence(text: str, maxlen: int = 90) -> str:
    """Extract a short title from the first line of a text block."""
    first = text.strip().split("\n")[0].strip()
    first = re.sub(r"^[*#\->`•]+\s*", "", first)
    return first[:maxlen] if first else text[:maxlen]


def _split_markdown(text: str, chunk_size: int) -> list[tuple[str, str]]:
    """Split markdown by ## / ### headings → [(title, body), ...]."""
    heading_re = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
    matches = list(heading_re.finditer(text))
    if not matches:
        return _split_plain(text, chunk_size)

    results: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        if len(body) <= chunk_size:
            results.append((title, body))
        else:
            for j, (sub_title, sub_body) in enumerate(_split_plain(body, chunk_size)):
                label = f"{title} ({j + 1})" if j else title
                results.append((label, sub_body))
    return results


def _split_plain(text: str, chunk_size: int) -> list[tuple[str, str]]:
    """Split plain text into paragraph-based chunks ≤ chunk_size chars."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[tuple[str, str]] = []
    buf: list[str] = []
    buf_len = 0

    def _flush() -> None:
        if not buf:
            return
        combined = "\n\n".join(buf)
        chunks.append((_first_sentence(combined), combined))
        buf.clear()

    for para in paragraphs:
        if buf_len + len(para) > chunk_size and buf:
            _flush()
            buf_len = 0
        buf.append(para)
        buf_len += len(para)
    _flush()
    return chunks


def _extract_json_text(data: Any) -> list[tuple[str, str]]:
    """Extract (title, text) pairs from a parsed JSON value."""
    results: list[tuple[str, str]] = []
    if isinstance(data, list):
        for item in data:
            results.extend(_extract_json_text(item))
    elif isinstance(data, dict):
        title = str(data.get("title") or data.get("name") or data.get("heading") or "")
        content = str(
            data.get("content") or data.get("text") or
            data.get("body") or data.get("summary") or ""
        )
        if content:
            results.append((title or _first_sentence(content), content))
        else:
            # Recurse into string values that look like long text
            for v in data.values():
                if isinstance(v, str) and len(v) > 100:
                    results.append((_first_sentence(v), v))
                elif isinstance(v, (list, dict)):
                    results.extend(_extract_json_text(v))
    elif isinstance(data, str) and len(data) > 50:
        results.append((_first_sentence(data), data))
    return results


# ---------------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------------

class ConversationAdapter(BaseAdapter):
    """
    Reads Claude/LLM conversation exports (md, txt, json) as PortalEntry stream.

    Each section / paragraph block becomes one PortalEntry.
    Q6 is auto-assigned by topic keyword detection.
    """

    name = "conversations"

    def __init__(
        self,
        path: str | None = None,
        max_entries: int | None = None,
        chunk_size: int | None = None,
    ) -> None:
        env_path = os.environ.get("NAUTILUS_CONV_PATH", "docs")
        env_max = int(os.environ.get("NAUTILUS_CONV_MAX", "80"))
        env_chunk = int(os.environ.get("NAUTILUS_CONV_CHUNK", "700"))
        self._path = Path(path or env_path)
        self._max = max_entries if max_entries is not None else env_max
        self._chunk = chunk_size if chunk_size is not None else env_chunk
        self._cache: list[PortalEntry] | None = None

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def _find_files(self) -> list[Path]:
        if self._path.is_file():
            return [self._path]
        if not self._path.is_dir():
            return []
        found: list[Path] = []
        for p in sorted(self._path.iterdir()):
            if p.is_file() and p.suffix in _SUPPORTED_EXT:
                if p.stat().st_size <= _MAX_FILE_BYTES:
                    found.append(p)
        return found[:10]  # at most 10 files

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_file(self, path: Path) -> list[tuple[str, str]]:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []

        ext = path.suffix.lower()

        if ext == ".json":
            try:
                data = json.loads(raw)
                pairs = _extract_json_text(data)
                if pairs:
                    return pairs
            except (json.JSONDecodeError, ValueError):
                pass
            # fall through to text splitting
            return _split_plain(raw, self._chunk)

        if ext == ".md":
            return _split_markdown(raw, self._chunk)

        if ext in (".txt", ""):
            # Try JSON first for extension-less files
            if ext == "":
                try:
                    data = json.loads(raw)
                    pairs = _extract_json_text(data)
                    if pairs:
                        return pairs
                except (json.JSONDecodeError, ValueError):
                    pass
            return _split_plain(raw, self._chunk)

        return []

    # ------------------------------------------------------------------
    # Entry construction
    # ------------------------------------------------------------------

    def _make_entry(
        self, title: str, content: str, source_file: str, idx: int
    ) -> PortalEntry:
        slug = _slugify(title or content[:30])
        q6 = _detect_q6(title + " " + content[:300])
        return PortalEntry(
            id=f"conv:{source_file}:{idx}:{slug}",
            title=title[:200] or f"Раздел {idx + 1}",
            source=f"docs/{source_file}",
            format_type="conversation",
            content=content[:self._chunk],
            metadata={"q6": q6, "file": source_file, "section": idx},
            links=[],
            is_fallback=False,
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self) -> list[PortalEntry]:
        if self._cache is not None:
            return self._cache

        entries: list[PortalEntry] = []
        for file in self._find_files():
            pairs = self._parse_file(file)
            for i, (title, content) in enumerate(pairs):
                if not content.strip():
                    continue
                entries.append(self._make_entry(title, content, file.stem, i))
                if len(entries) >= self._max:
                    break
            if len(entries) >= self._max:
                break

        self._cache = entries
        return entries

    # ------------------------------------------------------------------
    # BaseAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str) -> list[PortalEntry]:
        all_entries = self._load_all()
        if not all_entries:
            return []
        q = query.lower().strip()
        if not q:
            return all_entries[:10]
        results = [
            e for e in all_entries
            if fuzzy_match(q, e.title) or fuzzy_match(q, e.content)
        ]
        return results[:10] if results else all_entries[:3]

    def reload(self) -> None:
        """Clear cache and re-read all files on next fetch."""
        self._cache = None

    def describe(self) -> dict[str, Any]:
        files = self._find_files()
        entries = self._load_all()
        return {
            "format": "conversation",
            "native_unit": "раздел разговора",
            "path": str(self._path),
            "files": [f.name for f in files],
            "total_entries": len(entries),
            "max_entries": self._max,
            "chunk_size": self._chunk,
            "q6_mapping": "auto (keyword detection)",
        }
