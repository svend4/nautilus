# Паспорт: svend4/soz150 (Writing OS / Legal)

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/soz150 |
| Формат | `.legal` — юридические инструменты, шаблоны документов |
| Единица | Юридический инструмент / правовой документ |
| Адаптер | `adapters/legal.py` |
| Уровень совместимости | 1 — читаемый |

## Содержимое

- 300+ JavaScript-инструментов для создания юридических документов
- Покрытие: немецкое социальное право (SGB II, XII, IX), жилищное право, DSGVO
- Форматы вывода: Markdown, DOCX, PDF
- Языки: немецкий (основной), частично английский

## Humanities Extension

Этот адаптер поддерживает расширенные metadata-поля (Humanities Extension):

| Поле | Тип | Описание |
|------|-----|---------|
| `jurisdiction` | string | Юрисдикция (DE, AT, EU, ...) |
| `valid_from` | date | Дата вступления в силу |
| `language` | string | Язык документа (ISO 639-1) |
| `gdpr_contains_personal_data` | bool | Содержит ли персональные данные |

## Q6-координата

`100010` — анализ / правила / право.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| info1 | правовые уровни сложности ↔ α-уровни |
| daten22 | юридические шаблоны ↔ документальные архетипы |

## Bridges (machine-readable)

```json
[
  {"target": "info1",  "direction": "→", "mapping": "legal complexity levels → α-level abstraction", "confidence": 0.60, "type": "analogy"},
  {"target": "daten22","direction": "↔", "mapping": "legal document templates ↔ documentation archetype", "confidence": 0.65, "type": "analogy"}
]
```
