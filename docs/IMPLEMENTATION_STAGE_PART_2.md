# Отчёт о стадии реализации проекта Nautilus — Часть 2

## Техническая стадия — детали реализации

---

## 1. Ядро портала (`portal.py`, 533 LoC)

### Главный класс `NautilusPortal`

```python
class NautilusPortal:
    def __init__(self) -> None:
        self.adapters = {
            "info1":         Info1Adapter(),
            "pro2":          Pro2Adapter(),
            "meta":          MetaAdapter(),
            "data2":         Data2Adapter(),
            "data7":         Data7Adapter(),
            "infosystems":   InfoSystemsAdapter(),
            "ai_agents":     AIAgentsAdapter(),
            "conversations": ConversationAdapter(),
        }
        self._load_auto_adapters()
```

### Ключевые методы

| Метод | Расположение | Назначение |
|-------|--------------|------------|
| `query()` | `portal.py:108` | Мультиадаптерный поиск с ранжированием |
| `query_neighbors()` | `portal.py:127` | Поиск по Q6-соседям (Hamming-метрика) |
| `_consensus()` | `portal.py:163` | Расчёт покрытия с учётом fallback |
| `_cross_links()` | `portal.py:149` | Извлечение межрепозиторных связей |
| `register()` | `portal.py:124` | Динамическая регистрация адаптера |
| `_load_auto_adapters()` | `portal.py:92` | Авто-загрузка из `nautilus.json` |

### Алгоритм ранжирования (`_relevance_score`)

```python
# portal.py:45-68
score = 0.0
if q == title_l:           score += 1.0   # точное совпадение заголовка
elif q in title_l:         score += 0.7   # подстрока заголовка
if q in content_l:         score += 0.3   # подстрока контента
if q in entry.id.lower():  score += 0.4   # совпадение в ID
score += min(len(entry.links) * 0.05, 0.2)  # бонус за связность
if entry.is_fallback:      score *= 0.5   # штраф за fallback
```

### Q6-соседство (Hamming)

Функция `q6_neighbors(bits, max_distance)` (`portal.py:23`) — BFS по 6-битному кубу,
возвращает все вершины в пределах Хэмминг-расстояния.

### Консенсус-модель

```python
# portal.py:170-177
{
    "present_in":             [...],  # реальные источники
    "present_in_fallback":    [...],  # только заглушки
    "missing_in":             [...],  # не найдено
    "coverage":               0.XX,   # реальное покрытие
    "coverage_with_fallback": 0.XX,
    "agreed":                 coverage >= 1.0
}
```

---

## 2. Адаптерный слой (`adapters/`, 14 модулей, ~2 430 LoC)

### Протокол `BaseAdapter` (`adapters/base.py:38`)

```python
class BaseAdapter(ABC):
    name: str = "unnamed"

    @abstractmethod
    def fetch(self, query: str) -> list[PortalEntry]: ...

    @abstractmethod
    def describe(self) -> dict[str, Any]: ...
```

Полностью аннотирован: `py.typed` маркер + `mypy.ini` strict. **0 ошибок.**

### Дата-модель `PortalEntry` (`adapters/base.py:14`)

```python
@dataclass
class PortalEntry:
    id: str                         # "format:slug"
    title: str
    source: str                     # GitHub slug
    format_type: str                # document|concept|rule
    content: str
    metadata: dict[str, Any] = {}
    links: list[str] = []           # кросс-ссылки
    is_fallback: bool = False
```

### Таблица адаптеров

| # | Адаптер | LoC | Уровень | Тип |
|---|---------|-----|---------|-----|
| 1 | `pro2.py` | 347 | **3** — интерактивный | основной |
| 2 | `meta.py` | 177 | 1 — читаемый | основной |
| 3 | `obsidian.py` | 173 | — | универсальный |
| 4 | `arxiv.py` | 162 | — | внешний источник |
| 5 | `ai_agents.py` | 156 | 2 — связанный | домен pro2 |
| 6 | `github_topic.py` | 155 | — | универсальный |
| 7 | `jsonl.py` | 154 | — | универсальный |
| 8 | `data2.py` | 157 | 1 — читаемый | основной |
| 9 | `auto.py` | 131 | — | читает `nautilus.json` |
| 10 | `info1.py` | 130 | 1 — читаемый | основной |
| 11 | `infosystems.py` | 125 | 2 — связанный | домен pro2 |
| 12 | `data7.py` | 121 | 2 — связанный | основной |
| 13 | `cache.py` | 105 | — | дисковый кэш (TTL 24ч) |
| 14 | `conversation.py` | ~230 | — | экспорты LLM-сессий |
| — | `base.py` | 71 | — | протокол |

### Новые адаптеры (Round 2)

**ArxivAdapter** (`arxiv.py`) — запрашивает arXiv Atom API, маппит категории
(cs.AI→`111110`, cs.LG→`101010`) на Q6, 12-часовой дисковый кэш.

**GitHubTopicAdapter** (`github_topic.py`) — GitHub Search API по топику
`nautilus-compatible`, пробует загрузить `nautilus.json` каждого репо.

**JSONLAdapter** (`jsonl.py`) — читает `.jsonl`-файлы (файл или директорию),
гибкий маппинг полей, fuzzy search.

**ConversationAdapter** (`conversation.py`) — читает экспорты Claude/LLM-сессий
(`.md`, `.txt`, `.json`, без расширения). Разбивает по заголовкам Markdown или
абзацам (chunk ≤ 700 символов), автоматически назначает Q6 по ключевым словам
темы (multi-agent → `110100`, strategy → `111110` и т.д.). Зарегистрирован в
`NautilusPortal` по умолчанию с путём `docs/`.

