#!/usr/bin/env python3
"""
cluster.py — кластеризация концептов по Q6-близости (расстояние Хэмминга).

Группирует записи экосистемы по близости в Q6-пространстве:
  - Жадная кластеризация: строит кластеры вокруг самых населённых вершин
  - Внутри кластера — все вершины на расстоянии ≤ radius от центроида
  - Аннотирует каждый кластер: домен, CA-класс, α-уровень

Использование:
    python cluster.py               # текстовый отчёт (radius=1)
    python cluster.py --radius 2    # более широкие кластеры
    python cluster.py --json        # JSON-вывод
    python cluster.py --query метод # кластеры для конкретного запроса
"""

import argparse
import json
import sys
import time
from typing import Any

from portal import NautilusPortal
from adapters.base import PortalEntry


# Wolfram CA class for a Q6 bit-string
_CA_CLASS: dict[str, str] = {
    "000000": "I", "000001": "I", "000010": "I", "000011": "I",
    "000100": "II", "000101": "II", "000110": "II", "000111": "II",
    "001000": "II", "001001": "II", "001010": "II", "001011": "II",
    "001100": "II", "001101": "II", "001110": "II", "001111": "II",
    "010000": "II", "010001": "II", "010010": "II", "010011": "II",
    "010100": "II", "010101": "II", "010110": "II", "010111": "II",
    "011000": "II", "011001": "II", "011010": "II", "011011": "II",
    "011100": "II", "011101": "II", "011110": "II", "011111": "II",
    "100000": "III", "100001": "III", "100010": "III", "100011": "III",
    "100100": "III", "100101": "III", "100110": "III", "100111": "III",
    "101000": "III", "101001": "IV", "101010": "IV", "101011": "IV",
    "101100": "III", "101101": "III", "101110": "IV", "101111": "IV",
    "110000": "III", "110001": "IV", "110010": "III", "110011": "IV",
    "110100": "IV", "110101": "IV", "110110": "III", "110111": "IV",
    "111000": "III", "111001": "III", "111010": "IV", "111011": "IV",
    "111100": "IV", "111101": "IV", "111110": "IV", "111111": "IV",
}

_ALPHA_FROM_BITS: dict[str, int] = {
    "000000": -4, "000001": -3, "000010": -3, "000011": -3,
    "000100": -2, "000101": -2, "000110": -2, "000111": -2,
    "001000": -2, "001001": -2, "001010": -2, "001011": -2,
    "001100": -2, "001101": -2, "001110": -2, "001111": -2,
    "010000": -1, "010001": -1, "010010": -1, "010011": -1,
    "010100": 0,  "010101": 0,  "010110": 0,  "010111": 0,
    "011000": 0,  "011001": 0,  "011010": 0,  "011011": 0,
    "011100": 0,  "011101": 0,  "011110": 0,  "011111": 0,
    "100000": 1,  "100001": 1,  "100010": 1,  "100011": 1,
    "100100": 1,  "100101": 1,  "100110": 1,  "100111": 1,
    "101000": 1,  "101001": 2,  "101010": 2,  "101011": 2,
    "101100": 1,  "101101": 1,  "101110": 2,  "101111": 2,
    "110000": 2,  "110001": 3,  "110010": 2,  "110011": 3,
    "110100": 3,  "110101": 3,  "110110": 2,  "110111": 3,
    "111000": 2,  "111001": 2,  "111010": 3,  "111011": 3,
    "111100": 3,  "111101": 3,  "111110": 3,  "111111": 4,
}


def _hamming(a: str, b: str) -> int:
    """Hamming distance between two equal-length bit strings."""
    return sum(x != y for x, y in zip(a, b))


def _collect_entries(portal: NautilusPortal) -> list[PortalEntry]:
    """Collect all non-fallback entries with valid Q6 coordinates."""
    seen: set[str] = set()
    result: list[PortalEntry] = []
    broad = ["", "knowledge", "синтез", "алгоритм", "agent",
             "theory", "concept", "data", "rule"]
    for q in broad:
        for e in portal.query(q, ranked=False).entries:
            if e.id not in seen:
                seen.add(e.id)
                q6 = e.metadata.get("q6", "")
                if isinstance(q6, str) and len(q6) == 6 and all(c in "01" for c in q6):
                    result.append(e)
    return result


