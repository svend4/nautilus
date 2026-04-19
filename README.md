# ⬡ Nautilus Portal

**Единая точка входа для экосистемы svend4** · v1.1

> Не слияние — совместимость.  
> Как Office Suite читает `.docx`, `.pdf`, `.xlsx` не сливая их в один формат —  
> Nautilus читает все репозитории экосистемы, находит связи, строит общий вид.

[![CI](https://github.com/svend4/nautilus/actions/workflows/ci.yml/badge.svg)](https://github.com/svend4/nautilus/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-60%20passed-brightgreen)
![mypy](https://img.shields.io/badge/mypy-clean-brightgreen)
![Links](https://img.shields.io/badge/links-187%20valid-brightgreen)
![Health](https://img.shields.io/badge/health-82%2F100-yellow)

---

## Репозитории экосистемы

| Репо | Формат | Что хранит | Совместимость |
|------|--------|-----------|:---:|
| [svend4/info1](https://github.com/svend4/info1) | `.info1` | 74+ Markdown-документа с α-уровнями (-4..+4) | 1 |
| [svend4/pro2](https://github.com/svend4/pro2) | `.pro2` | Q6-концепты, граф знаний, bidir-цикл | 3 |
| [svend4/meta](https://github.com/svend4/meta) | `.meta` | 256 CA-правил + 64 гексаграммы И-Цзин | 1 |
| [svend4/data2](https://github.com/svend4/data2) | `.data2` | 310+ томов ЕТД (Единая Теория Движения) | 1 |
| [svend4/data7](https://github.com/svend4/data7) | `.data7` | Граф знаний, K₀→K∞ трансформация | 2 |
| svend4/pro2 (домен) | `.infosystems` | Архитектура информационных систем | 2 |
| svend4/pro2 (домен) | `.ai_agents` | ИИ-агенты и мультиагентные системы | 2 |

Уровни совместимости: **0** обнаруживаемый · **1** читаемый · **2** связанный · **3** интерактивный

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

# Семантический поиск (TF-IDF)
python tfidf_search.py --build-index
python tfidf_search.py "квантовые вычисления"

# Кластеризация концептов по Q6-близости
python cluster.py --radius 1

# Q6-карта в браузере (интерактивный гиперкуб + тепловая карта)
open q6_map.html

# Состояние экосистемы
python health_check.py

# Docker (portal + api + health + snapshot)
docker compose up portal api
```

---

## Как это работает

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  info1   │  │   pro2   │  │   meta   │  │  data2   │  │  data7   │
│ α-уровни │  │ Q6-граф  │  │ CA-прав. │  │  тома    │  │  K₀→K∞  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │              │              │
     └──────────────┴──────────────┴──────────────┴──────────────┘
                                   │
                           ⬡ Nautilus Portal
                    BaseAdapter · PortalEntry · CacheManager
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
       текстовый вывод      REST API / JSON        HTML SPA
       portal.py --query    api.py :8080           --serve :8000
```

**Консенсус** — концепт признаётся согласованным, если найден во всех репозиториях (coverage = 100%). Частичный консенсус показывает, в каких репо концепт есть, в каких — отсутствует.

**Q6-пространство** — каждый концепт имеет координату в 6-битном гиперкубе {0,1}⁶ (64 вершины). Вершины соответствуют гексаграммам И-Цзин и классам CA Вольфрама. Расстояние Хэмминга = семантическая близость.

---

## REST API

```bash
GET /api/query?q=синтез&ranked=1    # поиск с ранжированием
GET /api/health                      # здоровье экосистемы (score 0–100)
GET /api/links                       # валидация кросс-ссылок
GET /api/describe                    # описание всех адаптеров
GET /api/neighbors?q6=110001&dist=1  # Q6-соседи по Хэммингу
GET /metrics                         # Prometheus-метрики
```

Полная спецификация: [`openapi.yaml`](openapi.yaml)

---

## Инструменты анализа

| Инструмент | Команда | Что делает |
|-----------|---------|-----------|
| **Health Check** | `python health_check.py` | Score 0–100, диагностика всех адаптеров |
| **Validate Links** | `python validate_links.py` | Проверка 187 кросс-ссылок |
| **Gap Detection** | `python gap_detection.py` | Пробелы в Q6-покрытии (BFS по Хэммингу) |
| **TF-IDF Search** | `python tfidf_search.py "запрос"` | Семантический поиск (cosine similarity) |
| **Clustering** | `python cluster.py --radius 1` | Кластеры концептов по Q6-близости |
| **Diff Report** | `python diff_report.py` | Дельта с последней синхронизации |
| **Timeline** | `python timeline.py` | Свежесть данных: кэш, адаптеры, паспорта |
| **Snapshot** | `python snapshot.py` | Точечный снимок состояния экосистемы |
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
  "q6": "010100",
  "bridges": {
    "pro2": "Q6-концепты ↔ my-format через тему",
    "info1": "α-уровень ↔ my abstraction"
  }
}
```

**Вариант B — полный адаптер:**

```python
# adapters/my_repo.py
from adapters.base import BaseAdapter, PortalEntry

class MyRepoAdapter(BaseAdapter):
    name = "my-repo"

    def fetch(self, query: str) -> list[PortalEntry]:
        # вернуть список PortalEntry, не бросать исключения
        return [PortalEntry(
            id="my-repo:concept:1",
            title="Концепт",
            source="svend4/my-repo",
            format_type="document",
            content="...",
            metadata={"q6": "010100", "alpha": 0},
            links=["pro2:q6:010100"],
        )]

    def describe(self) -> dict:
        return {"format": "my-format", "native_unit": "документ"}
```

Зарегистрировать: `portal.register("my-repo", MyRepoAdapter())`

Полное руководство: [`INTEGRATION.md`](INTEGRATION.md) (Варианты A–E)

---

## Расширенные адаптеры

Помимо 7 реестровых адаптеров доступны:

| Адаптер | Класс | Источник |
|---------|-------|---------|
| **ObsidianAdapter** | `adapters/obsidian.py` | Локальный Obsidian vault (`[[wikilinks]]`) |
| **ArxivAdapter** | `adapters/arxiv.py` | arXiv API (статьи по категориям, 12ч кэш) |
| **GitHubTopicAdapter** | `adapters/github_topic.py` | GitHub repos с топиком `nautilus-compatible` |
| **JSONLAdapter** | `adapters/jsonl.py` | Локальные `.jsonl` файлы как поток записей |
| **AutoAdapter** | `adapters/auto.py` | Любой репо с `nautilus.json` в корне |

```python
from adapters.obsidian import ObsidianAdapter
portal.register("obsidian", ObsidianAdapter("/path/to/vault"))

from adapters.jsonl import JSONLAdapter
portal.register("corpus", JSONLAdapter("data/knowledge.jsonl"))
```

---

## Файловая структура

```
nautilus/
├── portal.py              ← движок портала (533 LOC)
├── api.py                 ← REST API (265 LOC)
├── nautilus.json          ← реестр: 7 репозиториев
├── nautilus_sdk.py        ← Python SDK для клиентов
├── openapi.yaml           ← OpenAPI 3.1.0 спецификация
│
├── adapters/
│   ├── base.py            ← BaseAdapter + PortalEntry (протокол)
│   ├── info1.py, pro2.py, meta.py, data2.py, data7.py
│   ├── infosystems.py, ai_agents.py
│   ├── auto.py, obsidian.py, arxiv.py, github_topic.py, jsonl.py
│   └── cache.py           ← дисковый кэш (TTL = 24ч)
│
├── passports/             ← 7 паспортов репозиториев (.md)
│
├── tests/                 ← 60 тестов (все проходят)
│   ├── test_adapters.py, test_portal.py
│   ├── test_health_check.py, test_validate_links.py
│
├── .github/workflows/
│   ├── ci.yml             ← pytest + validate + health (push/PR)
│   ├── sync.yml           ← еженедельная синхронизация (пн 03:00 UTC)
│   └── ...
│
├── q6_map.html            ← интерактивная Q6-карта + тепловая карта
├── graph.html             ← D3.js граф кросс-ссылок
├── Dockerfile             ← образ Python 3.11-slim
├── docker-compose.yml     ← portal · api · health · snapshot
│
├── health_check.py        ← диагностика (score: 82/100)
├── validate_links.py      ← валидация ссылок (0 битых)
├── gap_detection.py       ← анализ Q6-пробелов
├── tfidf_search.py        ← семантический поиск
├── cluster.py             ← кластеризация концептов
├── diff_report.py         ← дельта изменений
├── timeline.py            ← временная шкала свежести
├── snapshot.py            ← снимок состояния
│
└── STATUS.md              ← детальный отчёт о состоянии проекта
```

---

## Метрики проекта

| Показатель | Значение |
|-----------|---------|
| Python LOC | 6 782 |
| Тестов | 60 / 60 ✅ |
| mypy ошибок | 0 ✅ |
| Битых ссылок | 0 / 187 ✅ |
| Health Score | 82 / 100 |
| Q6-покрытие | 21.9% real · 29.7% fallback |
| Внешних зависимостей | **0** (stdlib only) |

---

*Nautilus Portal Protocol v1.1 · [STATUS.md](STATUS.md) · [INTEGRATION.md](INTEGRATION.md)*
