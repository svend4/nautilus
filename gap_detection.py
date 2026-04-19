#!/usr/bin/env python3
"""
gap_detection.py — поиск белых пятен в Q6-пространстве экосистемы Nautilus.

Анализирует покрытие 64 вершин Q6-гиперкуба {0,1}^6 и выдаёт:
  - вершины без единой записи (gap)
  - вершины с только fallback-записями (weak coverage)
  - кластеры пустых вершин (structural gaps)
  - рекомендации: какой CA-класс недопредставлен

Использование:
    python gap_detection.py              # текстовый отчёт
    python gap_detection.py --json       # JSON-вывод
    python gap_detection.py --strict     # exit 1 если есть полные пробелы
    python gap_detection.py --top 10     # показать 10 крупнейших кластеров
"""

import json
import sys
import argparse
from collections import defaultdict
from portal import NautilusPortal


QUERIES = [
    "knowledge", "синтез", "bidir", "agent", "алгоритм",
    "theory", "concept", "data", "rule", "design",
    "котёл", "архетип", "мир", "петля", "резонанс",
]

CA_CLASS_NAMES = {"I": "Стационарные", "II": "Периодические",
                  "III": "Хаотические",  "IV": "Сложные (край хаоса)"}

# Mapping hex_id → CA class (from meta adapter data)
HEX_CA = {
    1: "I", 2: "I", 3: "II", 4: "II", 5: "II", 6: "III", 7: "II", 8: "II",
    9: "II", 10: "II", 11: "II", 12: "III", 14: "II", 19: "II", 21: "II",
    23: "III", 24: "IV", 29: "III", 30: "III", 41: "II", 42: "II",
    49: "IV", 50: "IV", 51: "III", 52: "I", 53: "II", 54: "II",
    57: "II", 58: "II", 63: "IV", 64: "IV",
}


def bits_to_hex_id(bits: str) -> int:
    return int(bits, 2) + 1


def ca_class_of(bits: str) -> str:
    hex_id = bits_to_hex_id(bits)
    return HEX_CA.get(hex_id, "II")  # default II for unmapped


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def collect_coverage(portal: NautilusPortal) -> dict[str, dict]:
    """Returns {bits: {"real": int, "fallback": int, "adapters": set}}"""
    coverage: dict[str, dict] = {
        format(i, "06b"): {"real": 0, "fallback": 0, "adapters": set()}
        for i in range(64)
    }

    for q in QUERIES:
        result = portal.query(q, ranked=False)
        for e in result.entries:
            q6 = e.metadata.get("q6", "")
            if not q6 or not isinstance(q6, str) or len(q6) != 6 or not all(c in "01" for c in q6):
                continue
            adapter = e.id.split(":")[0]
            if e.is_fallback:
                coverage[q6]["fallback"] += 1
            else:
                coverage[q6]["real"] += 1
            coverage[q6]["adapters"].add(adapter)

    return coverage


def find_gap_clusters(gaps: list[str]) -> list[list[str]]:
    """Group gap vertices by Hamming-1 adjacency into clusters."""
    gap_set = set(gaps)
    visited = set()
    clusters = []

    for start in gaps:
        if start in visited:
            continue
        cluster = []
        queue = [start]
        while queue:
            node = queue.pop()
            if node in visited:
                continue
            visited.add(node)
            cluster.append(node)
            for b in range(6):
                flipped = list(node)
                flipped[b] = "1" if node[b] == "0" else "0"
                neighbor = "".join(flipped)
                if neighbor in gap_set and neighbor not in visited:
                    queue.append(neighbor)
        clusters.append(sorted(cluster))

    return sorted(clusters, key=len, reverse=True)


def analyze(portal: NautilusPortal) -> dict:
    coverage = collect_coverage(portal)

    gaps = []          # no entries at all
    weak = []          # only fallback
    covered = []       # has real entries

    for bits, data in coverage.items():
        if data["real"] == 0 and data["fallback"] == 0:
            gaps.append(bits)
        elif data["real"] == 0:
            weak.append(bits)
        else:
            covered.append(bits)

    total = 64
    gap_clusters = find_gap_clusters(gaps)

    # CA-class breakdown
    ca_breakdown: dict[str, dict] = {c: {"total": 0, "covered": 0, "weak": 0, "gap": 0}
                                      for c in ("I", "II", "III", "IV")}
    for bits in coverage:
        ca = ca_class_of(bits)
        ca_breakdown[ca]["total"] += 1
        if bits in covered:
            ca_breakdown[ca]["covered"] += 1
        elif bits in weak:
            ca_breakdown[ca]["weak"] += 1
        else:
            ca_breakdown[ca]["gap"] += 1

    # Recommendations: CA classes with worst coverage
    recommendations = []
    for ca, stats in sorted(ca_breakdown.items(),
                             key=lambda x: x[1]["gap"] / max(x[1]["total"], 1),
                             reverse=True):
        gap_pct = stats["gap"] / max(stats["total"], 1) * 100
        if gap_pct > 0:
            recommendations.append(
                f"Класс {ca} ({CA_CLASS_NAMES[ca]}): "
                f"{stats['gap']}/{stats['total']} вершин без покрытия ({gap_pct:.0f}%)"
            )

    # Top gap neighbors — vertices adjacent to coverage that would extend it best
    covered_set = set(covered)
    gap_priority: dict[str, int] = {}
    for gap in gaps:
        neighbors_covered = sum(
            1 for b in range(6)
            for neighbor in ["".join(
                "1" if gap[b] == "0" else "0" if i == b else gap[i]
                for i in range(6)
            )]
            if neighbor in covered_set
        )
        gap_priority[gap] = neighbors_covered

    priority_gaps = sorted(gaps, key=lambda g: gap_priority.get(g, 0), reverse=True)

    return {
        "total_vertices": total,
        "covered": len(covered),
        "weak": len(weak),
        "gaps": len(gaps),
        "coverage_pct": round(len(covered) / total * 100, 1),
        "weak_pct": round(len(weak) / total * 100, 1),
        "gap_pct": round(len(gaps) / total * 100, 1),
        "gap_vertices": gaps,
        "weak_vertices": weak,
        "covered_vertices": covered,
        "gap_clusters": gap_clusters,
        "ca_breakdown": ca_breakdown,
        "recommendations": recommendations,
        "priority_gaps": priority_gaps[:10],
    }


