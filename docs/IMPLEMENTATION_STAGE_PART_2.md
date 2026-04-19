# Отчёт о стадии реализации проекта Nautilus — Часть 2

## Техническая стадия — детали реализации

---

## 1. Ядро портала (`portal.py`, 533 LoC)

### Главный класс `NautilusPortal`

```python
class NautilusPortal:
    def __init__(self) -> None:
        self.adapters = {
            "info1":       Info1Adapter(),
            "pro2":        Pro2Adapter(),
            "meta":        MetaAdapter(),
            "data2":       Data2Adapter(),
            "data7":       Data7Adapter(),
            "infosystems": InfoSystemsAdapter(),
            "ai_agents":   AIAgentsAdapter(),
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

Функция `q6_neighbors(bits, max_distance)` (`portal.py:23`) — BFS по 6-битному кубу, возвращает все вершины в пределах Хэмминг-расстояния.

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

## 2. Адаптерный слой (`adapters/`, 13 модулей, ~2 200 LoC)

### Протокол `BaseAdapter` (`adapters/base.py:38`)

```python
class BaseAdapter(ABC):
    name: str = "unnamed"

    @abstractmethod
    def fetch(self, query: str) -> list[PortalEntry]: ...

    @abstractmethod
    def describe(self) -> dict[str, Any]: ...
```

### Дата-модель `PortalEntry` (`adapters/base.py:14`)

```python
@dataclass
class PortalEntry:
    id: str                              # "format:slug"
    title: str
    source: str                          # GitHub slug
    format_type: str                     # document|concept|rule
    content: str
    metadata: dict[str, Any] = {}
    links: list[str] = []                # кросс-ссылки
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
| 13 | `cache.py` | 105 | — | декоратор-обёртка |
| — | `base.py` | 71 | — | протокол |

### Pro2Adapter — флагман уровня 3

- Живой поиск по `bidir_train_v2_log.json`
- Парсинг `self_improvement_report.txt` с регекспами (метрики `CD`, `VT`, `CR`, `DB`)
- Таблица `_Q6_LABELS` — 6-битные паттерны → семантические метки (64 состояния)
- Fallback на статические записи при ошибке

### Fuzzy-matching

Общая утилита `fuzzy_match()` (`adapters/base.py:27`) — `difflib.SequenceMatcher` с настраиваемым порогом. Используется в обёртках адаптеров для толерантности к опечаткам.

---

## 3. Семантический слой (~780 LoC)

### TF-IDF поиск (`tfidf_search.py`, 259 LoC)

- Полнотекстовый индекс без numpy/scipy
- Хранение: `snapshots/tfidf_index.json` (109 КБ)
- Токенизация, стоп-слова, нормализация TF-IDF
- Косинусная близость запроса к документам

### Кластеризация (`cluster.py`, 240 LoC)

- Группировка концептов по Q6 Hamming-расстоянию
- Выявление семантических кластеров в 6-битном кубе

### Gap-detection (`gap_detection.py`, 283 LoC)

- Обнаружение пустых ячеек в Q6-пространстве
- Отчёт о непокрытых координатах по адаптерам

---

## 4. Инфраструктура и DevOps (~1 050 LoC)

### HTTP API (`api.py`, 265 LoC)

| Эндпоинт | Назначение |
|----------|------------|
| `GET /api/query?q=...&ranked=1` | поиск концептов |
| `GET /api/health` | состояние экосистемы |
| `GET /api/links` | валидация ссылок |
| `GET /api/describe` | описание адаптеров |
| `GET /metrics` | Prometheus-метрики |

- CORS включён (`Access-Control-Allow-Origin: *`)
- TTL-кеш для `/metrics` (30 сек) чтобы не долбить health_check
- Базируется на stdlib `http.server`

### SDK (`nautilus_sdk.py`, 189 LoC)

Клиентская библиотека-обёртка над HTTP API.

### OpenAPI (`openapi.yaml`)

Формальная спецификация REST API.

### CI/CD пайплайны (`.github/workflows/`, 4 workflow)

| Файл | Назначение |
|------|------------|
| `ci.yml` | тесты + mypy на каждый push |
| `sync.yml` | синхронизация снапшотов |
| `register_nautilus.yml` | авто-регистрация репо через webhook |
| `auto_update.yml` | обновление реестра при событии `repo_registered` |

### Контейнеризация

- `Dockerfile` — образ
- `docker-compose.yml` — оркестрация
- `bootstrap.sh` — установочный скрипт

### Мониторинг

- `health_check.py` (261 LoC) — проверка живости адаптеров
- `validate_links.py` (161 LoC) — валидация кросс-ссылок
- Prometheus `/metrics` — интеграция со стандартным мониторингом

### Типобезопасность

- `mypy.ini` — строгий конфиг
- Маркер `adapters/py.typed`
- **0 mypy-ошибок** во всём проекте (коммит `4731776`)

---

## 5. Жизненный цикл данных

### Snapshot/Diff

- `snapshot.py` (218 LoC) — фиксация состояния экосистемы
- `snapshots/latest_diff_baseline.json` (54 КБ) — последний baseline
- `diff_report.py` (234 LoC) — дельты между снапшотами
- `timeline.py` (250 LoC) — хронология изменений

### Онбординг новых репо

- `scan_repo.py` (410 LoC) — авто-сканер через GitHub API
- `generate_passport.py` (290 LoC) — интерактивный мастер
- `passport_schema.json` — JSON-Schema валидация паспортов

---

## 6. Безопасность

- **XSS-защита:** `_html.escape` во всех rendered полях (`portal.py:13`, коммит `ac981c9`)
- **Нет eval/exec** в кодовой базе
- **Нет secrets** в коде (GITHUB_TOKEN через env)
- **Timeout 5 сек** на все HTTP-запросы к GitHub API
- **Fallback при ошибках** — адаптеры не бросают исключения

---

## 7. Что технически отсутствует

| Компонент | Статус | Критичность |
|-----------|--------|-------------|
| Реальная БД | ❌ только in-memory + статика | низкая (достаточно для MVP) |
| Аутентификация API | ❌ публичный доступ | средняя |
| RBAC | ❌ | низкая |
| pip/npm-пакет | ❌ нет `pyproject.toml` | средняя |
| Kubernetes/Helm | ❌ только compose | низкая |
| Coverage-отчёты | ❌ | средняя |
| E2E-тесты | ❌ только unit | средняя |
| Rate limiting на API | ❌ | средняя |

**Подробности концептуальной стадии — в Части 3.**
