"""
Daten22Adapter — адаптер для svend4/daten22.
Формат: SQLite FTS4-RAG + 16 архетипов рационализации.
Q6: 101010 (архитектура / системы).
"""

from .base import BaseAdapter, PortalEntry, fuzzy_match

# -----------------------------------------------------------------------
# 16 архетипов рационализации daten22
# -----------------------------------------------------------------------

_ARCHETYPES = [
    ("arch:1",  "Инвентаризация",        "Полный учёт всех элементов системы перед изменением.", "101010"),
    ("arch:2",  "Декомпозиция",          "Разбиение задачи на независимые подзадачи с явными границами.", "101010"),
    ("arch:3",  "Приоритизация",         "Ранжирование задач по критериям ценность/усилие/срочность.", "101010"),
    ("arch:4",  "Параллелизация",        "Одновременное выполнение независимых потоков работы.", "101011"),
    ("arch:5",  "Автоматизация",         "Замена повторяющихся операций программными агентами.", "101011"),
    ("arch:6",  "Кэширование",           "Сохранение промежуточных результатов для повторного использования.", "101010"),
    ("arch:7",  "Обратная связь",        "Замкнутый цикл: действие → измерение → корректировка.", "101010"),
    ("arch:8",  "Абстракция",            "Выделение инвариантного паттерна из конкретных случаев.", "101110"),
    ("arch:9",  "Модульность",           "Разделение на независимые заменяемые модули с чистым интерфейсом.", "101010"),
    ("arch:10", "Версионирование",       "Фиксация состояния системы для откатов и сравнения.", "101000"),
    ("arch:11", "Документирование",      "Явная фиксация намерений, решений, контекста.", "101001"),
    ("arch:12", "Мониторинг",            "Непрерывное наблюдение за ключевыми метриками системы.", "101010"),
    ("arch:13", "Рефакторинг",           "Улучшение структуры без изменения внешнего поведения.", "101010"),
    ("arch:14", "Интеграция",            "Объединение разрозненных компонентов через общий протокол.", "101011"),
    ("arch:15", "Тестирование",          "Верификация поведения через воспроизводимые сценарии.", "101001"),
    ("arch:16", "Итерация",              "Циклическое улучшение через малые проверяемые шаги.", "101010"),
]

# -----------------------------------------------------------------------
# Ключевые концепты daten22
# -----------------------------------------------------------------------

_CONCEPTS = [
    ("daten22:fts4_rag",
     "SQLite FTS4-RAG — локальный семантический поиск",
     "Гибридный поиск: SQLite FTS4 (полнотекстовый) + векторное embedding (RAG). "
     "Работает полностью локально без внешних API. "
     "Индексирует Markdown/текстовые файлы, поддерживает русский и немецкий язык. "
     "Скорость: <100ms на корпусе 10k документов.",
     "101010",
     ["daten22:architecture", "pro2:bidir"],
     ["fts4", "sqlite", "rag", "local", "search"]),

    ("daten22:architecture",
     "Архитектура daten22: Dynamic Planner + AI",
     "Трёхслойная архитектура: (1) Knowledge Layer — SQLite FTS4 индекс, "
     "(2) Planning Layer — динамический планировщик задач с приоритетами, "
     "(3) AI Layer — интеграция с LLM для генерации и оценки планов. "
     "Планировщик использует 16 архетипов рационализации как building blocks.",
     "101010",
     ["daten22:fts4_rag", "daten22:planner", "info1:methodology"],
     ["architecture", "planner", "ai", "layers"]),

    ("daten22:planner",
     "Динамический планировщик (Dynamic Planner)",
     "Планировщик задач с AI-ассистентом: принимает цель → декомпозирует на шаги "
     "→ назначает архетипы → оценивает зависимости → строит DAG выполнения. "
     "Поддерживает re-planning при изменении контекста.",
     "101010",
     ["daten22:architecture", "daten22:archetypes"],
     ["planner", "dag", "task", "ai"]),

    ("daten22:archetypes",
     "16 архетипов рационализации",
     "Набор из 16 паттернов оптимизации: инвентаризация, декомпозиция, приоритизация, "
     "параллелизация, автоматизация, кэширование, обратная связь, абстракция, "
     "модульность, версионирование, документирование, мониторинг, рефакторинг, "
     "интеграция, тестирование, итерация. "
     "Каждый архетип имеет Q6-координату и мост к info1 α-уровням.",
     "101010",
     ["daten22:planner", "info1:methodology", "meta:ca_rules"],
     ["archetypes", "rationalization", "patterns", "16"]),

    ("daten22:rationalization_os",
     "Rationalization OS — операционная система мышления",
     "Концепция daten22: все умственные процессы поддаются рационализации "
     "через применение архетипов. ОС мышления = планировщик + база знаний + "
     "рефлексия. Близко к Building a Second Brain (Forte) но с явной AI-интеграцией.",
     "101010",
     ["daten22:archetypes", "daten22:planner"],
     ["rationalization", "os", "thinking", "pkm"]),
]


class Daten22Adapter(BaseAdapter):
    name = "daten22"
    REPO = "svend4/daten22"

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        results = []

        # Поиск по архетипам
        for aid, name, desc, q6 in _ARCHETYPES:
            if not q or q in name.lower() or q in desc.lower() or fuzzy_match(q, name):
                results.append(PortalEntry(
                    id=f"daten22:{aid}",
                    title=f"Архетип: {name}",
                    source=self.REPO,
                    format_type="concept",
                    content=desc,
                    metadata={"q6": q6, "archetype_id": aid},
                    links=["daten22:daten22:archetypes", "info1:methodology"],
                    is_fallback=not bool(q),
                ))

        # Поиск по концептам
        for cid, title, content, q6, links, tags in _CONCEPTS:
            if not q or q in title.lower() or q in content.lower() or any(q in t for t in tags) or fuzzy_match(q, title):
                results.append(PortalEntry(
                    id=cid,
                    title=title,
                    source=self.REPO,
                    format_type="concept",
                    content=content,
                    metadata={"q6": q6, "tags": tags},
                    links=links,
                    is_fallback=not bool(q),
                ))

        if not results:
            # Fallback: обзорные записи
            fb = [PortalEntry(
                id=cid, title=title, source=self.REPO,
                format_type="concept", content=content,
                metadata={"q6": q6}, links=links, is_fallback=True,
            ) for cid, title, content, q6, links, _ in _CONCEPTS[:2]]
            return fb

        # Без запроса — только концепты, без 16 архетипов по одному
        if not q:
            return [e for e in results if not e.id.startswith("daten22:daten22:")][:6]

        return results[:10]

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "daten22",
            "native_unit": "архетип рационализации / концепт планировщика",
            "q6": "101010",
            "total_archetypes": len(_ARCHETYPES),
            "total_concepts": len(_CONCEPTS),
            "compatibility": 1,
            "description": "SQLite FTS4-RAG + Dynamic Planner + 16 архетипов рационализации",
        }
