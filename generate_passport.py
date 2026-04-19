"""
generate_passport.py — генератор паспортов для Nautilus Portal.

Использование:
  python generate_passport.py                    # интерактивный режим
  python generate_passport.py --repo svend4/myrepo --format myformat
  python generate_passport.py --validate passports/info1.md
  python generate_passport.py --list             # список всех паспортов
"""

import json
import argparse
import sys
from pathlib import Path


PASSPORT_TEMPLATE_MD = """\
# Паспорт: {repo}

| Поле | Значение |
|------|----------|
| Репозиторий | {repo} |
| Формат | `.{format}` — {native_unit} |
| Единица | {native_unit} |
| Адаптер | `adapters/{adapter_file}` |
| Уровень совместимости | {compatibility} — {compat_label} |

## Описание

{description}

## Объём

- Единиц: {total_items}
{abstraction_line}

## Q6-отображение

{q6_key}

## Мосты к другим репозиториям

{bridges_table}

## Как получить данные

- Тип доступа: `{access_type}`
- Требует токен: {requires_token}
- Fallback: {fallback}

## Примеры запросов

{example_queries}
"""

COMPAT_LABELS = {
    0: "обнаруживаемый",
    1: "читаемый",
    2: "связанный",
    3: "интерактивный",
}

ADAPTER_TEMPLATE = """\
\"\"\"
{format_upper}Adapter — адаптер для {repo}.
Формат: {native_unit}.
\"\"\"

from .base import BaseAdapter, PortalEntry


class {format_upper}Adapter(BaseAdapter):
    name = "{format}"
    REPO = "{repo}"

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        results = self._static_entries()
        if q not in ("", "all", "knowledge"):
            results = [e for e in results if q in e.title.lower() or q in e.content.lower()]
        return results or self._static_entries()[:2]

    def _static_entries(self) -> list[PortalEntry]:
        # TODO: заменить на реальный поиск по репозиторию
        return [
            PortalEntry(
                id="{format}:overview",
                title="{repo} — обзор",
                source=self.REPO,
                format_type="document",
                content="{description}",
                metadata={{}},
                links=[],
            ),
        ]

    def describe(self) -> dict:
        return {{
            "repo": self.REPO,
            "format": "{format}",
            "native_unit": "{native_unit}",
            "compatibility": {compatibility},
        }}
"""


def ask(prompt: str, default: str = "") -> str:
    val = input(f"{prompt}{' [' + default + ']' if default else ''}: ").strip()
    return val or default


def interactive_mode() -> dict:
    print("\n⬡ Nautilus Passport Generator")
    print("=" * 40)
    print("Заполните поля паспорта (Enter = пропустить/использовать дефолт)\n")

    data = {}
    data["repo"] = ask("GitHub repo (owner/name)")
    if not data["repo"] or "/" not in data["repo"]:
        print("Ошибка: укажите repo в формате owner/name")
        sys.exit(1)

    data["format"] = ask("Формат (короткое имя)", data["repo"].split("/")[-1])
    data["native_unit"] = ask("Атомарная единица", "Markdown-документ")
    data["description"] = ask("Краткое описание")

    print("\nУровни совместимости:")
    for k, v in COMPAT_LABELS.items():
        print(f"  {k} — {v}")
    compat_str = ask("Уровень совместимости", "1")
    data["compatibility"] = int(compat_str)

    data["total_items"] = ask("Количество единиц", "?")
    data["abstraction_range"] = ask("Диапазон абстракции", "")
    data["q6_key"] = ask("Q6-отображение", "не определено")

    print("\nМосты к другим репозиториям (Enter чтобы завершить):")
    bridges = {}
    while True:
        repo_target = ask("  Целевой репо (пусто = завершить)", "")
        if not repo_target:
            break
        link_desc = ask(f"  Связь с {repo_target}")
        bridges[repo_target] = link_desc
    data["bridges"] = bridges

    data["access"] = {
        "type": ask("Тип доступа", "static"),
        "requires_token": ask("Требует токен? (yes/no)", "no").lower() == "yes",
        "fallback": ask("Fallback если данные недоступны", "static_entries"),
    }

    examples_str = ask("Примеры запросов (через запятую)", "knowledge")
    data["example_queries"] = [e.strip() for e in examples_str.split(",")]

    data["adapter_file"] = f"{data['format']}.py"
    return data


