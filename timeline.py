#!/usr/bin/env python3
"""
timeline.py — временная шкала обновлений экосистемы Nautilus.

Показывает:
  - когда каждый адаптер/кэш последний раз обновлялся
  - свежесть записей (по метаданным published/updated)
  - историю sync (по git-логу)
  - рекомендации: что устарело и требует обновления

Использование:
    python timeline.py              # текстовый отчёт
    python timeline.py --json       # JSON-вывод
    python timeline.py --html       # HTML-шкала (stdout)
"""

import json
import os
import subprocess
import sys
import time
import argparse
from pathlib import Path
from adapters.cache import CacheManager

_cache = CacheManager()
STALE_HOURS = 24 * 7  # 7 дней → устаревший


def _git_log(n: int = 20) -> list[dict]:
    """Get last N commits touching ecosystem files."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%H|%ai|%s",
             "--", "adapters/", "passports/", "nautilus.json",
             "health_check.py", "portal.py"],
            capture_output=True, text=True, cwd=Path(__file__).parent
        )
        entries = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                entries.append({
                    "hash": parts[0][:8],
                    "date": parts[1][:19],
                    "message": parts[2],
                })
        return entries
    except Exception:
        return []


def _cache_freshness() -> list[dict]:
    """Get freshness info for all cached repos."""
    items = []
    try:
        for info in _cache.list_cached():
            age_h = info.get("age_hours", 0)
            items.append({
                "repo": info["repo"],
                "age_hours": age_h,
                "fresh": info.get("fresh", False),
                "status": "fresh" if age_h < 24 else "stale" if age_h > STALE_HOURS else "aging",
                "last_fetched": info.get("fetched_at", ""),
            })
    except Exception:
        pass
    return sorted(items, key=lambda x: x["age_hours"])


def _passport_freshness() -> list[dict]:
    """Get modification times of passport files."""
    passport_dir = Path("passports")
    items = []
    if not passport_dir.exists():
        return items
    now = time.time()
    for f in sorted(passport_dir.glob("*.md")):
        mtime = f.stat().st_mtime
        age_h = (now - mtime) / 3600
        items.append({
            "name": f.stem,
            "path": str(f),
            "age_hours": round(age_h, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            "status": "fresh" if age_h < 24 else "stale" if age_h > STALE_HOURS else "aging",
        })
    return items


def _adapter_file_freshness() -> list[dict]:
    """Check modification times of adapter .py files."""
    adapters_dir = Path("adapters")
    now = time.time()
    items = []
    for f in sorted(adapters_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        mtime = f.stat().st_mtime
        age_h = (now - mtime) / 3600
        items.append({
            "name": f.stem,
            "age_hours": round(age_h, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            "status": "fresh" if age_h < 24 else "aging",
        })
    return sorted(items, key=lambda x: x["age_hours"])


def collect() -> dict:
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cache_entries": _cache_freshness(),
        "passports": _passport_freshness(),
        "adapter_files": _adapter_file_freshness(),
        "git_log": _git_log(15),
    }


def _age_bar(age_hours: float, width: int = 20) -> str:
    max_age = STALE_HOURS
    fill = max(0, min(width, int((1 - age_hours / max_age) * width)))
    color = "█" if age_hours < 24 else "▒" if age_hours < STALE_HOURS else "░"
    return color * fill + "░" * (width - fill)


def print_report(data: dict):
    print(f"\n⬡ Nautilus Timeline Report")
    print(f"{'=' * 54}")
    print(f"Дата: {data['generated_at']}")

    # Git log
    log = data.get("git_log", [])
    if log:
        print()
        print("── Git история (экосистемные файлы) ─────────────────")
        for entry in log[:8]:
            print(f"  {entry['date']}  {entry['hash']}  {entry['message'][:50]}")

    # Cache
    cache_items = data.get("cache_entries", [])
    if cache_items:
        print()
        print("── Кэш адаптеров ────────────────────────────────────")
        for item in cache_items:
            bar = _age_bar(item["age_hours"])
            status_icon = "✅" if item["status"] == "fresh" else "⚠️ " if item["status"] == "aging" else "❌"
            print(f"  {status_icon} {item['repo']:35s}  {item['age_hours']:6.1f}ч  [{bar}]")
    else:
        print("\n── Кэш: пуст (репо ещё не загружались) ─────────────")

    # Adapter files
    adapter_items = data.get("adapter_files", [])
    if adapter_items:
        print()
        print("── Файлы адаптеров ──────────────────────────────────")
        for item in adapter_items:
            bar = _age_bar(item["age_hours"])
            print(f"  {'✅' if item['age_hours'] < 48 else '·'}  {item['name']:20s}  {item['modified']}  [{bar}]")

    # Passports
    passport_items = data.get("passports", [])
    if passport_items:
        print()
        print("── Паспорта ─────────────────────────────────────────")
        for item in passport_items:
            bar = _age_bar(item["age_hours"])
            icon = "✅" if item["status"] == "fresh" else "⚠️ "
            print(f"  {icon} {item['name']:20s}  {item['modified']}  [{bar}]")

    # Recommendations
    stale_cache = [i for i in cache_items if i["status"] == "stale"]
    stale_pass = [i for i in passport_items if i["status"] == "stale"]
    if stale_cache or stale_pass:
        print()
        print("── Рекомендации ─────────────────────────────────────")
        for i in stale_cache:
            print(f"  ⚠️  Кэш устарел: {i['repo']} ({i['age_hours']:.0f}ч)")
        for i in stale_pass:
            print(f"  ⚠️  Паспорт устарел: {i['name']} ({i['age_hours']:.0f}ч)")

    print()


def render_html(data: dict) -> str:
    items = (data.get("cache_entries", []) +
             data.get("passport_items", []) +
             data.get("adapter_files", []))
    log = data.get("git_log", [])

    rows = ""
    for item in data.get("adapter_files", []):
        age = item["age_hours"]
        pct = max(0, min(100, int((1 - age / STALE_HOURS) * 100)))
        color = "#3fb950" if age < 24 else "#d29922" if age < STALE_HOURS else "#f85149"
        rows += f"""
        <tr>
          <td>{item['name']}</td>
          <td>{item['modified']}</td>
          <td><div style="width:{pct}%;height:8px;background:{color};border-radius:4px"></div></td>
        </tr>"""

    log_rows = "".join(
        f"<tr><td>{e['date']}</td><td><code>{e['hash']}</code></td>"
        f"<td>{e['message'][:60]}</td></tr>"
        for e in log[:10]
    )

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>⬡ Nautilus Timeline</title>
<style>
  body{{font-family:monospace;background:#0d1117;color:#c9d1d9;padding:20px}}
  h1{{color:#58a6ff}} table{{border-collapse:collapse;width:100%;margin:16px 0}}
  th,td{{padding:6px 12px;border:1px solid #30363d;text-align:left;font-size:13px}}
  th{{background:#161b22;color:#8b949e}} tr:hover{{background:#161b2288}}
  h2{{color:#8b949e;font-size:14px;margin:24px 0 8px}}
</style>
</head><body>
<h1>⬡ Nautilus Timeline</h1>
<p style="color:#8b949e">Сгенерировано: {data['generated_at']}</p>
<h2>Файлы адаптеров</h2>
<table><tr><th>Адаптер</th><th>Последнее изменение</th><th>Свежесть</th></tr>
{rows}
</table>
<h2>Git история</h2>
<table><tr><th>Дата</th><th>Хэш</th><th>Сообщение</th></tr>
{log_rows}
</table>
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Nautilus Timeline")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()

    data = collect()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.html:
        print(render_html(data))
    else:
        print_report(data)


if __name__ == "__main__":
    main()
