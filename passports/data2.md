# Паспорт: svend4/data2

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/data2 |
| Формат | `.data2` — тома ЕТД (Единая Теория Движения) |
| Единица | Том (Markdown, номер + домен) |
| Адаптер | `adapters/data2.py` |
| Уровень совместимости | 1 — читаемый |

## Содержимое

310+ томов в 5 сериях (I–V+), 326 файлов.

12 архетипов движения: петля · три сферы · нечётность · 7±2 · шахматка · резонанс · lci · синтез · ката · ...

Ключевой алгоритм: `scarab_algorithm.py` — обход Q6-пространства по траектории фигуры-8.

## Метрика системы

LCI (Loop Closure Index) — степень замкнутости системы движения.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| pro2 | scarab_algorithm ↔ Q6-траектория |
| meta | архетипы ↔ CA-классы |
| info1 | серия тома ↔ α-уровень |

## Bridges (machine-readable)

```json
[
  {"target": "pro2",  "direction": "→", "mapping": "scarab_algorithm → Q6-trajectory traversal", "confidence": 0.75, "type": "derivation"},
  {"target": "meta",  "direction": "↔", "mapping": "ETD movement archetypes ↔ CA-classes", "confidence": 0.70, "type": "analogy"},
  {"target": "info1", "direction": "→", "mapping": "volume series (I–V+) → α-level depth", "confidence": 0.65, "type": "projection"}
]
```
