#!/usr/bin/env python3
"""
health_check.py — отчёт о состоянии экосистемы Nautilus Portal.

Использование:
    python health_check.py              # текстовый отчёт
    python health_check.py --json       # JSON для CI/badges
    python health_check.py --strict     # exit 1 при критических проблемах
"""

import json
import sys
import time
import argparse
from pathlib import Path
from portal import NautilusPortal


def check_adapters(portal: NautilusPortal) -> dict:
    results = {}
    for name, adapter in portal.adapters.items():
        t0 = time.monotonic()
        try:
            entries = adapter.fetch("knowledge")
            elapsed = time.monotonic() - t0
            real = [e for e in entries if not e.is_fallback]
            results[name] = {
                "ok": True,
                "entries_total": len(entries),
                "entries_real": len(real),
                "entries_fallback": len(entries) - len(real),
                "has_q6": any(e.metadata.get("q6") for e in entries),
                "has_links": any(e.links for e in entries),
                "response_ms": round(elapsed * 1000),
            }
        except Exception as ex:
            results[name] = {"ok": False, "error": str(ex)}
    return results


def check_passports() -> dict:
    passport_dir = Path("passports")
    registry_path = Path("nautilus.json")
    results = {}

    if not registry_path.exists():
        return {"error": "nautilus.json не найден"}

    registry = json.loads(registry_path.read_text())
    registered = {e.get("adapter") for e in registry.get("registry", [])}

    for fmt in registered:
        passport_file = passport_dir / f"{fmt}.md"
        if not passport_file.exists():
            results[fmt] = {"exists": False}
            continue
        content = passport_file.read_text()
        required = ["Репозиторий", "Формат", "Адаптер", "Уровень совместимости"]
        missing = [f for f in required if f not in content]
        has_q6 = "Q6" in content or "q6" in content
        has_bridges = "Мосты" in content or "Bridges" in content
        results[fmt] = {
            "exists": True,
            "missing_fields": missing,
            "has_q6": has_q6,
            "has_bridges": has_bridges,
            "size_lines": content.count("\n"),
        }
    return results


def check_consensus(portal: NautilusPortal) -> dict:
    test_queries = {
        "knowledge": {"expected_min_coverage": 0.5},
        "синтез":    {"expected_min_coverage": 0.3},
        "bidir":     {"expected_min_coverage": 0.2},
    }
    results = {}
    for query, expectations in test_queries.items():
        result = portal.query(query)
        c = result.consensus or {}
        results[query] = {
            "coverage_real":     c.get("coverage", 0),
            "coverage_fallback": c.get("coverage_with_fallback", 0),
            "present_real":      c.get("present_in", []),
            "present_fallback":  c.get("present_in_fallback", []),
            "missing":           c.get("missing_in", []),
            "entries":           len(result.entries),
            "cross_links":       len(result.cross_links),
            "ok": c.get("coverage", 0) >= expectations["expected_min_coverage"],
        }
    return results


def check_cache() -> dict:
    try:
        from adapters.cache import CacheManager
        cm = CacheManager()
        cached = cm.list_cached()
        return {
            "cached_repos": len(cached),
            "repos": cached,
        }
    except Exception as ex:
        return {"error": str(ex)}


def score(adapter_results, passport_results, consensus_results) -> tuple[int, list]:
    """Возвращает (score 0-100, список проблем)."""
    issues = []
    points = 100

    # Адаптеры
    failed = [n for n, r in adapter_results.items() if not r.get("ok")]
    if failed:
        issues.append(f"❌ Адаптеры не отвечают: {', '.join(failed)}")
        points -= len(failed) * 10

    no_real = [n for n, r in adapter_results.items()
               if r.get("ok") and r.get("entries_real", 0) == 0]
    if no_real:
        issues.append(f"⚠️  Только fallback-записи: {', '.join(no_real)}")
        points -= len(no_real) * 3

    no_q6 = [n for n, r in adapter_results.items()
             if r.get("ok") and not r.get("has_q6")]
    if no_q6:
        issues.append(f"⚠️  Нет Q6-координат: {', '.join(no_q6)}")
        points -= len(no_q6) * 2

    # Паспорта
    missing_passports = [f for f, r in passport_results.items() if not r.get("exists")]
    if missing_passports:
        issues.append(f"❌ Паспорта отсутствуют: {', '.join(missing_passports)}")
        points -= len(missing_passports) * 5

    incomplete = [f for f, r in passport_results.items()
                  if r.get("exists") and r.get("missing_fields")]
    if incomplete:
        issues.append(f"⚠️  Неполные паспорта: {', '.join(incomplete)}")
        points -= len(incomplete) * 2

    # Консенсус
    low_consensus = [q for q, r in consensus_results.items() if not r.get("ok")]
    if low_consensus:
        issues.append(f"⚠️  Низкий консенсус: {', '.join(low_consensus)}")
        points -= len(low_consensus) * 3

    return max(0, points), issues


