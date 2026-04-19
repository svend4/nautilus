#!/usr/bin/env python3
"""
visualize.py — генератор Mermaid-диаграммы экосистемы Nautilus.

Выводит граф адаптеров, их связей и консенсусных покрытий.

Использование:
  python visualize.py                    # Mermaid в stdout
  python visualize.py --format mermaid   # явно mermaid
  python visualize.py --format dot       # Graphviz DOT
  python visualize.py --out diagram.md   # записать в файл
  python visualize.py --query синтез     # граф для конкретного запроса
"""

import argparse
import sys
from collections import defaultdict
from portal import NautilusPortal


def _adapter_color(name: str) -> str:
    palette = {
        "info1": "#1f6feb", "pro2": "#388bfd", "meta": "#8b5cf6",
        "data2": "#10b981", "data7": "#f59e0b", "infosystems": "#ef4444",
        "ai_agents": "#ec4899",
    }
    return palette.get(name, "#6b7280")


def build_graph(portal: NautilusPortal, query: str = "") -> dict:
    """Build adjacency data from cross-links for the given query."""
    queries = [query] if query else ["knowledge", "синтез", "bidir", "agent", "алгоритм"]
    edges = defaultdict(set)
    adapter_stats = {}

    for q in queries:
        result = portal.query(q, ranked=False)
        c = result.consensus or {}
        for link in result.cross_links:
            src = link["from_repo"]
            dst = link["to_repo"]
            if src in portal.adapters and dst in portal.adapters:
                edges[src].add(dst)
        for name in portal.adapters:
            if name not in adapter_stats:
                adapter_stats[name] = {"real": 0, "fallback": 0}
            for e in result.entries:
                if e.id.startswith(name + ":"):
                    if e.is_fallback:
                        adapter_stats[name]["fallback"] += 1
                    else:
                        adapter_stats[name]["real"] += 1

    return {"edges": {k: list(v) for k, v in edges.items()},
            "adapters": adapter_stats}


def to_mermaid(portal: NautilusPortal, query: str = "") -> str:
    graph = build_graph(portal, query)
    edges = graph["edges"]
    stats = graph["adapters"]

    lines = ["graph LR"]

    # Node definitions with labels
    for name in sorted(portal.adapters.keys()):
        s = stats.get(name, {})
        real = s.get("real", 0)
        fb = s.get("fallback", 0)
        label = f"{name}\\n[real={real} fb={fb}]"
        lines.append(f'    {name}["{label}"]')

    lines.append("")

    # Edges
    drawn = set()
    for src, dsts in sorted(edges.items()):
        for dst in sorted(dsts):
            key = tuple(sorted([src, dst]))
            if key not in drawn:
                drawn.add(key)
                # Bidirectional if both directions exist
                if dst in edges and src in edges.get(dst, []):
                    lines.append(f"    {src} <--> {dst}")
                else:
                    lines.append(f"    {src} --> {dst}")

    # Style
    lines.append("")
    lines.append("    %% Adapter colours")
    for name in sorted(portal.adapters.keys()):
        color = _adapter_color(name)
        lines.append(f"    style {name} fill:{color},color:#fff,stroke:#333")

    return "\n".join(lines)


def to_dot(portal: NautilusPortal, query: str = "") -> str:
    graph = build_graph(portal, query)
    edges = graph["edges"]
    stats = graph["adapters"]

    lines = [
        'digraph nautilus {',
        '    rankdir=LR;',
        '    node [shape=box, style=filled, fontname=monospace];',
        '',
    ]

    for name in sorted(portal.adapters.keys()):
        s = stats.get(name, {})
        real = s.get("real", 0)
        fb = s.get("fallback", 0)
        color = _adapter_color(name)
        label = f"{name}\\nreal={real} fb={fb}"
        lines.append(f'    {name} [label="{label}", fillcolor="{color}", fontcolor=white];')

    lines.append("")

    drawn = set()
    for src, dsts in sorted(edges.items()):
        for dst in sorted(dsts):
            key = tuple(sorted([src, dst]))
            if key not in drawn:
                drawn.add(key)
                bidir = dst in edges and src in edges.get(dst, [])
                arrow = ' [dir=both]' if bidir else ''
                lines.append(f'    {src} -> {dst}{arrow};')

    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Nautilus Ecosystem Visualizer")
    parser.add_argument("--format", choices=["mermaid", "dot"], default="mermaid")
    parser.add_argument("--query", "-q", default="")
    parser.add_argument("--out", "-o", help="Output file (default: stdout)")
    args = parser.parse_args()

    portal = NautilusPortal()

    if args.format == "mermaid":
        output = to_mermaid(portal, args.query)
        if not args.out:
            output = f"```mermaid\n{output}\n```"
    else:
        output = to_dot(portal, args.query)

    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"Saved to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
