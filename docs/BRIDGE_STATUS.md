# Bridge System — Статус реализации

**Версия:** 2.0  **Дата:** 2026-04-19

---

## Что реализовано

### Паспортная система (12 паспортов)

Каждый паспорт — `.md`-файл в `passports/` с секцией:

```markdown
## Bridges (machine-readable)
```json
[
  {"target": "pro2", "type": "analogy", "description": "...", "confidence": 0.8}
]
```
```

Итого: **33 моста** в 12 паспортах.

### Bridge Algebra v2.0 (`bridge_registry.py`)

| Операция | Метод | Описание |
|----------|-------|---------|
| Инверсия | `invert(bridge)` | A→B становится B→A, confidence × 0.95 |
| Композиция | `compose(ab, bc)` | A→B + B→C = A→C, confidence = min |
| Транзитивное замыкание | `transitive_closure(source, max_hops)` | BFS по графу до N хопов |
| Обнаружение конфликтов | `detect_conflicts(entries)` | Protocol 3: Q6-несоответствия |

### API-эндпоинты

```bash
GET /api/bridge?id=pro2:bidir&hops=2   # обход графа от точки
GET /api/bridge_conflicts              # Protocol 3: список конфликтов
GET /api/bridge_summary               # сводка + transitive closure для всех
```

---

## Статистика по типам мостов

```
analogy      ██████████████████░░  17  (51.5%)
derivation   ██████░░░░░░░░░░░░░░   6  (18.2%)
projection   ████░░░░░░░░░░░░░░░░   4  (12.1%)
embedding    ███░░░░░░░░░░░░░░░░░   3  ( 9.1%)
isomorphism  ███░░░░░░░░░░░░░░░░░   3  ( 9.1%)
```

---

## Покрытие адаптеров мостами

Адаптеры с паспортами и мостами: ai_agents, ai_research, continuum, data2, data7, daten22, graphrag, info1, infosystems, legal, meta, pro2

Без мостов: conversations, sessions (динамические источники, не имеют постоянной семантики).

---

## Известные ограничения

- Мосты объявляются только в паспортах — нет автоматического вывода из содержимого записей
- `detect_conflicts` смотрит только на Q6-несоответствия (Хэмминг > 0); семантические конфликты не проверяются
- Транзитивное замыкание ограничено `max_hops=3` для предотвращения экспоненциального роста
- `compose` создаёт мост типа `derivation` независимо от исходных типов

---

## Следующие шаги

1. Добавить паспорт для `conversations` / `sessions` с временны́ми мостами
2. Реализовать `bridge_path(from_id, to_id)` — кратчайший путь между двумя записями
3. Визуализировать граф мостов в `graph.html` (отдельный слой)
