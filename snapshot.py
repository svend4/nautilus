#!/usr/bin/env python3
"""
snapshot.py — статический экспорт всей экосистемы Nautilus.

Генерирует:
  snapshot.json        — полный JSON-дамп всех записей и связей
  snapshot.md          — Markdown-отчёт для GitHub Pages / README
  ecosystem_stats.json — статистика (используется sync.yml)

Использование:
  python snapshot.py                          # всё
  python snapshot.py --json                   # только snapshot.json
  python snapshot.py --md                     # только snapshot.md
  python snapshot.py --stats                  # только ecosystem_stats.json
  python snapshot.py --out-dir docs/          # другая директория
"""

import json
import time
import argparse
from pathlib import Path
from collections import defaultdict
from portal import NautilusPortal
from health_check import check_adapters, check_passports, check_consensus, score


QUERIES = [
    "knowledge", "синтез", "bidir", "agent", "алгоритм",
    "theory", "concept", "data", "rule", "design",
]


def collect_all(portal: NautilusPortal) -> dict:
    entries_map = {}
    cross_links_all = []
    seen_links = set()

    for q in QUERIES:
        result = portal.query(q, ranked=False)
        for e in result.entries:
            if e.id not in entries_map:
                entries_map[e.id] = e
        for lnk in result.cross_links:
            key = tuple(sorted([lnk["from"], lnk["to"]]))
            if key not in seen_links:
                seen_links.add(key)
                cross_links_all.append(lnk)

    return {"entries": entries_map, "cross_links": cross_links_all}


def build_snapshot(portal: NautilusPortal) -> dict:
    data = collect_all(portal)
    entries = list(data["entries"].values())
    adapter_stats = defaultdict(lambda: {"total": 0, "real": 0, "fallback": 0, "q6": 0})
    for e in entries:
        src = e.id.split(":")[0]
        adapter_stats[src]["total"] += 1
        if e.is_fallback:
            adapter_stats[src]["fallback"] += 1
        else:
            adapter_stats[src]["real"] += 1
        if e.metadata.get("q6"):
            adapter_stats[src]["q6"] += 1

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_entries": len(entries),
        "total_cross_links": len(data["cross_links"]),
        "adapters": {k: dict(v) for k, v in adapter_stats.items()},
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "source": e.source,
                "format_type": e.format_type,
                "content": e.content[:500],
                "metadata": e.metadata,
                "links": e.links,
                "is_fallback": e.is_fallback,
            }
            for e in sorted(entries, key=lambda e: e.id)
        ],
        "cross_links": sorted(data["cross_links"],
                              key=lambda l: (l["from_repo"], l["to_repo"])),
    }


def build_stats(portal: NautilusPortal) -> dict:
    adapter_r = check_adapters(portal)
    passport_r = check_passports()
    consensus_r = check_consensus(portal)
    sc, issues = score(adapter_r, passport_r, consensus_r)
    data = collect_all(portal)
    entries = data["entries"]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "score": sc,
        "ok": sc >= 70,
        "total_entries": len(entries),
        "total_cross_links": len(data["cross_links"]),
        "adapters_count": len(portal.adapters),
        "issues": issues,
        "coverage_knowledge": consensus_r.get("knowledge", {}).get("coverage_real", 0),
        "adapters": {
            name: {
                "ok": r.get("ok", False),
                "entries_real": r.get("entries_real", 0),
                "entries_fallback": r.get("entries_fallback", 0),
                "has_q6": r.get("has_q6", False),
                "response_ms": r.get("response_ms", 0),
            }
            for name, r in adapter_r.items()
        },
    }


def build_markdown(portal: NautilusPortal, snap: dict, stats: dict) -> str:
    sc = stats["score"]
    bar = "█" * (sc // 5) + "░" * (20 - sc // 5)
    color_badge = "brightgreen" if sc >= 80 else "yellow" if sc >= 50 else "red"
    ts = snap["generated_at"]

    lines = [
        "# ⬡ Nautilus Ecosystem Snapshot",
        "",
        f"![health](https://img.shields.io/badge/health-{sc}%25-{color_badge})",
        f"![entries](https://img.shields.io/badge/entries-{snap['total_entries']}-blue)",
        f"![links](https://img.shields.io/badge/cross--links-{snap['total_cross_links']}-blue)",
        "",
        f"*Generated: {ts}*",
        "",
        f"**Score: {sc}/100** `[{bar}]`",
        "",
        "## Adapters",
        "",
        "| Adapter | Entries (real) | Entries (fallback) | Q6 | Links |",
        "|---------|---------------|-------------------|----|----|",
    ]
    for name, st in sorted(stats["adapters"].items()):
        q6 = "✓" if st.get("has_q6") else "✗"
        ok = "✅" if st.get("ok") else "❌"
        lines.append(
            f"| {ok} {name} | {st.get('entries_real', 0)} | "
            f"{st.get('entries_fallback', 0)} | {q6} | "
            f"{st.get('response_ms', 0)}ms |"
        )

    lines += [
        "",
        "## Cross-Adapter Links (sample)",
        "",
    ]
    for lnk in snap["cross_links"][:20]:
        lines.append(f"- `{lnk['from']}` → `{lnk['to']}` ({lnk['from_repo']} ↔ {lnk['to_repo']})")

    if stats.get("issues"):
        lines += ["", "## Issues", ""]
        for issue in stats["issues"]:
            lines.append(f"- {issue}")

    lines += [
        "",
        "## Ecosystem Graph",
        "",
        "```mermaid",
    ]
    from visualize import to_mermaid
    lines.append(to_mermaid(portal))
    lines += ["```", ""]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Nautilus Snapshot Generator")
    parser.add_argument("--json", action="store_true", help="Generate snapshot.json only")
    parser.add_argument("--md", action="store_true", help="Generate snapshot.md only")
    parser.add_argument("--stats", action="store_true", help="Generate ecosystem_stats.json only")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    portal = NautilusPortal()
    all_modes = not (args.json or args.md or args.stats)

    snap = None
    stats = None

    if args.json or args.md or all_modes:
        print("Building full snapshot...", flush=True)
        snap = build_snapshot(portal)

    if args.stats or args.md or all_modes:
        print("Computing ecosystem stats...", flush=True)
        stats = build_stats(portal)

    if args.json or all_modes:
        p = out / "snapshot.json"
        p.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
        print(f"✅ {p}  ({snap['total_entries']} entries, {snap['total_cross_links']} links)")

    if args.stats or all_modes:
        p = out / "ecosystem_stats.json"
        p.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
        print(f"✅ {p}  (score={stats['score']})")

    if args.md or all_modes:
        md = build_markdown(portal, snap, stats)
        p = out / "snapshot.md"
        p.write_text(md)
        print(f"✅ {p}")


if __name__ == "__main__":
    main()
