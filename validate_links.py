#!/usr/bin/env python3
"""
validate_links.py — проверка кросс-ссылок в экосистеме Nautilus.

Собирает все entry.id из всех адаптеров, затем проверяет каждую
ссылку в entry.links. Находит битые ссылки и выводит отчёт.

Использование:
    python validate_links.py              # полная проверка
    python validate_links.py --fix        # показать как исправить
    python validate_links.py --json       # JSON-отчёт
    python validate_links.py --strict     # exit 1 если есть ошибки
"""

import json
import sys
import argparse
from collections import defaultdict
from portal import NautilusPortal


def collect_all_entries(portal: NautilusPortal) -> dict[str, list]:
    """Получить все записи от всех адаптеров по широкому запросу."""
    all_entries = {}
    broad_queries = ["knowledge", "all", "", "синтез", "алгоритм",
                     "agent", "theory", "concept", "data", "rule"]
    for q in broad_queries:
        result = portal.query(q)
        for e in result.entries:
            all_entries[e.id] = e
    return all_entries


def validate(portal: NautilusPortal) -> dict:
    print("Собираем все записи...", end=" ", flush=True)
    entries = collect_all_entries(portal)
    print(f"{len(entries)} записей")

    known_ids = set(entries.keys())

    # Также добавить префиксы-паттерны как "мягкие" цели
    # (некоторые ссылки вида "meta:hexagram:all" — групповые)
    known_prefixes = {e_id.rsplit(":", 1)[0] for e_id in known_ids}

    broken = []
    valid_count = 0
    links_by_adapter = defaultdict(lambda: {"valid": 0, "broken": []})

    for entry_id, entry in entries.items():
        adapter = entry_id.split(":")[0]
        for link in entry.links:
            target_adapter = link.split(":")[0]
            # Ссылка валидна если:
            # 1. Точное совпадение ID
            # 2. Совпадает префикс (групповые ссылки типа "meta:hexagram:all")
            # 3. Целевой адаптер существует (минимальная проверка)
            is_exact = link in known_ids
            is_prefix = link in known_prefixes
            is_adapter_known = target_adapter in portal.adapters

            if is_exact or is_prefix:
                valid_count += 1
                links_by_adapter[adapter]["valid"] += 1
            elif is_adapter_known:
                # Адаптер есть, но конкретная запись не найдена
                broken.append({
                    "link": link,
                    "source": entry_id,
                    "adapter_exists": True,
                    "severity": "warning",
                    "note": f"адаптер '{target_adapter}' есть, запись '{link}' не найдена",
                })
                links_by_adapter[adapter]["broken"].append(link)
            else:
                broken.append({
                    "link": link,
                    "source": entry_id,
                    "adapter_exists": False,
                    "severity": "error",
                    "note": f"адаптер '{target_adapter}' не зарегистрирован",
                })
                links_by_adapter[adapter]["broken"].append(link)

    errors = [b for b in broken if b["severity"] == "error"]
    warnings = [b for b in broken if b["severity"] == "warning"]

    return {
        "total_entries": len(entries),
        "total_links": valid_count + len(broken),
        "valid_links": valid_count,
        "broken": broken,
        "errors": len(errors),
        "warnings": len(warnings),
        "by_adapter": dict(links_by_adapter),
        "ok": len(errors) == 0,
    }


def print_report(report: dict, show_fix: bool = False):
    total = report["total_links"]
    valid = report["valid_links"]
    errors = report["errors"]
    warnings = report["warnings"]

    print(f"\n⬡ Nautilus Link Validation")
    print("=" * 50)
    print(f"Записей:       {report['total_entries']}")
    print(f"Ссылок всего:  {total}")
    print(f"Корректных:    {valid}  ✅")
    print(f"Ошибок:        {errors}  {'❌' if errors else '✅'}")
    print(f"Предупрежд.:   {warnings}  {'⚠️' if warnings else '✅'}")

    if not report["broken"]:
        print("\n✅ Все ссылки корректны")
        return

    # Группировать по серьёзности
    for severity, label in [("error", "ОШИБКИ"), ("warning", "ПРЕДУПРЕЖДЕНИЯ")]:
        items = [b for b in report["broken"] if b["severity"] == severity]
        if not items:
            continue
        print(f"\n{'❌' if severity == 'error' else '⚠️ '} {label} ({len(items)}):")
        for b in items:
            print(f"  {b['link']}")
            print(f"    └─ источник: {b['source']}")
            print(f"    └─ {b['note']}")
            if show_fix:
                adapter = b["link"].split(":")[0]
                print(f"    💡 Добавить запись с id='{b['link']}' в адаптер '{adapter}'")
                print(f"       или удалить ссылку из записи '{b['source']}'")

    print(f"\nПо адаптерам:")
    for adapter, stats in sorted(report["by_adapter"].items()):
        broken_count = len(stats["broken"])
        status = f"⚠️  {broken_count} битых" if broken_count else "✅"
        print(f"  {adapter:15s}: {stats['valid']} ок  {status}")


def main():
    parser = argparse.ArgumentParser(description="Nautilus Link Validator")
    parser.add_argument("--fix", action="store_true", help="Показать подсказки по исправлению")
    parser.add_argument("--json", action="store_true", help="JSON-вывод")
    parser.add_argument("--strict", action="store_true", help="Exit 1 если есть ошибки")
    args = parser.parse_args()

    portal = NautilusPortal()
    report = validate(portal)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report, show_fix=args.fix)

    if args.strict and not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
