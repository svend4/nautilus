"""
split_sessions.py — разбивка большого файла сессии Claude на тематические документы.

Читает docs/_raw_sessions.md (или другой файл через --input),
разбивает по «# you asked / # claude response» блокам,
группирует по теме и записывает в docs/sessions/*.md.

Каждый выходной файл начинается с YAML-фронтматтера и комментария
о том, как использовать его с Nautilus.

Использование:
  python split_sessions.py
  python split_sessions.py --input docs/my_session.md --out docs/sessions
  python split_sessions.py --list        # только показать темы без записи
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Правила детекции темы
# Порядок важен: первое совпадение побеждает
# ---------------------------------------------------------------------------

_THEME_RULES: list[tuple[str, list[str], str]] = [
    # Порядок критически важен: первое совпадение побеждает.
    # Ищем ключевые слова в (вопрос + первые 800 символов ответа).

    ("anthropic_vacancies", [
        "68 ролей", "150 ролей", "36 ролей", "sales — 150",
        "436 открытых", "ai research & engineering — 68",
        "вилка", "3dnews",
    ], "Вакансии Anthropic по кластерам"),

    ("profile_role_matching", [
        "primary match", "secondary match", "tertiary match",
        "forward deployed engineer", "что не подходит",
        "уникальная ниша", "маппинг профиля",
    ], "Маппинг профиля на роли Anthropic"),

    ("repos_analysis", [
        "naming convention расшифрована", "кластер 1: legal",
        "кластер 2: information", "кластер 3: ai", "кластер 4:",
        "data70", "53 репозитори", "soz", "daten",
        "что на самом деле в data70",
    ], "Анализ 70 GitHub-репозиториев svend4"),

    ("repo_consolidation", [
        "consolidation", "топ-10 репо", "за один weekend",
        "архивировать", "приоритет 1", "целевая картина",
        "финализированный план", "финализированная",
    ], "Стратегия консолидации репозиториев"),

    # --- Nautilus до AI teams, чтобы URL nautilus не путался с MMORPG ---
    ("nautilus_development", [
        "svend4/nautilus", "claude/review-nautilus",
        "implementation_stage", "status.md",
        "ветки с исправлениями", "перенесены в отдельный репозитори",
        "файлы были модифицированн", "файлы были перенесен",
        "наутилус может быть базов", "про два про два",
        "опцию c потом опцию а",
    ], "Разработка Nautilus Portal"),

    ("protocol_spec", [
        "portal-protocol.md", "portal protocol",
        "nautilus portal protocol", "formal specification",
        "w3c/ietf", "version string", "разработать общие план",
        "псевдокод на основе тех",
    ], "PORTAL-PROTOCOL.md v1.1 — формальная спецификация"),

    ("ai_distributed_teams", [
        "вариант c", "terence tao", "polymath",
        "ai-managed", "bounty consortium", "innocentive", "toptal",
        "mmorpg", "ролевых онлайн-игр",
    ], "AI-управляемые команды: тезис + MMORPG-вариант"),

    ("agent_architecture", [
        "мета-агент-координатор",
        "sub-agent", "суб-агент",
        "symbolic guardian", "technical demon",
        "four temperament",
    ], "Архитектура иерархических AI-агентов"),

    ("protocol_broadening", [
        "применимо к гуманитарным", "юридическим документам",
        "короткий ответ\n\nда. nautilus",
        "насчёт приватности", "личные данные",
        "инновация как рационализация",
        "одно не мешает другого", "применим к",
    ], "Протокол за пределами технического: гуманитарное и правовое"),

    ("double_triangle_foundation", [
        "double-triangle", "спрос рождает предложение",
        "если гора не идёт", "guild structure",
        "subsidiarity", "phase 0:", "phase 1:", "phase 2:",
        "call for partnership", "phased rollout", "appendix d",
    ], "Double-Triangle: модель Human-AI коллаборации"),

    ("integral_profile", [
        "интегральный анализ профиля", "интегральный портрет",
        "интегральный ответ", "пять слоёв", "три идентичности",
        "output volume", "distribution problem",
    ], "Интегральный анализ профиля svend4"),
]

_FALLBACK_SLUG = "misc_exchanges"
_FALLBACK_NAME = "Прочие фрагменты"


# ---------------------------------------------------------------------------
# Структура обмена (один вопрос + один ответ)
# ---------------------------------------------------------------------------

class Exchange(NamedTuple):
    question: str
    response: str
    theme_slug: str
    theme_name: str


# ---------------------------------------------------------------------------
# Парсинг файла
# ---------------------------------------------------------------------------

def parse_exchanges(text: str) -> list[Exchange]:
    # Разбиваем по маркеру «# you asked»
    raw_blocks = re.split(r"\n#\s+you asked\s*\n", text)

    exchanges: list[Exchange] = []
    prev_slug = _FALLBACK_SLUG
    prev_name = _FALLBACK_NAME

    for block in raw_blocks[1:]:  # первый элемент — шапка файла
        # Внутри блока ищем «# claude response»
        parts = re.split(r"\n#\s+claude response\s*\n", block, maxsplit=1)
        question = parts[0].strip()
        response = parts[1].strip() if len(parts) > 1 else ""

        # Короткие вопросы («Да», «По порядку», «1.») продолжают предыдущую тему
        # если у них нет собственных ключевых слов
        if len(question) < 50:
            candidate_slug, candidate_name = _detect_theme(response)
            if candidate_slug == _FALLBACK_SLUG:
                slug, name = prev_slug, prev_name
            else:
                slug, name = candidate_slug, candidate_name
        else:
            slug, name = _detect_theme(question + "\n" + response)

        exchanges.append(Exchange(question, response, slug, name))
        prev_slug, prev_name = slug, name

    return exchanges


def _detect_theme(text: str) -> tuple[str, str]:
    # Search in question + first 1200 chars of response for specificity
    tl = text[:4000].lower()
    for slug, keywords, name in _THEME_RULES:
        if any(kw.lower() in tl for kw in keywords):
            return slug, name
    return _FALLBACK_SLUG, _FALLBACK_NAME


# ---------------------------------------------------------------------------
# Группировка по теме
# ---------------------------------------------------------------------------

def group_by_theme(
    exchanges: list[Exchange],
) -> dict[str, tuple[str, list[Exchange]]]:
    groups: dict[str, tuple[str, list[Exchange]]] = {}
    for ex in exchanges:
        if ex.theme_slug not in groups:
            groups[ex.theme_slug] = (ex.theme_name, [])
        groups[ex.theme_slug][1].append(ex)
    return groups


# ---------------------------------------------------------------------------
# Генерация выходного файла с YAML-фронтматтером и комментарием Nautilus
# ---------------------------------------------------------------------------

_NAUTILUS_USAGE = """
<!-- ======================================================================
NAUTILUS INTEGRATION NOTE
========================================================================

