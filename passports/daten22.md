# Паспорт: svend4/daten22

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/daten22 |
| Формат | `.daten22` — SQLite FTS4-RAG + архетипы рационализации |
| Единица | Архетип рационализации / концепт планировщика |
| Адаптер | `adapters/daten22.py` |
| Уровень совместимости | 1 — читаемый |

## Архитектура

Три слоя:
1. **Knowledge Layer** — SQLite FTS4-индекс + vector embeddings
2. **Planning Layer** — Dynamic Planner, строит DAG из 16 архетипов
3. **AI Layer** — LLM-интеграция для генерации и оценки планов

## 16 архетипов рационализации

Инвентаризация · Декомпозиция · Приоритизация · Параллелизация · Автоматизация ·
Кэширование · Обратная связь · Абстракция · Модульность · Версионирование ·
Документирование · Мониторинг · Рефакторинг · Интеграция · Тестирование · Итерация

## Q6-координата

`101010` — архитектура / системы. Rationalization OS = системное мышление.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| info1 | архетипы рационализации ↔ α-уровни методологии |
| pro2 | FTS4-RAG ↔ bidir_train KnowledgeGraph |
| continuum | Dynamic Planner ↔ Continuum DAG выполнения |

## Bridges (machine-readable)

```json
[
  {"target": "info1",    "direction": "↔", "mapping": "rationalization archetypes ↔ α-level methodology", "confidence": 0.70, "type": "analogy"},
  {"target": "pro2",     "direction": "↔", "mapping": "FTS4-RAG local index ↔ bidir_train KnowledgeGraph", "confidence": 0.65, "type": "analogy"},
  {"target": "continuum","direction": "↔", "mapping": "Dynamic Planner DAG ↔ Continuum execution DAG", "confidence": 0.80, "type": "analogy"}
]
```
