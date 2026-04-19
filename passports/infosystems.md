# Паспорт: домен infosystems (внутри svend4/pro2)

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/pro2 (домен) |
| Формат | Архитектуры, онтологии, схемы данных |
| Единица | Граф знаний / онтология / доменная модель |
| Адаптер | `adapters/infosystems.py` |
| Уровень совместимости | 2 — связанный |

## Ключевые компоненты

| Компонент | Файл | Описание |
|-----------|------|----------|
| KnowledgeGraph | `bidir_train.py` | Граф с PageRank-центральностью |
| DomainMoE | `geometry/ffn.py` | Маршрутизация по 6 доменам |
| Q6-онтология | — | 64 гексаграммы как категориальная система |
| Корпус (6+1 доменов) | `data/svend4_corpus/` | Учебные данные по доменам |

## Q6-онтология

64 вершины гиперкуба `{-1,+1}^6` = универсальная категориальная система.  
Метрика: Хэмминг. Навигация: BianGuaTransform.

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| pro2 | KnowledgeGraph, DomainMoE живут в pro2 |
| data7 | Q6-онтология ↔ K₀→K∞ цикл |
| meta | 64 гексаграммы ↔ 64 вершины Q6 |

## Bridges (machine-readable)

```json
[
  {"target": "pro2",  "direction": "←", "mapping": "KnowledgeGraph and DomainMoE are implemented inside pro2", "confidence": 1.00, "type": "embedding"},
  {"target": "data7", "direction": "↔", "mapping": "Q6-ontology (64 vertices) ↔ K₀→K∞ transformation cycle", "confidence": 0.75, "type": "analogy"},
  {"target": "meta",  "direction": "↔", "mapping": "64 hexagrams ↔ 64 Q6 hypercube vertices", "confidence": 0.95, "type": "isomorphism"}
]
```
