# Паспорт: домен ai_agents (внутри svend4/pro2)

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/pro2 (домен) |
| Формат | Агентные паттерны — стратегии, циклы, curriculum |
| Единица | Агентный паттерн |
| Адаптер | `adapters/ai_agents.py` |
| Уровень совместимости | 2 — связанный |

## Ключевые агенты

| Агент | Файл | Тип |
|-------|------|-----|
| self_train | `self_train.py` | 3-стадийное самообучение |
| bidir | `bidir_train.py` | Двунаправленный (forward + backward loop) |
| AdvancedGenerator | `inference/bridge_inference.py` | 5 стратегий генерации |
| HMoE curriculum | `train_hmoe_curriculum.py` | 5-фазное обучение экспертов |
| NautilusHierarchy | `geometry/nautilus.py` | 7-камерная иерархия |

## Паттерн: Двунаправленный агент

```
Forward:  KnowledgeGraph → PageRank → концепты → train batch
Backward: generate → filter → evaluate → update graph
```

Цикл замкнут: граф направляет обучение, обучение обогащает граф.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| pro2 | все агенты реализованы в pro2 |
| data7 | bidir реализует недостающую петлю K₀→K∞ |
| infosystems | KnowledgeGraph — общий для обоих доменов |

## Bridges (machine-readable)

```json
[
  {"target": "pro2",        "direction": "←", "mapping": "all agent implementations reside in pro2", "confidence": 1.00, "type": "embedding"},
  {"target": "data7",       "direction": "→", "mapping": "bidir_train implements the missing K₀→K∞ loop described in data7", "confidence": 0.90, "type": "derivation"},
  {"target": "infosystems", "direction": "↔", "mapping": "KnowledgeGraph is shared infrastructure for both ai_agents and infosystems domains", "confidence": 1.00, "type": "embedding"}
]
```
