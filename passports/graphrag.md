# Паспорт: svend4/infom (GraphRAG)

| Поле | Значение |
|------|----------|
| Репозиторий | svend4/infom |
| Формат | `.graphrag` — граф знаний + community summaries |
| Единица | Узел графа (сущность или концепт) + рёбра |
| Адаптер | `adapters/graphrag.py` |
| Уровень совместимости | 1 — читаемый |

## Архитектура

```
Текст → Entity Extraction → Knowledge Graph → Community Detection
                                                      ↓
                              Summarization (LLM) → Hierarchical Context
                                                      ↓
                              Query Engine (Global / Local) → Answer
```

## Q6-координата

`110001` — семантика / онтология. GraphRAG строит явный семантический граф,
что соответствует онтологическому уровню Q6-пространства.

## Ключевые компоненты

| Компонент | Описание |
|-----------|----------|
| `graph_builder.py` | Entity extraction + knowledge graph |
| `community_detector.py` | Leiden/Louvain clustering |
| `summarizer.py` | LLM-суммаризация communities |
| `query_engine.py` | Global + Local retrieval |

## Мосты к другим репо

| Цель | Связь |
|------|-------|
| pro2 | GraphRAG-узлы ↔ Q6-вершины гиперкуба |
| data7 | graph traversal ↔ K₀→K∞ цикл трансформации |

## Bridges (machine-readable)

```json
[
  {"target": "pro2",  "direction": "↔", "mapping": "GraphRAG graph nodes ↔ Q6 hypercube vertices", "confidence": 0.75, "type": "analogy"},
  {"target": "data7", "direction": "↔", "mapping": "community graph traversal ↔ K₀→K∞ knowledge transformation", "confidence": 0.70, "type": "analogy"}
]
```
