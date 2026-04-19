# ⬡ Nautilus Portal

**Единая точка входа для экосистемы svend4** · v1.2

> Не слияние — совместимость.  
> Как Office Suite читает `.docx`, `.pdf`, `.xlsx` не сливая их в один формат —  
> Nautilus читает все репозитории экосистемы, находит связи, строит общий вид.

[![CI](https://github.com/svend4/nautilus/actions/workflows/ci.yml/badge.svg)](https://github.com/svend4/nautilus/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-60%20passed-brightgreen)
![mypy](https://img.shields.io/badge/mypy-clean-brightgreen)
![Links](https://img.shields.io/badge/links-317%20valid-brightgreen)
![Adapters](https://img.shields.io/badge/adapters-14-blue)
![Bridges](https://img.shields.io/badge/bridges-33-purple)

---

## Репозитории экосистемы

| Репо | Формат | Что хранит | Q6 |
|------|--------|-----------|:---:|
| [svend4/info1](https://github.com/svend4/info1) | `.info1` | 74+ Markdown-документа, α-уровни −4..+4 | 100001 |
| [svend4/pro2](https://github.com/svend4/pro2) | `.pro2` | Q6-концепты, граф знаний, bidir-цикл | 110011 |
| [svend4/meta](https://github.com/svend4/meta) | `.meta` | 256 CA-правил + 64 гексаграммы И-Цзин | 000100 |
| [svend4/data2](https://github.com/svend4/data2) | `.data2` | 310+ томов ЕТД (Единая Теория Движения) | 001000 |
| [svend4/data7](https://github.com/svend4/data7) | `.data7` | Граф знаний, K₀→K∞ трансформация | 110001 |
| [svend4/infom](https://github.com/svend4/infom) | GraphRAG | Knowledge graph + community detection | 110001 |
| [svend4/daten22](https://github.com/svend4/daten22) | daten22 | SQLite FTS4-RAG + 16 архетипов рационализации | 101010 |
| [svend4/soz150](https://github.com/svend4/soz150) | legal | 300+ инструментов немецкого социального права | 100010 |
| [svend4/meta1](https://github.com/svend4/meta1) | continuum | Детерминированный AI-рантайм, Step/DAG | 110100 |
| svend4/info3+4+30+100 | ai_research | ReAct, CoT, ToT, MAS, Agentic Workflow | 110100 |
| svend4/pro2 (домен) | infosystems | Архитектура информационных систем | 101001 |
| svend4/pro2 (домен) | ai_agents | ИИ-агенты и мультиагентные системы | 110100 |

---

## Быстрый старт

```bash
git clone https://github.com/svend4/nautilus
cd nautilus

# Поиск концепта (текстовый вывод)
python portal.py --query "синтез"

# Веб-портал с живым поиском → http://localhost:8000
python portal.py --serve

# REST API → http://localhost:8080
python api.py

# Семантический поиск (TF-IDF, 207 документов)
python tfidf_search.py "квантовые вычисления"

# Состояние экосистемы
python health_check.py

# Docker
docker compose up portal api
```

---

## Как это работает

```
info1  pro2  meta  data2  data7  graphrag  daten22  legal  continuum  ai_research
  └──────┴─────┴─────┴─────┴────────┴────────┴──────┴────────┴──────────┘
                                     │
                             ⬡ Nautilus Portal v1.2
                      BaseAdapter · PortalEntry · BridgeRegistry
                                     │
              ┌──────────────────────┼────────────────────────┐
              │                      │                         │
       текстовый вывод        REST API / JSON             HTML SPA
       portal.py --query      api.py :8080                --serve :8000
```

**Q6-пространство** — каждый концепт имеет координату в {0,1}⁶ (64 вершины). Расстояние Хэмминга = семантическая близость. Соответствует гексаграммам И-Цзин и CA-классам Вольфрама.

**Bridge-граф** — 33 типизированных связи между адаптерами (analogy / derivation / projection / embedding / isomorphism). Bridge algebra v2.0: `invert`, `compose`, `transitive_closure`.

**Аннотации** — любой участник или агент-адаптер аннотирует любую запись. Protocol 3: автоматические флаги `needs_review` при обнаружении конфликтов.

---

## REST API

```bash
GET  /api/query?q=синтез&ranked=1       поиск с ранжированием
GET  /api/health                         состояние экосистемы (score 0–100)
GET  /api/links                          валидация 317 кросс-ссылок
GET  /api/describe                       описание всех адаптеров
GET  /api/neighbors?q6=110001&dist=1     Q6-соседи по Хэммингу
GET  /api/bridge?id=pro2:bidir&hops=2    обход графа bridges
GET  /api/bridge_conflicts               Protocol 3: Q6-конфликты
GET  /api/bridge_summary                 сводка bridges + transitive closure
GET  /api/annotations?target=<id>        аннотации к записи
POST /api/annotations                    добавить аннотацию (JSON body)
GET  /api/flags[?severity=warning]       Protocol 3: флаги для ревью
GET  /metrics                            Prometheus text/plain
```

Полная спецификация: [`openapi.yaml`](openapi.yaml)

---

## Инструменты анализа

| Инструмент | Команда | Что делает |
|-----------|---------|-----------|
| **Health Check** | `python health_check.py` | Score 0–100, диагностика адаптеров и bridges |
| **Validate Links** | `python validate_links.py` | Проверка 317 кросс-ссылок |
| **Gap Detection** | `python gap_detection.py` | Пробелы в Q6-покрытии (BFS) |
| **TF-IDF Search** | `python tfidf_search.py "запрос"` | Семантический поиск по 207 документам |
| **Clustering** | `python cluster.py --radius 1` | Кластеры по Q6-близости |
| **Diff Report** | `python diff_report.py` | Дельта с последней синхронизации |
| **Timeline** | `python timeline.py` | Свежесть данных |
| **Snapshot** | `python snapshot.py` | Точечный снимок состояния |
| **Q6 Map** | `open q6_map.html` | Интерактивная карта гиперкуба + тепловая карта |
| **Graph** | `open graph.html` | D3.js граф кросс-ссылок |

---

## Подключить новый репозиторий

**Вариант A — 5 минут** (только `nautilus.json` в корне репо):

```json
{
  "name": "my-repo",
  "format": "my-format",
  "native_unit": "документ",
  "compatibility": 1,
  "q6": "010100"
}
```

**Вариант B — полный адаптер:**

```python
from adapters.base import BaseAdapter, PortalEntry

class MyRepoAdapter(BaseAdapter):
    name = "my-repo"

    def fetch(self, query: str) -> list[PortalEntry]:
        return [PortalEntry(
            id="my-repo:concept:1",
            title="Концепт",
            source="svend4/my-repo",
            format_type="concept",
            content="...",
            metadata={"q6": "010100"},
            links=["pro2:q6:010100"],
        )]

    def describe(self) -> dict:
        return {"format": "my-format", "native_unit": "документ"}
```

Полное руководство: [`INTEGRATION.md`](INTEGRATION.md)

---

## Расширенные адаптеры

| Адаптер | Класс | Источник |
|---------|-------|---------|
| **ObsidianAdapter** | `adapters/obsidian.py` | Локальный Obsidian vault |
| **ArxivAdapter** | `adapters/arxiv.py` | arXiv API (12ч кэш) |
| **GitHubTopicAdapter** | `adapters/github_topic.py` | GitHub `nautilus-compatible` |
| **JSONLAdapter** | `adapters/jsonl.py` | `.jsonl` файлы |
| **AutoAdapter** | `adapters/auto.py` | Любой репо с `nautilus.json` |
| **ConversationAdapter** | `adapters/conversation.py` | LLM-сессии (`.md`, `.json`) |

---

## Файловая структура

```
nautilus/
├── portal.py              ← движок портала (14 адаптеров, bridge + annotation API)
├── api.py                 ← REST API (12 эндпоинтов)
├── annotations.py         ← Annotation system (Double-Triangle Protocol 3)
├── bridge_registry.py     ← Bridge algebra v2.0
├── nautilus.json          ← реестр: 13 репозиториев, v1.2
├── nautilus_sdk.py        ← Python SDK для клиентов
├── openapi.yaml           ← OpenAPI 3.1.0 спецификация
│
├── adapters/              ← 14 адаптеров
│   ├── base.py            ← BaseAdapter + PortalEntry (протокол)
│   ├── info1.py, pro2.py, meta.py, data2.py, data7.py
│   ├── infosystems.py, ai_agents.py
│   ├── graphrag.py, daten22.py, legal.py, continuum.py, ai_research.py
│   ├── auto.py, obsidian.py, arxiv.py, github_topic.py, jsonl.py
│   └── cache.py           ← дисковый кэш (TTL = 24ч)
│
├── passports/             ← 12 паспортов с типизированными bridges
├── tests/                 ← 60 тестов (все проходят)
├── docs/                  ← документация
│   ├── STATUS_v1.2.md     ← текущий технический статус
│   ├── CONCEPTUAL_STAGE.md ← концептуальная стадия
│   ├── BRIDGE_STATUS.md   ← bridge system
│   ├── ANNOTATION_SYSTEM.md ← Protocol 3
│   └── ADAPTER_ROADMAP.md ← дорожная карта адаптеров
│
├── health_check.py        ← диагностика с bridge stats
├── validate_links.py      ← валидация ссылок (0 битых из 317)
├── gap_detection.py       ← анализ Q6-пробелов
├── tfidf_search.py        ← семантический поиск
├── cluster.py             ← кластеризация концептов
├── q6_map.html            ← интерактивная Q6-карта
└── graph.html             ← D3.js граф кросс-ссылок
```

---

## Метрики проекта

| Показатель | v1.1 | **v1.2** |
|-----------|:----:|:--------:|
| Python LOC | 6 782 | **8 733** |
| Адаптеров | 13 | **14** |
| Паспортов | 7 | **12** |
| Кросс-ссылок | 187 | **317** |
| Мостов (bridges) | 0 | **33** |
| TF-IDF документов | 200 | **207** |
| API эндпоинтов | 7 | **12** |
| Тестов | 60 ✅ | **60 ✅** |
| mypy ошибок | 0 ✅ | **0 ✅** |
| Внешних зависимостей | 0 | **0** |

---

## Документация

| Файл | Содержание |
|------|-----------|
| [`docs/STATUS_v1.2.md`](docs/STATUS_v1.2.md) | Технический статус, метрики |
| [`docs/CONCEPTUAL_STAGE.md`](docs/CONCEPTUAL_STAGE.md) | Концептуальная зрелость |
| [`docs/BRIDGE_STATUS.md`](docs/BRIDGE_STATUS.md) | Bridge algebra v2.0 |
| [`docs/ANNOTATION_SYSTEM.md`](docs/ANNOTATION_SYSTEM.md) | Protocol 3, аннотации |
| [`docs/ADAPTER_ROADMAP.md`](docs/ADAPTER_ROADMAP.md) | Дорожная карта адаптеров |
| [`docs/BRIDGES_FORMALIZATION.md`](docs/BRIDGES_FORMALIZATION.md) | Формальная спецификация bridges |
| [`INTEGRATION.md`](INTEGRATION.md) | Руководство по подключению репо |
| [`PORTAL-PROTOCOL.md`](PORTAL-PROTOCOL.md) | Формальный протокол портала |

---

*Nautilus Portal Protocol v1.2 · [docs/STATUS_v1.2.md](docs/STATUS_v1.2.md)*
