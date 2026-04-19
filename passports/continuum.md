# Паспорт: svend4/meta1 (Continuum)

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/meta1 |
| Формат | `.continuum` — детерминированный AI-рантайм |
| Единица | Step (атомарная единица выполнения) |
| Адаптер | `adapters/continuum.py` |
| Уровень совместимости | 1 — читаемый |

## Концепция

Continuum решает проблему недетерминизма в AI-агентах: явный state machine
гарантирует воспроизводимость каждого шага. Snapshot/restore позволяет
откатиться в любое предыдущее состояние.

## Единица данных

```python
Step = (
    input_state:  dict,    # полный контекст на входе
    action:       str,     # тип шага: LLM_CALL | TOOL_USE | BRANCH | MERGE
    output_state: dict,    # полный контекст на выходе
    metadata:     dict,    # timestamp, cost, tokens, duration
)
```

## Q6-координата

`110100` — мультиагент / оркестрация.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| daten22 | Dynamic Planner DAG ↔ Continuum execution DAG |
| ai_agents | AI-агенты Nautilus ↔ Continuum Steps |
| ai_research | Agentic Workflow паттерны ↔ Continuum типы шагов |

## Bridges (machine-readable)

```json
[
  {"target": "daten22",    "direction": "↔", "mapping": "Continuum execution DAG ↔ daten22 Dynamic Planner DAG", "confidence": 0.80, "type": "analogy"},
  {"target": "ai_agents",  "direction": "↔", "mapping": "Continuum Steps ↔ Nautilus AI-agent execution units", "confidence": 0.75, "type": "analogy"},
  {"target": "ai_research","direction": "↔", "mapping": "Continuum step types ↔ Agentic Workflow patterns", "confidence": 0.80, "type": "analogy"}
]
```
