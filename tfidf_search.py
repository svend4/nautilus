#!/usr/bin/env python3
"""
tfidf_search.py — TF-IDF поиск по всей экосистеме Nautilus.

Строит TF-IDF матрицу по всем записям, ищет по косинусному сходству.
Превосходит простой substring-поиск на смысловых запросах.

Только stdlib, нет зависимостей от numpy/sklearn.

Использование:
    python tfidf_search.py "квантовые вычисления"
    python tfidf_search.py --top 5 "биологические системы"
    python tfidf_search.py --json "синтез"
    python tfidf_search.py --build-index      # предварительно построить индекс
"""

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

from portal import NautilusPortal
from adapters.base import PortalEntry

_INDEX_PATH = Path("snapshots/tfidf_index.json")


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into tokens ≥ 2 chars."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [t for t in text.split() if len(t) >= 2]


def _collect_entries(portal: NautilusPortal) -> list[PortalEntry]:
    seen: set[str] = set()
    result: list[PortalEntry] = []
    for q in ["", "knowledge", "синтез", "алгоритм", "agent", "theory", "concept", "data"]:
        for e in portal.query(q, ranked=False).entries:
            if e.id not in seen:
                seen.add(e.id)
                result.append(e)
    return result


def _doc_text(e: PortalEntry) -> str:
    """Combine title (weighted ×3) and content for TF-IDF."""
    return (e.title + " ") * 3 + e.content


class TFIDFIndex:
    """Pure-stdlib TF-IDF index over PortalEntry corpus."""

    def __init__(self) -> None:
        self.entries: list[PortalEntry] = []
        self.idf: dict[str, float] = {}
        self.tfidf_vecs: list[dict[str, float]] = []
        self.built_at: str = ""

    # -- Build ----------------------------------------------------------------

    def build(self, entries: list[PortalEntry]) -> None:
        self.entries = entries
        N = len(entries)
        if N == 0:
            return

        # Tokenize all docs
        tokenized: list[list[str]] = [_tokenize(_doc_text(e)) for e in entries]

        # Document frequency
        df: dict[str, int] = {}
        for tokens in tokenized:
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1

        # IDF (smoothed, log(1+N/df))
        self.idf = {t: math.log(1 + N / (1 + d)) for t, d in df.items()}

        # TF-IDF vectors (L2-normalised)
        self.tfidf_vecs = []
        for tokens in tokenized:
            tf: dict[str, float] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0.0) + 1.0
            total = len(tokens) or 1
            vec: dict[str, float] = {}
            norm = 0.0
            for t, cnt in tf.items():
                val = (cnt / total) * self.idf.get(t, 0.0)
                vec[t] = val
                norm += val * val
            norm = math.sqrt(norm) or 1.0
            self.tfidf_vecs.append({t: v / norm for t, v in vec.items()})

        self.built_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # -- Serialise ------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(exist_ok=True)
        payload = {
            "built_at": self.built_at,
            "idf": self.idf,
            "entries": [
                {
                    "id": e.id,
                    "title": e.title,
                    "source": e.source,
                    "format_type": e.format_type,
                    "content": e.content[:300],
                    "q6": e.metadata.get("q6", ""),
                    "is_fallback": e.is_fallback,
                    "vec": self.tfidf_vecs[i],
                }
                for i, e in enumerate(self.entries)
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False))

    def load(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
            self.idf = data["idf"]
            self.built_at = data.get("built_at", "")
            # Reconstruct minimal PortalEntry objects
            from adapters.base import PortalEntry
            self.entries = []
            self.tfidf_vecs = []
            for item in data["entries"]:
                e = PortalEntry(
                    id=item["id"], title=item["title"], source=item["source"],
                    format_type=item["format_type"], content=item["content"],
                    metadata={"q6": item.get("q6", "")},
                    is_fallback=item.get("is_fallback", False),
                )
                self.entries.append(e)
                self.tfidf_vecs.append(item["vec"])
            return True
        except Exception:
            return False

    # -- Search ---------------------------------------------------------------

    def query_vec(self, query: str) -> dict[str, float]:
        """Build (unnormalised) TF-IDF vector for query."""
        tokens = _tokenize(query)
        if not tokens:
            return {}
        vec: dict[str, float] = {}
        for t in tokens:
            if t in self.idf:
                vec[t] = vec.get(t, 0.0) + self.idf[t]
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Return top-k entries sorted by cosine similarity to query."""
        qvec = self.query_vec(query)
        if not qvec or not self.entries:
            return []

        scores: list[tuple[float, int]] = []
        for i, vec in enumerate(self.tfidf_vecs):
            # Cosine similarity = dot product (both L2-normalised)
            score = sum(qvec.get(t, 0.0) * v for t, v in vec.items())
            if score > 0:
                scores.append((score, i))

        scores.sort(reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            e = self.entries[idx]
            results.append({
                "score": round(score, 4),
                "id": e.id,
                "title": e.title,
                "source": e.source,
                "content": e.content[:200],
                "q6": e.metadata.get("q6", ""),
                "is_fallback": e.is_fallback,
            })
        return results


def print_results(query: str, results: list[dict[str, Any]], built_at: str) -> None:
    print(f"\n⬡ TF-IDF Поиск: «{query}»")
    print(f"{'=' * 54}")
    print(f"Индекс: {built_at}  Найдено: {len(results)}")
    print()
    if not results:
        print("  (нет результатов)")
        return
    for i, r in enumerate(results, 1):
        q6_tag = f"  Q6={r['q6']}" if r.get("q6") else ""
        fb_tag = "  [fallback]" if r["is_fallback"] else ""
        print(f"  {i:2d}. [{r['score']:.3f}]  {r['title'][:55]}{q6_tag}{fb_tag}")
        print(f"       {r['id']}")
        if r.get("content"):
            snippet = r["content"][:120].replace("\n", " ")
            print(f"       {snippet}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nautilus TF-IDF Search")
    parser.add_argument("query", nargs="?", default="", help="Поисковый запрос")
    parser.add_argument("--top", type=int, default=10, help="Топ-N результатов")
    parser.add_argument("--json", action="store_true", help="JSON-вывод")
    parser.add_argument("--build-index", action="store_true",
                        help="Собрать и сохранить TF-IDF индекс")
    parser.add_argument("--no-cache", action="store_true",
                        help="Пересобрать индекс перед поиском")
    args = parser.parse_args()

    idx = TFIDFIndex()

    if args.build_index or args.no_cache or not _INDEX_PATH.exists():
        portal = NautilusPortal()
        print("Собираем записи...", end=" ", flush=True)
        entries = _collect_entries(portal)
        print(f"{len(entries)}.  Строим индекс...", end=" ", flush=True)
        t0 = time.monotonic()
        idx.build(entries)
        elapsed = round((time.monotonic() - t0) * 1000)
        print(f"готово ({elapsed}ms).")
        idx.save(_INDEX_PATH)
        print(f"Индекс сохранён: {_INDEX_PATH}  ({len(entries)} документов)")
        if args.build_index:
            return
    else:
        if not idx.load(_INDEX_PATH):
            print("Не удалось загрузить индекс. Запустите с --build-index.")
            sys.exit(1)

    query = args.query.strip()
    if not query:
        print("Укажите поисковый запрос. Пример: python tfidf_search.py «синтез»")
        return

    results = idx.search(query, top_k=args.top)

    if args.json:
        print(json.dumps({
            "query": query, "built_at": idx.built_at,
            "total": len(results), "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        print_results(query, results, idx.built_at)


if __name__ == "__main__":
    main()
