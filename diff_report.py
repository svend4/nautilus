#!/usr/bin/env python3
"""
diff_report.py — отчёт об изменениях с момента последней синхронизации.

Сравнивает текущее состояние экосистемы (записи от всех адаптеров)
с сохранённым снимком (snapshot). Показывает:
  - новые записи (появились в текущем состоянии)
  - удалённые записи (были в снимке, исчезли сейчас)
  - изменившиеся записи (title, content или links изменились)
  - изменения Q6-покрытия (какие координаты добавились/исчезли)

Использование:
    python diff_report.py                      # отчёт с последним снимком
    python diff_report.py --baseline snap.json # использовать конкретный снимок
    python diff_report.py --save               # сохранить текущее состояние как новый снимок
    python diff_report.py --json               # JSON-вывод
"""

import json
import sys
import time
import argparse
from pathlib import Path
from typing import Any, cast

from portal import NautilusPortal

_SNAPSHOT_DIR = Path("snapshots")
_DEFAULT_BASELINE = _SNAPSHOT_DIR / "latest_diff_baseline.json"


def _collect_current(portal: NautilusPortal) -> dict[str, Any]:
    """Собрать все текущие записи в словарь id → snapshot-запись."""
    entries: dict[str, Any] = {}
    broad = ["", "knowledge", "синтез", "алгоритм", "agent", "theory",
             "concept", "data", "rule", "all"]
    for q in broad:
        result = portal.query(q, ranked=False)
        for e in result.entries:
            entries[e.id] = {
                "id": e.id,
                "title": e.title,
                "content": e.content[:300],
                "source": e.source,
                "format_type": e.format_type,
                "q6": e.metadata.get("q6", ""),
                "links": sorted(e.links),
                "is_fallback": e.is_fallback,
            }
    return entries


def _load_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return cast(dict[str, Any], data.get("entries", {}))
    except Exception:
        return {}


def _save_baseline(entries: dict[str, Any]) -> Path:
    _SNAPSHOT_DIR.mkdir(exist_ok=True)
    payload = {
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(entries),
        "entries": entries,
    }
    _DEFAULT_BASELINE.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return _DEFAULT_BASELINE


def _entry_changed(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Return list of changed field names between two entry snapshots."""
    changes = []
    for field in ("title", "content", "links", "is_fallback", "q6"):
        if old.get(field) != new.get(field):
            changes.append(field)
    return changes


def diff(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Compute diff between current and baseline entry sets."""
    current_ids = set(current)
    baseline_ids = set(baseline)

    added_ids = current_ids - baseline_ids
    removed_ids = baseline_ids - current_ids
    common_ids = current_ids & baseline_ids

    changed: list[dict[str, Any]] = []
    for eid in sorted(common_ids):
        fields = _entry_changed(baseline[eid], current[eid])
        if fields:
            changed.append({
                "id": eid,
                "changed_fields": fields,
                "old": {f: baseline[eid].get(f) for f in fields},
                "new": {f: current[eid].get(f) for f in fields},
            })

    # Q6 coverage diff
    old_q6 = {v.get("q6") for v in baseline.values() if v.get("q6") and not v.get("is_fallback")}
    new_q6 = {v.get("q6") for v in current.values() if v.get("q6") and not v.get("is_fallback")}
    q6_added = sorted(new_q6 - old_q6)
    q6_removed = sorted(old_q6 - new_q6)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_current": len(current),
            "total_baseline": len(baseline),
            "added": len(added_ids),
            "removed": len(removed_ids),
            "changed": len(changed),
            "unchanged": len(common_ids) - len(changed),
        },
        "added": [current[i] for i in sorted(added_ids)],
        "removed": [baseline[i] for i in sorted(removed_ids)],
        "changed": changed,
        "q6_coverage": {
            "added_vertices": q6_added,
            "removed_vertices": q6_removed,
            "net_change": len(q6_added) - len(q6_removed),
        },
    }


