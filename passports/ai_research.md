# Паспорт: svend4/info3+info4+info30+info100 (AI Research)

| Поле | Значение |
|------|----------|
| Репозитории | svend4/info3, svend4/info4, svend4/info30, svend4/info100 |
| Формат | `.ai_research` — методология AI-агентов |
| Единица | Агентный паттерн / концепт методологии |
| Адаптер | `adapters/ai_research.py` |
| Уровень совместимости | 1 — читаемый |

## Источники и распределение

| Репо | Тема | Концептов |
|------|------|:---------:|
| info3 | Базовые паттерны: ReAct, CoT, ToT | 3 |
| info4 | MAS архитектуры, Tool Use, Function Calling | 3 |
| info30 | MCTS, Self-Reflection, оптимизация | 2 |
| info100 | Memory, Agentic Workflow, синтез | 3 |

## Охваченные паттерны

ReAct · Chain-of-Thought · Tree-of-Thoughts · Multi-Agent Systems ·
Tool Use · Function Calling · MCTS · Self-Reflection ·
Agent Memory (4 типа) · Agentic Workflow (4 паттерна)

## Q6-координата

`110100` — мультиагент / оркестрация.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| ai_agents | паттерны из литературы ↔ реализации в pro2 |
| continuum | Agentic Workflow ↔ Continuum step types |
| graphrag | Agent Memory (external) ↔ GraphRAG retrieval |

## Bridges (machine-readable)

```json
[
  {"target": "ai_agents",  "direction": "↔", "mapping": "research agent patterns ↔ pro2 agent implementations", "confidence": 0.75, "type": "analogy"},
  {"target": "continuum",  "direction": "↔", "mapping": "Agentic Workflow patterns ↔ Continuum step types", "confidence": 0.80, "type": "analogy"},
  {"target": "graphrag",   "direction": "→", "mapping": "Agent Memory (external long-term) → GraphRAG retrieval backend", "confidence": 0.70, "type": "derivation"}
]
```
