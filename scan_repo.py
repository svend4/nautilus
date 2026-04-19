#!/usr/bin/env python3
"""
scan_repo.py — автоматический сканер репозитория для Nautilus Portal.

Анализирует структуру GitHub-репо и генерирует:
  - passports/<format>.md
  - adapters/<format>.py

Использование:
    python scan_repo.py owner/myrepo
    python scan_repo.py owner/myrepo --format myformat
    python scan_repo.py owner/myrepo --dry-run        # показать без сохранения
    python scan_repo.py owner/myrepo --output report.json
"""

import json
import os
import re
import sys
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from collections import Counter


# ── Вспомогательные функции ──────────────────────────────────────────────────

def github_get(path: str, token: str = None) -> dict:
    url = f"https://api.github.com{path}"
    headers = {"User-Agent": "nautilus-scanner/1.0",
               "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def fetch_raw(repo: str, path: str, token: str = None) -> str:
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        try:
            headers = {"User-Agent": "nautilus-scanner/1.0"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception:
            continue
    return ""


def extract_description(readme: str) -> str:
    """Первый непустой абзац из README."""
    lines = readme.splitlines()
    paragraphs, current = [], []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    text = paragraphs[0] if paragraphs else ""
    # Убрать markdown-разметку
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    return text[:300]


def guess_q6_key(files: list, fmt: str) -> str:
    """Эвристика для Q6-отображения по типу файлов."""
    exts = Counter(Path(f["path"]).suffix.lower() for f in files)
    dominant = exts.most_common(1)[0][0] if exts else ""
    hints = {
        "meta":  "hex_id - 1 → bin(6)",
        "info1": "alpha + 4 → 3 старших бита Q6",
        "data2": "порядковый номер тома % 64 → bin(6)",
    }
    if fmt in hints:
        return hints[fmt]
    if dominant == ".json":
        return "index % 64 → bin(6)  (уточнить)"
    return "не определено  (заполнить вручную)"


def guess_bridges(fmt: str, files: list) -> dict:
    """Эвристика для мостов на основе ключевых слов."""
    all_names = " ".join(f["path"] for f in files).lower()
    bridges = {}
    if "alpha" in all_names or "level" in all_names:
        bridges["info1"] = "уровень абстракции ↔ α-уровень  (уточнить)"
    if "hex" in all_names or "q6" in all_names or "hexagram" in all_names:
        bridges["meta"] = "категория ↔ гексаграмма  (уточнить)"
    if "concept" in all_names or "knowledge" in all_names or "graph" in all_names:
        bridges["pro2"] = "концепт ↔ Q6-координата  (уточнить)"
    if not bridges:
        bridges["pro2"] = "не определено  (заполнить вручную)"
    return bridges


def make_entry_from_file(repo: str, fmt: str, file_item: dict,
                          index: int, token: str = None) -> dict:
    path = file_item["path"]
    name = Path(path).stem
    # Попытаться прочитать первые 200 символов файла
    content_raw = fetch_raw(repo, path, token)
    content = content_raw[:200].strip().replace("\n", " ") if content_raw else path

    q6_index = index % 64
    q6_bits = format(q6_index, "06b")

    return {
        "id": f"{fmt}:{name[:30]}",
        "title": name.replace("-", " ").replace("_", " ").title(),
        "content": content,
        "type": "document",
        "q6": q6_bits,
        "links": [],
    }


# ── Основной сканер ───────────────────────────────────────────────────────────

def scan_repo(repo: str, fmt: str = None, token: str = None,
              max_entries: int = 5) -> dict:
    print(f"[scan] {repo}")

    # 1. Дерево файлов
    print("[scan] получаем дерево файлов...")
    try:
        tree_data = github_get(f"/repos/{repo}/git/trees/HEAD?recursive=1", token)
        files = [f for f in tree_data.get("tree", []) if f["type"] == "blob"]
    except Exception as e:
        print(f"[scan] ошибка GitHub API: {e}")
        files = []

    # 2. Проверить nautilus.json в репо (Вариант C)
    existing_nautilus = fetch_raw(repo, "nautilus.json", token)
    if existing_nautilus:
        try:
            existing = json.loads(existing_nautilus)
            print(f"[scan] найден nautilus.json в репо (формат={existing.get('format')})")
        except Exception:
            existing = {}
    else:
        existing = {}

    # 3. README
    print("[scan] читаем README...")
    readme = fetch_raw(repo, "README.md", token) or fetch_raw(repo, "readme.md", token)
    description = existing.get("description") or extract_description(readme)

    # 4. Определить формат
    exts = Counter(Path(f["path"]).suffix.lower() for f in files if f["path"].count("/") == 0)
    dominant_ext = exts.most_common(1)[0][0] if exts else ".md"
    ext_to_fmt = {".md": "markdown", ".py": "python", ".json": "json",
                  ".txt": "text", ".yaml": "yaml", ".yml": "yaml"}

    if fmt is None:
        fmt = (existing.get("format")
               or repo.split("/")[-1].replace("-", "_").replace(".", "_"))

    native_unit_map = {
        ".md": "Markdown-документ",
        ".py": "Python-модуль",
        ".json": "JSON-запись",
        ".txt": "текстовый файл",
        ".yaml": "YAML-файл",
    }
    native_unit = existing.get("native_unit") or native_unit_map.get(dominant_ext, "файл")

    # 5. Выбрать примеры файлов
    sample_files = [
        f for f in files
        if f["path"].endswith(dominant_ext)
        and not f["path"].startswith(".")
        and "test" not in f["path"].lower()
    ][:max_entries]

    # 6. Прочитать содержимое примеров
    print(f"[scan] читаем {len(sample_files)} примеров файлов...")
    entries = existing.get("index") or [
        make_entry_from_file(repo, fmt, f, i, token)
        for i, f in enumerate(sample_files)
    ]

    # 7. Метрики
    total = existing.get("total_items") or len(files)
    q6_key = existing.get("q6_key") or guess_q6_key(files, fmt)
    bridges = existing.get("bridges") or guess_bridges(fmt, files)
    compat = existing.get("compatibility", 1)
    examples = existing.get("example_queries", ["knowledge", fmt])

    # 8. Топ расширений
    top_exts = dict(Counter(Path(f["path"]).suffix.lower() for f in files).most_common(5))

    return {
        "repo": repo,
        "format": fmt,
        "native_unit": native_unit,
        "compatibility": compat,
        "description": description,
        "total_items": total,
        "q6_key": q6_key,
        "bridges": bridges,
        "example_queries": examples,
        "adapter_file": f"{fmt}.py",
        "access": {
            "type": existing.get("access", {}).get("type", "github_api"),
            "requires_token": bool(token),
            "fallback": "static_entries",
        },
        "index": entries,
        "_meta": {
            "total_files": len(files),
            "top_extensions": top_exts,
            "dominant_ext": dominant_ext,
            "has_existing_nautilus_json": bool(existing),
        },
    }


# ── Генераторы файлов ─────────────────────────────────────────────────────────

def build_passport_md(data: dict) -> str:
    bridges = data.get("bridges", {})
    if bridges:
        tbl = "| Репо | Связь |\n|------|-------|\n"
        tbl += "".join(f"| `{k}` | {v} |\n" for k, v in bridges.items())
    else:
        tbl = "_Мосты не определены._"

    examples = "\n".join(f"- `{q}`" for q in data.get("example_queries", []))
    token_req = "да (GITHUB_TOKEN)" if data.get("access", {}).get("requires_token") else "нет"

    return f"""# Паспорт: {data['repo']}

| Поле | Значение |
|------|----------|
| Репозиторий | {data['repo']} |
| Формат | `.{data['format']}` — {data['native_unit']} |
| Единица | {data['native_unit']} |
| Адаптер | `adapters/{data['adapter_file']}` |
| Уровень совместимости | {data['compatibility']} |

## Описание

{data.get('description', '_заполнить_')}

## Объём

- Единиц: {data['total_items']}
- Файлов всего: {data['_meta']['total_files']}
- Типы файлов: {', '.join(f"{ext}={n}" for ext, n in data['_meta']['top_extensions'].items())}

## Q6-отображение

{data['q6_key']}

## Мосты к другим репозиториям

{tbl}

## Доступ к данным

- Тип: `{data['access']['type']}`
- Требует токен: {token_req}
- Fallback: {data['access']['fallback']}

## Примеры запросов

{examples}
"""


def build_adapter_py(data: dict) -> str:
    fmt = data["format"]
    cls = "".join(w.capitalize() for w in re.split(r"[_\-]", fmt))
    entries_code = ""
    for item in data.get("index", [])[:5]:
        links_repr = repr(item.get("links", []))
        entries_code += f"""            PortalEntry(
                id={repr(item['id'])},
                title={repr(item['title'])},
                source=self.REPO,
                format_type={repr(item.get('type', 'document'))},
                content={repr(item.get('content', '')[:200])},
                metadata={{"q6": {repr(item.get('q6', ''))}}},
                links={links_repr},
            ),
"""

    return f'''"""
{cls}Adapter — адаптер для {data['repo']}.
Формат: {data['native_unit']}.
Сгенерирован автоматически scan_repo.py — проверьте и дополните.
"""

from .base import BaseAdapter, PortalEntry


class {cls}Adapter(BaseAdapter):
    name = {repr(fmt)}
    REPO = {repr(data['repo'])}

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        results = [
            e for e in self._static_entries()
            if q in e.title.lower() or q in e.content.lower()
        ]
        return results or self._static_entries()[:2]

    def _static_entries(self) -> list[PortalEntry]:
        # TODO: проверить записи, добавить Q6-ссылки, дополнить links
        return [
{entries_code}        ]

    def describe(self) -> dict:
        return {{
            "repo": self.REPO,
            "format": {repr(fmt)},
            "native_unit": {repr(data['native_unit'])},
            "total_items": {repr(data['total_items'])},
            "compatibility": {data['compatibility']},
        }}
'''


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nautilus Repository Scanner")
    parser.add_argument("repo", help="GitHub repo: owner/name")
    parser.add_argument("--format", "-f", help="Имя формата (по умолчанию: имя репо)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показать результат без сохранения файлов")
    parser.add_argument("--output", "-o", help="Сохранить JSON-отчёт в файл")
    parser.add_argument("--token", help="GitHub token (или через GITHUB_TOKEN)")
    parser.add_argument("--max-entries", type=int, default=5,
                        help="Максимум примеров файлов (по умолчанию: 5)")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")

    data = scan_repo(
        repo=args.repo,
        fmt=args.format,
        token=token,
        max_entries=args.max_entries,
    )

    passport_md = build_passport_md(data)
    adapter_py = build_adapter_py(data)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("ПАСПОРТ (passports/{}.md):".format(data["format"]))
        print("=" * 60)
        print(passport_md)
        print("=" * 60)
        print("АДАПТЕР (adapters/{}.py):".format(data["format"]))
        print("=" * 60)
        print(adapter_py)
        return

    # Сохранить файлы
    Path("passports").mkdir(exist_ok=True)
    Path("adapters").mkdir(exist_ok=True)

    passport_path = Path("passports") / f"{data['format']}.md"
    adapter_path = Path("adapters") / f"{data['format']}.py"

    passport_path.write_text(passport_md, encoding="utf-8")
    adapter_path.write_text(adapter_py, encoding="utf-8")

    print(f"\n✅ Паспорт:  {passport_path}")
    print(f"✅ Адаптер:  {adapter_path}")

    if args.output:
        Path(args.output).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✅ Отчёт:    {args.output}")

    fmt = data["format"]
    cls = "".join(w.capitalize() for w in re.split(r"[_\-]", fmt))
    print(f"""
Следующие шаги:
  1. Проверьте adapters/{fmt}.py — заполните _static_entries()
  2. Проверьте passports/{fmt}.md — уточните Q6-отображение и мосты
  3. Добавьте в adapters/__init__.py:
       from .{fmt} import {cls}Adapter
  4. Добавьте в portal.py в NautilusPortal.__init__():
       "{fmt}": {cls}Adapter(),
  5. Запустите:
       python portal.py --describe
       python portal.py --query "test"
""")


if __name__ == "__main__":
    main()