def cluster(entries: list[PortalEntry], radius: int = 1) -> list[dict[str, Any]]:
    """
    Greedy Q6 clustering: repeatedly pick the vertex with the most unclustered
    entries, assign all entries within `radius` Hamming distance to it.
    """
    # Build q6 → entries index
    by_q6: dict[str, list[PortalEntry]] = {}
    for e in entries:
        q6 = str(e.metadata.get("q6", ""))
        by_q6.setdefault(q6, []).append(e)

    unclustered = set(by_q6.keys())
    clusters: list[dict[str, Any]] = []

    while unclustered:
        # Pick centroid = vertex with most entries among unclustered
        centroid = max(unclustered, key=lambda v: len(by_q6[v]))

        # Gather all vertices within radius
        members: list[str] = []
        for v in list(unclustered):
            if _hamming(centroid, v) <= radius:
                members.append(v)

        cluster_entries: list[PortalEntry] = []
        for v in members:
            cluster_entries.extend(by_q6[v])
            unclustered.discard(v)

        ca_class = _CA_CLASS.get(centroid, "?")
        alpha = _ALPHA_FROM_BITS.get(centroid, 0)
        real_count = sum(1 for e in cluster_entries if not e.is_fallback)

        clusters.append({
            "centroid": centroid,
            "radius": radius,
            "ca_class": ca_class,
            "alpha": alpha,
            "vertices": sorted(members),
            "size": len(cluster_entries),
            "real": real_count,
            "fallback": len(cluster_entries) - real_count,
            "adapters": sorted({e.id.split(":")[0] for e in cluster_entries}),
            "entries": [
                {"id": e.id, "title": e.title[:60], "q6": str(e.metadata.get("q6", "")),
                 "is_fallback": e.is_fallback}
                for e in cluster_entries
            ],
        })

    # Sort by size descending
    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters


def analyze(portal: NautilusPortal, radius: int = 1) -> dict[str, Any]:
    t0 = time.monotonic()
    entries = _collect_entries(portal)
    clusters_list = cluster(entries, radius)
    elapsed_ms = round((time.monotonic() - t0) * 1000)

    ca_breakdown: dict[str, int] = {}
    for cl in clusters_list:
        ca_breakdown[cl["ca_class"]] = ca_breakdown.get(cl["ca_class"], 0) + cl["size"]

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_ms": elapsed_ms,
        "radius": radius,
        "total_entries": len(entries),
        "total_clusters": len(clusters_list),
        "ca_breakdown": ca_breakdown,
        "clusters": clusters_list,
    }


def print_report(data: dict[str, Any]) -> None:
    clusters_list = data["clusters"]
    ca = data["ca_breakdown"]

    print(f"\n⬡ Nautilus Concept Clustering")
    print(f"{'=' * 54}")
    print(f"Дата:      {data['generated_at']}  ({data['elapsed_ms']}ms)")
    print(f"Записей:   {data['total_entries']}  →  {data['total_clusters']} кластеров  (radius={data['radius']})")
    print()

    ca_order = ["I", "II", "III", "IV", "?"]
    print("── CA-классы ─────────────────────────────────────────")
    for cls in ca_order:
        n = ca.get(cls, 0)
        if n:
            bar = "█" * min(30, n // 2)
            print(f"  CA-{cls:3s}  {n:3d} записей  {bar}")

    print()
    print("── Кластеры (топ-15) ─────────────────────────────────")
    for i, cl in enumerate(clusters_list[:15], 1):
        adapters_str = ",".join(cl["adapters"])[:30]
        real_str = f"real={cl['real']}" if cl["real"] < cl["size"] else f"real={cl['real']}"
        fb_str = f" fb={cl['fallback']}" if cl["fallback"] else ""
        print(f"  {i:2d}. Q6={cl['centroid']} CA={cl['ca_class']} α={cl['alpha']:+d}"
              f"  {cl['size']:3d} записей  {real_str}{fb_str}  [{adapters_str}]")
        for v in cl["vertices"]:
            if v != cl["centroid"]:
                print(f"       ┊  +{v}")
        top_entries = [e for e in cl["entries"] if not e["is_fallback"]][:3]
        for e in top_entries:
            print(f"       · {e['title'][:50]}")

    if len(clusters_list) > 15:
        print(f"  ... и ещё {len(clusters_list) - 15} кластеров")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nautilus Concept Clustering")
    parser.add_argument("--radius", type=int, default=1,
                        help="Hamming-радиус кластеризации (default: 1)")
    parser.add_argument("--query", default="",
                        help="Фильтр: показать кластеры только для этого запроса")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    portal = NautilusPortal()

    if args.query:
        result = portal.query(args.query)
        entries = [
            e for e in result.entries
            if isinstance(e.metadata.get("q6"), str) and len(str(e.metadata.get("q6", ""))) == 6
        ]
        clusters_list = cluster(entries, args.radius)
        data: dict[str, Any] = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_ms": 0,
            "radius": args.radius,
            "query": args.query,
            "total_entries": len(entries),
            "total_clusters": len(clusters_list),
            "ca_breakdown": {},
            "clusters": clusters_list,
        }
    else:
        data = analyze(portal, args.radius)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_report(data)


if __name__ == "__main__":
    main()