def print_report(report: dict[str, Any]) -> None:
    s = report["summary"]
    q6 = report["q6_coverage"]
    print(f"\n⬡ Nautilus Diff Report")
    print(f"{'=' * 54}")
    print(f"Дата:     {report['generated_at']}")
    print(f"Текущих:  {s['total_current']}  Базовых: {s['total_baseline']}")
    print()

    print(f"── Изменения записей ─────────────────────────────────")
    print(f"  ✅ Без изменений:  {s['unchanged']}")
    if s["added"]:
        print(f"  ➕ Новых:          {s['added']}")
    if s["removed"]:
        print(f"  ➖ Удалённых:      {s['removed']}")
    if s["changed"]:
        print(f"  ✏️  Изменённых:    {s['changed']}")

    if report["added"]:
        print()
        print("── Новые записи ──────────────────────────────────────")
        for e in report["added"][:15]:
            q6_tag = f"  Q6={e['q6']}" if e.get("q6") else ""
            print(f"  + {e['id']:40s}{q6_tag}")
        if len(report["added"]) > 15:
            print(f"  ... и ещё {len(report['added']) - 15}")

    if report["removed"]:
        print()
        print("── Удалённые записи ──────────────────────────────────")
        for e in report["removed"][:10]:
            print(f"  - {e['id']}")
        if len(report["removed"]) > 10:
            print(f"  ... и ещё {len(report['removed']) - 10}")

    if report["changed"]:
        print()
        print("── Изменённые записи ─────────────────────────────────")
        for c in report["changed"][:10]:
            fields = ", ".join(c["changed_fields"])
            print(f"  ~ {c['id']:40s}  [{fields}]")
            for f in c["changed_fields"]:
                old_val = str(c["old"].get(f, ""))[:60]
                new_val = str(c["new"].get(f, ""))[:60]
                if old_val != new_val:
                    print(f"      {f}: «{old_val}» → «{new_val}»")
        if len(report["changed"]) > 10:
            print(f"  ... и ещё {len(report['changed']) - 10}")

    if q6["added_vertices"] or q6["removed_vertices"]:
        print()
        print("── Q6-покрытие ───────────────────────────────────────")
        if q6["added_vertices"]:
            print(f"  ➕ Новые вершины Q6: {', '.join(q6['added_vertices'])}")
        if q6["removed_vertices"]:
            print(f"  ➖ Утерянные вершины: {', '.join(q6['removed_vertices'])}")
        net = q6["net_change"]
        sign = "+" if net >= 0 else ""
        print(f"  Δ покрытие: {sign}{net} вершин")
    else:
        print()
        print("── Q6-покрытие: без изменений ────────────────────────")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nautilus Diff Report")
    parser.add_argument("--baseline", help="Путь к файлу базового снимка")
    parser.add_argument("--save", action="store_true",
                        help="Сохранить текущее состояние как новый базовый снимок")
    parser.add_argument("--json", action="store_true", help="JSON-вывод")
    args = parser.parse_args()

    portal = NautilusPortal()

    print("Собираем текущие записи...", end=" ", flush=True)
    current = _collect_current(portal)
    print(f"{len(current)} записей")

    if args.save:
        path = _save_baseline(current)
        print(f"✅ Базовый снимок сохранён: {path}  ({len(current)} записей)")
        return

    baseline_path = Path(args.baseline) if args.baseline else _DEFAULT_BASELINE
    if not baseline_path.exists():
        print(f"ℹ️  Базовый снимок не найден: {baseline_path}")
        print("  Запустите с --save чтобы создать базовый снимок.")
        # Show current state as "all new"
        baseline: dict[str, Any] = {}
    else:
        baseline = _load_baseline(baseline_path)
        print(f"Базовый снимок: {baseline_path}  ({len(baseline)} записей)")

    report = diff(current, baseline)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
