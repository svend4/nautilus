"""
ObsidianAdapter — адаптер для локального Obsidian-хранилища (.md с [[wikilinks]]).

Читает .md файлы из указанной директории (vault), извлекает:
  - заголовки и содержание
  - [[wikilinks]] как cross-links
  - #теги как метаданные
  - frontmatter (YAML между --- блоками)

Конфигурация через env:
  NAUTILUS_OBSIDIAN_VAULT  — путь к vault директории
  NAUTILUS_OBSIDIAN_DEPTH  — глубина поиска (default: 3)

Использование:
  portal.register("obsidian", ObsidianAdapter("/path/to/vault"))
"""

import os
import re
from pathlib import Path
from .base import BaseAdapter, PortalEntry, fuzzy_match


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown text. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 4:].strip()
    meta = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def _extract_wikilinks(text: str) -> list[str]:
    """Extract [[target]] patterns as link targets."""
    return re.findall(r"\[\[([^\]|#]+?)(?:\|[^\]]+?)?\]\]", text)


def _extract_tags(text: str) -> list[str]:
    """Extract #tag patterns (word characters only)."""
    return re.findall(r"(?<!\[)#(\w+)", text)


def _guess_q6(meta: dict, tags: list) -> str:
    """Guess Q6 coordinate from frontmatter or tags."""
    if "q6" in meta:
        return str(meta["q6"])
    if "alpha" in meta:
        alpha_map = {"-4": "000000", "-3": "000001", "-2": "000011",
                     "-1": "000111", "0": "010100", "1": "010111",
                     "2": "101010", "3": "111110", "4": "111111"}
        return alpha_map.get(str(meta["alpha"]), "010100")
    # Infer from tags
    if any(t in tags for t in ("ontology", "философия", "онтология")):
        return "111111"
    if any(t in tags for t in ("methodology", "методология")):
        return "101010"
    if any(t in tags for t in ("code", "код", "implementation")):
        return "000001"
    return "010100"


class ObsidianAdapter(BaseAdapter):
    """Reads a local Obsidian vault directory. Supports [[wikilinks]] as cross-links."""

    name = "obsidian"

    def __init__(self, vault_path: str | None = None, max_depth: int | None = None):
        env_path = os.environ.get("NAUTILUS_OBSIDIAN_VAULT")
        env_depth = os.environ.get("NAUTILUS_OBSIDIAN_DEPTH")

        self._vault = Path(vault_path or env_path or ".")
        self._depth = max_depth or int(env_depth or 3)
        self._entries_cache: list[PortalEntry] | None = None

    def _load_all(self) -> list[PortalEntry]:
        if self._entries_cache is not None:
            return self._entries_cache
        if not self._vault.exists() or not self._vault.is_dir():
            self._entries_cache = []
            return []

        entries = []
        for md_file in self._vault.rglob("*.md"):
            # Limit depth
            rel = md_file.relative_to(self._vault)
            if len(rel.parts) > self._depth:
                continue
            try:
                entry = self._parse_file(md_file)
                if entry:
                    entries.append(entry)
            except Exception:
                continue

        self._entries_cache = entries
        return entries

    def _parse_file(self, path: Path) -> PortalEntry | None:
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = _parse_frontmatter(text)
        wikilinks = _extract_wikilinks(text)
        tags = _extract_tags(text)

        # Title: frontmatter title > first H1 > filename
        title = meta.get("title") or ""
        if not title:
            m = re.search(r"^#\s+(.+)", body, re.MULTILINE)
            title = m.group(1) if m else path.stem

        # Content: first 500 chars of body, no headings
        content_body = re.sub(r"^#{1,6}\s+.*$", "", body, flags=re.MULTILINE).strip()
        content_body = re.sub(r"\[\[.*?\]\]", "", content_body)
        content = content_body[:500].strip()

        q6 = _guess_q6(meta, tags)
        alpha = meta.get("alpha", "0")

        # Build links: [[target]] → obsidian:{slugified_target}
        links = [f"obsidian:{re.sub(r'[^a-zA-Z0-9_а-яА-Я]', '_', w.strip())}"
                 for w in wikilinks[:10]]

        slug = re.sub(r"[^a-zA-Z0-9_а-яА-Я]", "_", path.stem)

        return PortalEntry(
            id=f"obsidian:{slug}",
            title=title,
            source=str(self._vault),
            format_type="document",
            content=content,
            metadata={
                "path": str(path.relative_to(self._vault)),
                "q6": q6,
                "alpha": alpha,
                "tags": tags,
                **{k: v for k, v in meta.items() if k not in ("title", "q6", "alpha")},
            },
            links=links,
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
            if (fuzzy_match(q, e.title) or fuzzy_match(q, e.content)
                or q in " ".join(e.metadata.get("tags", [])).lower())
        ]
        return results[:10] if results else all_entries[:5]

    def describe(self) -> dict:
        all_entries = self._load_all()
        return {
            "format": "obsidian",
            "native_unit": "Markdown-заметка с [[wikilinks]]",
            "vault_path": str(self._vault),
            "total_notes": len(all_entries),
            "vault_exists": self._vault.exists(),
        }

    def is_available(self) -> bool:
        return self._vault.exists() and self._vault.is_dir()