---

## 3. Семантический слой (~782 LoC)

### TF-IDF поиск (`tfidf_search.py`, 259 LoC)

- Полнотекстовый индекс без numpy/scipy (stdlib only)
- Хранение: `snapshots/tfidf_index.json`
- Токенизация (`_tokenize`), TF-IDF с L2-нормализацией
- Косинусная близость запроса к документам
- Заголовок весом ×3 для повышения точности
- Опции: `--build-index`, `--top N`, `--no-cache`, `--json`

Пример результата (запрос «синтез»):
```
1. [0.599]  Q6=010100 · Синтез I
2. [0.587]  Архетип: Синтез  Q6=111110
3. [0.474]  Q6=111110 · Синтез
```

### Кластеризация (`cluster.py`, 240 LoC)

- Жадный алгоритм: итеративно выбирает вершину с наибольшим числом записей
- Поглощает все вершины в радиусе Hamming ≤ `radius` (default: 1)
- Аннотирует кластер: CA-класс, α-уровень, адаптеры
- Результат: 12 кластеров при radius=1 для 101 записи

### Gap-detection (`gap_detection.py`, 283 LoC)

- BFS по Хэммингу для выявления пустых ячеек Q6
- Текущее состояние: 14 real / 19 weak / **31 gap** (48.4%)
- Класс II наиболее уязвим: 31/50 непокрытых (62%)
- Приоритетные вершины: `010001`, `100001`, `100010`

---

## 4. Инфраструктура и DevOps (~1 050 LoC)

### HTTP API (`api.py`, 265 LoC)

| Эндпоинт | Назначение |
|----------|------------|
| `GET /api/query?q=...&ranked=1` | поиск концептов |
| `GET /api/health` | состояние экосистемы (score 0–100) |
| `GET /api/links` | валидация ссылок |
| `GET /api/describe` | описание адаптеров |
| `GET /api/neighbors?q6=110001&dist=1` | Q6-соседи |
| `GET /metrics` | Prometheus-метрики (text/plain, TTL 30с) |

CORS включён. Основан на stdlib `http.server`.

### Prometheus-метрики (`/metrics`)

```
nautilus_health_score        # 82
nautilus_adapters_count      # 7
nautilus_adapter_entries{adapter="info1"} 74
nautilus_adapter_entries{adapter="data2"} 310
nautilus_cache_age_hours{repo="svend4_pro2"} 0.12
```

### SDK (`nautilus_sdk.py`, 189 LoC)

Клиентская библиотека-обёртка над HTTP API.

### OpenAPI (`openapi.yaml`, 338 LoC)

Формальная спецификация REST API v3.1.0. Включает схемы:
`PortalEntry`, `Consensus`, `CrossLink`, `QueryResult`, `HealthReport`.

### CI/CD пайплайны (`.github/workflows/`, 4 workflow)

| Файл | Триггер | Назначение |
|------|---------|------------|
| `ci.yml` | push / PR | pytest 60 тестов + mypy + validate_links + health_check |
| `sync.yml` | пн 03:00 UTC | scan_repo → passports → gap_detection → auto-commit |
| `register_nautilus.yml` | вручную | GitHub Pages публикация |
| `auto_update.yml` | вручную | обновление кэша |

### Контейнеризация

- `Dockerfile` — образ `python:3.11-slim`, EXPOSE 8080
- `docker-compose.yml` — сервисы: `portal :8000`, `api :8080`, `health`, `snapshot`
- `.dockerignore` — исключает `.git`, `cache/`, `snapshots/`

### Типобезопасность

- `mypy.ini` с `disallow_untyped_defs = true`
- Маркер `adapters/py.typed` (PEP 561)
- **0 mypy-ошибок** во всём проекте

---

## 5. Жизненный цикл данных

### Snapshot/Diff

- `snapshot.py` (218 LoC) — фиксация состояния экосистемы
- `diff_report.py` (234 LoC) — дельты: новые/удалённые/изменённые записи + Q6-дельта
- `snapshots/latest_diff_baseline.json` — последний baseline (122 записи)
- `timeline.py` (250 LoC) — хронология изменений (git log + mtime + cache age)

### Онбординг новых репо

- `scan_repo.py` (410 LoC) — авто-сканер через GitHub API
- `generate_passport.py` (290 LoC) — интерактивный мастер
- `passport_schema.json` — JSON-Schema валидация паспортов

---

## 6. Визуализация

### Q6 Map (`q6_map.html`)

- Интерактивный 900×620px canvas
- Режим CA-классов (цвета по классу Вольфрама)
- **Режим тепловой карты** (Round 2) — плотность записей: серый→янтарный→зелёный
- Узлы масштабируются по числу записей
- Живая загрузка через `/api/query` + статические данные-fallback
- Поиск, смена осей, тултип с Q6 + CA-класс + счётчик записей

### D3.js граф (`graph.html`)

- Force-directed граф кросс-ссылок
- Узлы: адаптеры, рёбра: кросс-ссылки
- Клик для подсветки подграфа, hover-тултип

---

## 7. Что технически отсутствует

| Компонент | Статус | Критичность |
|-----------|--------|-------------|
| Реальная БД | ❌ только in-memory + статика | низкая (MVP) |
| Аутентификация API | ❌ публичный доступ | средняя |
| RBAC | ❌ | низкая |
| `pyproject.toml` / PyPI | ❌ | средняя |
| Kubernetes/Helm | ❌ только compose | низкая |
| Coverage-отчёты в CI | ❌ | средняя |
| E2E-тесты | ❌ только unit | средняя |
| Rate limiting на API | ❌ | средняя |

**Подробности концептуальной стадии — в Части 3.**