def print_report(data: dict, top: int = 5):
    cov = data["covered"]
    weak = data["weak"]
    gaps = data["gaps"]
    total = data["total_vertices"]

    bar_cov = "█" * int(cov / total * 20)
    bar_weak = "▒" * int(weak / total * 20)
    bar_gap = "░" * int(gaps / total * 20)

    print(f"\n⬡ Nautilus Q6 Gap Detection Report")
    print("=" * 52)
    print(f"Вершин всего:    {total} (6D гиперкуб)")
    print(f"Покрыто (real):  {cov:3d}  {data['coverage_pct']}%  {bar_cov}")
    print(f"Слабые (fb):     {weak:3d}  {data['weak_pct']}%  {bar_weak}")
    print(f"Пробелы (gap):   {gaps:3d}  {data['gap_pct']}%  {bar_gap}")
    print()

    print("── CA-классы ─────────────────────────────────────────")
    for ca, stats in data["ca_breakdown"].items():
        name = CA_CLASS_NAMES[ca]
        cov_n = stats["covered"]
        wk_n = stats["weak"]
        gp_n = stats["gap"]
        tot = stats["total"]
        bar = "█" * cov_n + "▒" * wk_n + "░" * gp_n
        print(f"  {ca} {name:25s}: {cov_n}/{tot} real  {wk_n} weak  {gp_n} gap  [{bar}]")

    if data["gap_clusters"]:
        print()
        print("── Кластеры пробелов ─────────────────────────────────")
        for i, cluster in enumerate(data["gap_clusters"][:top]):
            ca_dist = defaultdict(int)
            for bits in cluster:
                ca_dist[ca_class_of(bits)] += 1
            ca_str = " ".join(f"{c}:{n}" for c, n in sorted(ca_dist.items()))
            print(f"  Кластер {i+1}: {len(cluster)} вершин  [{ca_str}]")
            for bits in cluster[:4]:
                hex_id = bits_to_hex_id(bits)
                print(f"    · {bits}  (hex #{hex_id})")
            if len(cluster) > 4:
                print(f"    · ... ещё {len(cluster)-4}")

    if data["priority_gaps"]:
        print()
        print("── Приоритетные пробелы (ближе всего к покрытию) ────")
        for bits in data["priority_gaps"][:8]:
            neighbors = gap_priority_score(bits, set(data["covered_vertices"]))
            hex_id = bits_to_hex_id(bits)
            ca = ca_class_of(bits)
            print(f"  {bits}  hex#{hex_id}  класс {ca}  (покрытых соседей: {neighbors})")

    if data["recommendations"]:
        print()
        print("── Рекомендации ──────────────────────────────────────")
        for r in data["recommendations"]:
            print(f"  ⚠️  {r}")

    print()


def gap_priority_score(bits: str, covered_set: set) -> int:
    count = 0
    for b in range(6):
        flipped = list(bits)
        flipped[b] = "1" if bits[b] == "0" else "0"
        if "".join(flipped) in covered_set:
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Nautilus Q6 Gap Detection")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 если gap_pct > 50%")
    parser.add_argument("--top", type=int, default=5,
                        help="Число кластеров для показа")
    args = parser.parse_args()

    portal = NautilusPortal()
    data = analyze(portal)

    # Make serializable
    data_out = {k: (list(v) if isinstance(v, set) else v) for k, v in data.items()}
    for bits in data_out.get("covered_vertices", []):
        pass  # already lists

    if args.json:
        print(json.dumps(data_out, ensure_ascii=False, indent=2))
    else:
        print_report(data, top=args.top)

    if args.strict and data["gap_pct"] > 50:
        sys.exit(1)


if __name__ == "__main__":
    main()