def build_md(data: dict) -> str:
    bridges = data.get("bridges", {})
    if bridges:
        bridges_table = "| Репо | Связь |\n|------|-------|\n"
        bridges_table += "".join(f"| `{k}` | {v} |\n" for k, v in bridges.items())
    else:
        bridges_table = "_Мосты не определены._"

    abstraction_line = (
        f"- Диапазон абстракции: {data['abstraction_range']}"
        if data.get("abstraction_range")
        else ""
    )

    access = data.get("access", {})
    example_list = "\n".join(f"- `{q}`" for q in data.get("example_queries", []))

    return PASSPORT_TEMPLATE_MD.format(
        repo=data["repo"],
        format=data["format"],
        native_unit=data["native_unit"],
        adapter_file=data.get("adapter_file", f"{data['format']}.py"),
        compatibility=data["compatibility"],
        compat_label=COMPAT_LABELS.get(data["compatibility"], ""),
        description=data.get("description", ""),
        total_items=data.get("total_items", "?"),
        abstraction_line=abstraction_line,
        q6_key=data.get("q6_key", "не определено"),
        bridges_table=bridges_table,
        access_type=access.get("type", "static"),
        requires_token="да" if access.get("requires_token") else "нет",
        fallback=access.get("fallback", "static_entries"),
        example_queries=example_list,
    )


def build_adapter(data: dict) -> str:
    fmt = data["format"]
    return ADAPTER_TEMPLATE.format(
        format=fmt,
        format_upper=fmt.capitalize(),
        repo=data["repo"],
        native_unit=data.get("native_unit", ""),
        description=data.get("description", ""),
        compatibility=data["compatibility"],
    )


def validate_passport(path: str):
    schema_path = Path(__file__).parent / "passport_schema.json"
    if not schema_path.exists():
        print("passport_schema.json не найден")
        return

    content = Path(path).read_text(encoding="utf-8")
    required_fields = ["Репозиторий", "Формат", "Адаптер", "Уровень совместимости"]
    missing = [f for f in required_fields if f not in content]
    if missing:
        print(f"⚠️  Возможно отсутствуют поля: {', '.join(missing)}")
    else:
        print(f"✅ {path} — базовая структура в порядке")


def list_passports():
    passport_dir = Path(__file__).parent / "passports"
    if not passport_dir.exists():
        print("Директория passports/ не найдена")
        return
    files = sorted(passport_dir.glob("*.md"))
    print(f"Паспортов в репозитории: {len(files)}")
    for f in files:
        print(f"  · {f.name}")


def main():
    parser = argparse.ArgumentParser(description="Nautilus Passport Generator")
    parser.add_argument("--repo", help="GitHub repo (owner/name)")
    parser.add_argument("--format", dest="fmt", help="Формат репозитория")
    parser.add_argument("--validate", metavar="FILE", help="Проверить паспорт")
    parser.add_argument("--list", action="store_true", help="Список паспортов")
    parser.add_argument("--json", action="store_true", help="Вывести JSON вместо MD")
    parser.add_argument("--adapter", action="store_true", help="Также сгенерировать адаптер")
    args = parser.parse_args()

    if args.list:
        list_passports()
        return

    if args.validate:
        validate_passport(args.validate)
        return

    if args.repo:
        data = {
            "repo": args.repo,
            "format": args.fmt or args.repo.split("/")[-1],
            "native_unit": "документ",
            "description": "",
            "compatibility": 1,
            "total_items": "?",
            "q6_key": "не определено",
            "bridges": {},
            "access": {"type": "static", "requires_token": False, "fallback": "static_entries"},
            "example_queries": ["knowledge"],
            "adapter_file": f"{args.fmt or args.repo.split('/')[-1]}.py",
        }
    else:
        data = interactive_mode()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    md = build_md(data)
    out_path = Path("passports") / f"{data['format']}.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"✅ Паспорт сохранён: {out_path}")

    if args.adapter:
        adapter_code = build_adapter(data)
        adapter_path = Path("adapters") / f"{data['format']}.py"
        adapter_path.write_text(adapter_code, encoding="utf-8")
        print(f"✅ Адаптер сохранён: {adapter_path}")
        print(f"\nДобавьте в adapters/__init__.py:")
        fmt_cap = data['format'].capitalize()
        print(f"  from .{data['format']} import {fmt_cap}Adapter")


if __name__ == "__main__":
    main()