Этот файл автоматически индексируется ConversationAdapter (adapters/conversation.py).
Зарегистрируйте папку docs/sessions/ один раз:

    from adapters.conversation import ConversationAdapter
    portal.register("sessions", ConversationAdapter("docs/sessions/"))

После этого файл будет доступен через стандартный API:

    # TF-IDF семантический поиск по всем сессиям:
    python tfidf_search.py --build-index
    python tfidf_search.py "{тема}"

    # REST API (после запуска api.py):
    GET /api/query?q={тема}&ranked=1

    # Консенсус с основной базой знаний:
    portal.query("{концепт}")   # сравнивает с info1, pro2, meta, data2, data7

    # Прямая работа:
    adapter = ConversationAdapter("docs/sessions/")
    results = adapter.fetch("{запрос}")
    for r in results:
        print(r.title, r.metadata["q6"])

======================================================================= -->
"""


def render_file(theme_name: str, exchanges: list[Exchange], slug: str) -> str:
    q6 = _theme_slug_to_q6(slug)
    lines: list[str] = []

    # YAML frontmatter
    lines.append("---")
    lines.append(f'title: "{theme_name}"')
    lines.append(f'slug: "{slug}"')
    lines.append(f'q6: "{q6}"')
    lines.append(f"exchanges: {len(exchanges)}")
    lines.append('source: "claude.ai session export"')
    lines.append("---")
    lines.append("")

    lines.append(f"# {theme_name}")
    lines.append("")
    lines.append(_NAUTILUS_USAGE.strip())
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, ex in enumerate(exchanges, 1):
        lines.append(f"## Обмен {i}")
        lines.append("")
        if ex.question:
            lines.append("**Вопрос:**")
            lines.append("")
            lines.append(ex.question)
            lines.append("")
        if ex.response:
            lines.append("**Ответ:**")
            lines.append("")
            lines.append(ex.response)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _theme_slug_to_q6(slug: str) -> str:
    mapping = {
        "anthropic_vacancies":       "100101",  # анализ/оценка ролей
        "profile_role_matching":     "111110",  # стратегия/синтез
        "repos_analysis":            "100101",  # анализ/кластеры
        "repo_consolidation":        "011010",  # планирование/структура
        "integral_profile":          "111111",  # полный охват
        "alternative_pathways":      "110010",  # навигация/пути
        "ai_distributed_teams":      "110100",  # мультиагент/оркестрация
        "agent_architecture":        "110100",  # мультиагент/оркестрация
        "protocol_spec":             "010101",  # реализация/код
        "nautilus_development":      "101010",  # архитектура/системы
        "protocol_broadening":       "010100",  # концепты/теория
        "double_triangle_foundation":"110001",  # знания/мета/онтология
        "misc_exchanges":            "000000",
    }
    return mapping.get(slug, "000000")


# ---------------------------------------------------------------------------
# Статистика
# ---------------------------------------------------------------------------

def print_stats(groups: dict[str, tuple[str, list[Exchange]]]) -> None:
    total = sum(len(exs) for _, exs in groups.values())
    print(f"\nВсего обменов: {total}")
    print(f"Тем: {len(groups)}\n")
    print(f"{'Тема':<45} {'Обменов':>8}  {'Q6':>8}  Файл")
    print("-" * 80)
    for slug, (name, exs) in sorted(groups.items(), key=lambda x: -len(x[1][1])):
        q6 = _theme_slug_to_q6(slug)
        fname = f"{slug}.md"
        print(f"{name:<45} {len(exs):>8}  {q6:>8}  {fname}")
    print()


# ---------------------------------------------------------------------------
# Запись
# ---------------------------------------------------------------------------

def write_files(
    groups: dict[str, tuple[str, list[Exchange]]],
    out_dir: Path,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug, (name, exs) in groups.items():
        content = render_file(name, exs, slug)
        p = out_dir / f"{slug}.md"
        p.write_text(content, encoding="utf-8")
        written.append(p)
        size_kb = len(content.encode()) // 1024
        print(f"  ✓ {p.name}  ({len(exs)} обменов, {size_kb} КБ)")
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", default="docs/_raw_sessions.md",
        help="Входной файл (default: docs/_raw_sessions.md)",
    )
    parser.add_argument(
        "--out", default="docs/sessions",
        help="Папка для выходных файлов (default: docs/sessions)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Только показать статистику, не записывать файлы",
    )
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Файл не найден: {src}", file=sys.stderr)
        sys.exit(1)

    print(f"Читаю {src} ({src.stat().st_size // 1024} КБ)...")
    text = src.read_text(encoding="utf-8", errors="replace")

    print("Парсинг обменов...")
    exchanges = parse_exchanges(text)
    print(f"Найдено обменов: {len(exchanges)}")

    groups = group_by_theme(exchanges)
    print_stats(groups)

    if args.list:
        return

    out_dir = Path(args.out)
    print(f"Записываю в {out_dir}/")
    written = write_files(groups, out_dir)
    print(f"\nГотово: {len(written)} файлов в {out_dir}/")
    print("\nДля индексации в Nautilus:")
    print("  python tfidf_search.py --build-index")
    print("  python tfidf_search.py 'ваш запрос'")
    print("\nИли через Python:")
    print("  from adapters.conversation import ConversationAdapter")
    print(f"  adapter = ConversationAdapter('{args.out}')")
    print("  results = adapter.fetch('ваш запрос')")


if __name__ == "__main__":
    main()