def print_report(data: dict):
    adapters = data["adapters"]
    passports = data["passports"]
    consensus = data["consensus"]
    cache = data["cache"]
    sc = data["score"]
    issues = data["issues"]

    bar = "█" * (sc // 5) + "░" * (20 - sc // 5)
    color = "✅" if sc >= 80 else "⚠️ " if sc >= 50 else "❌"

    print(f"\n⬡ Nautilus Ecosystem Health Report")
    print(f"{'=' * 50}")
    print(f"Дата:    {data['timestamp']}")
    print(f"Оценка:  {color} {sc}/100  [{bar}]")
    print()

    print("── Адаптеры ──────────────────────────────────────")
    for name, r in sorted(adapters.items()):
        if not r.get("ok"):
            print(f"  ❌ {name:15s}  ERROR: {r.get('error','?')}")
            continue
        real = r['entries_real']
        fallback = r['entries_fallback']
        q6 = "Q6✓" if r['has_q6'] else "Q6✗"
        lnk = "links✓" if r['has_links'] else "links✗"
        ms = r['response_ms']
        print(f"  ✅ {name:15s}  real={real}  fallback={fallback}  {q6}  {lnk}  {ms}ms")

    print()
    print("── Паспорта ───────────────────────────────────────")
    for fmt, r in sorted(passports.items()):
        if not r.get("exists"):
            print(f"  ❌ {fmt:15s}  ОТСУТСТВУЕТ")
            continue
        missing = r.get("missing_fields", [])
        q6 = "Q6✓" if r['has_q6'] else "Q6✗"
        br = "bridges✓" if r['has_bridges'] else "bridges✗"
        status = "⚠️ " if missing else "✅"
        detail = f"  (нет: {', '.join(missing)})" if missing else ""
        print(f"  {status} {fmt:15s}  {r['size_lines']} строк  {q6}  {br}{detail}")

    print()
    print("── Консенсус ──────────────────────────────────────")
    for query, r in consensus.items():
        real_pct = int(r['coverage_real'] * 100)
        fb_pct = int(r['coverage_fallback'] * 100)
        status = "✅" if r['ok'] else "⚠️ "
        present = ', '.join(r['present_real']) or '—'
        print(f"  {status} \"{query:15s}\"  real={real_pct}%  +fallback={fb_pct}%"
              f"  entries={r['entries']}  xlinks={r['cross_links']}")
        if r['missing']:
            print(f"     отсутствует: {', '.join(r['missing'])}")

    print()
    print("── Кэш ────────────────────────────────────────────")
    if "error" in cache:
        print(f"  ⚠️  {cache['error']}")
    else:
        print(f"  Закэшировано репо: {cache['cached_repos']}")
        for repo_info in cache.get("repos", []):
            fresh = "свежий" if repo_info['fresh'] else "устаревший ⚠️"
            print(f"    · {repo_info['repo']:30s}  {repo_info['age_hours']}ч  {fresh}")

    if issues:
        print()
        print("── Проблемы ───────────────────────────────────────")
        for issue in issues:
            print(f"  {issue}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Nautilus Health Check")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 если score < 70 или есть ❌ ошибки")
    args = parser.parse_args()

    portal = NautilusPortal()

    adapter_results  = check_adapters(portal)
    passport_results = check_passports()
    consensus_results = check_consensus(portal)
    cache_results    = check_cache()
    sc, issues       = score(adapter_results, passport_results, consensus_results)

    data = {
        "timestamp":  time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "score":      sc,
        "issues":     issues,
        "adapters":   adapter_results,
        "passports":  passport_results,
        "consensus":  consensus_results,
        "cache":      cache_results,
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_report(data)

    if args.strict and (sc < 70 or any("❌" in i for i in issues)):
        sys.exit(1)


if __name__ == "__main__":
    main()
