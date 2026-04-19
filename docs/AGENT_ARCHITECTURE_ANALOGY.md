---
title: "Nautilus как агентная архитектура"
q6: "110100"
type: "architecture"
source: "synthesis: ai_distributed_teams.md + double_triangle_foundation.md"
date: "2026-04-19"
---

# Nautilus как агентная архитектура

**Тезис:** Nautilus Portal — это уже работающая реализация многоуровневой агентной
иерархии, описанной в `docs/sessions/ai_distributed_teams.md`. Не метафора, а прямое
структурное соответствие.

---

## Прямое отображение: теория → код

| Концепт из ai_distributed_teams | Nautilus-компонент | Файл |
|----------------------------------|-------------------|------|
| Мета-агент-координатор | `NautilusPortal` | `portal.py:80` |
| Контракт суб-агента | `BaseAdapter` (абстрактный класс) | `adapters/base.py:38` |
| Суб-агент, прикреплённый к специалисту | `Info1Adapter`, `Pro2Adapter`, `MetaAdapter`, ... | `adapters/*.py` |
| Специалист / домен знаний | Репозитории `info1`, `pro2`, `meta`, `data2`, `data7` | `nautilus.json` |
| Стандартное сообщение между агентами | `PortalEntry` | `adapters/base.py:14` |
| Конкурс между участниками за лучшее решение | Ранжирование через `_relevance_score()` | `portal.py:46` |
| Консенсус команды | `_consensus()` → `coverage`, `agreed` | `portal.py:166` |
| Перекрёстные ссылки между специалистами | `cross_links` в `PortalResult` | `portal.py:152` |
| Семантическая близость специалистов | Q6-расстояние Хэмминга | `portal.py:24` |

---

## Уровень 1 — Мета-координатор: `NautilusPortal`

```python
# portal.py:80
class NautilusPortal:
    def __init__(self) -> None:
        self.adapters = {          # реестр суб-агентов
            "info1":  Info1Adapter(),
            "pro2":   Pro2Adapter(),
            "meta":   MetaAdapter(),
            "data2":  Data2Adapter(),
            "data7":  Data7Adapter(),
            ...
        }

    def query(self, concept: str) -> PortalResult:
        all_entries = []
        for adapter in self.adapters.values():
            all_entries.extend(adapter.fetch(concept))   # параллельный опрос
        all_entries.sort(key=lambda e: _relevance_score(e, concept), reverse=True)
        return PortalResult(..., consensus=self._consensus(all_entries))
```

**Что здесь происходит по-агентному:**

1. `portal.query("мета-агент")` — мета-координатор рассылает задачу всем суб-агентам.
2. Каждый суб-агент отвечает в своём формате (`list[PortalEntry]`).
3. Мета-координатор ранжирует ответы по relevance и вычисляет consensus.
4. `PortalResult.consensus["agreed"]` — пришли ли суб-агенты к согласию.

Это точно та структура, которую описывает `ai_distributed_teams.md`:
> «На верхнем уровне — мета-агент-координатор. Он видит всю картину, распределяет ресурсы, отслеживает прогресс.»

---

## Уровень 2 — Контракт суб-агента: `BaseAdapter`

```python
# adapters/base.py:38
class BaseAdapter(ABC):
    name: str = "unnamed"

    @abstractmethod
    def fetch(self, query: str) -> list[PortalEntry]:
        """Поиск в своём домене. Не бросать исключения."""
        ...

    @abstractmethod
    def describe(self) -> dict:
        """Описание своих возможностей для реестра."""
        ...
```

**Аналогия из теории:** суб-агенты настроены заранее, до появления конкретной задачи.
`BaseAdapter` — это именно такой предварительный контракт: адаптер существует и описывает
себя (`describe()`) независимо от того, есть ли запрос.

Двойственность «ангел-хранитель / строгий критик» реализована через два режима fetch:

- **Режим "ангел"** — `fetch(query)` с реальным контентом: адаптер помогает, подсказывает,
  возвращает полезные `PortalEntry`.
- **Режим "критик"** — `is_fallback=True`: адаптер сигнализирует «данных нет», что
  `_consensus()` интерпретирует как gap и отражает в `missing_in`.

```python
# Пример: адаптер в режиме "критик" (fallback)
def fetch(self, query: str) -> list[PortalEntry]:
    results = self._real_search(query)
    if not results:
        return [PortalEntry(id=f"{self.name}:fallback", ..., is_fallback=True)]
    return results
```

---

## Уровень 3 — Специалисты и их домены

| Адаптер | Домен знаний | Q6 | Что умеет |
|---------|-------------|-----|-----------|
| `Info1Adapter` | Теория информации, уровни α | `101010` | Иерархические концепты |
| `Pro2Adapter` | Q6-граф, I-Цзин, YiJing-трансформер | `110100` | Семантические связи |
| `MetaAdapter` | 256 CA-правил, гексаграммы | `110001` | Паттерн-матчинг |
| `Data2Adapter` | ЕТД Крюкова, робототехника | `010100` | Формальные теории |
| `Data7Adapter` | Диссертации, энциклопедии, MMORPG | `010100` | Архивный поиск |
| `ConversationAdapter` | Экспорты Claude-сессий | `110100`..`010101` | Разговорные паттерны |

Аналогия из теории — «разработчики PHP для узкой задачи, суб-агент настроен именно под
эту задачу». Каждый адаптер знает только свой домен и не знает о других.

---

## Стандартное сообщение: `PortalEntry`

```python
# adapters/base.py:14
@dataclass
class PortalEntry:
    id: str               # "pro2:hexagram_42" — уникальный ID в пространстве портала
    title: str            # человекочитаемый заголовок
    source: str           # репо-источник
    format_type: str      # "document" | "concept" | "rule"
    content: str          # полный текст
    metadata: dict        # q6, tags, language, jurisdiction, ...
    links: list[str]      # перекрёстные ссылки на другие PortalEntry
    is_fallback: bool     # True = нет реальных данных
```

`PortalEntry` — это **протокол сообщения между агентами**: независимо от того, какой
адаптер вернул запись, мета-координатор работает с ней одинаково. Суб-агенты не знают
о формате друг друга — они знают только формат `PortalEntry`.

---

## Консенсус и конкурс

`ai_distributed_teams.md` описывает: «агент может принимать N решений от N разработчиков
параллельно, давать feedback, выбирать лучшее». В Nautilus это реализовано двумя способами.

**Конкурс** — ранжирование через `_relevance_score()`:

```python
# portal.py:46
def _relevance_score(entry: PortalEntry, query: str) -> float:
    score = 0.0
    if q in entry.title.lower():    score += 0.7
    if q in entry.content.lower():  score += 0.3
    if q in entry.id.lower():       score += 0.4
    score += min(len(entry.links) * 0.05, 0.2)  # связность = бонус
    if entry.is_fallback:           score *= 0.5  # штраф за пустой ответ
    return min(score, 1.0)
```

Записи из разных адаптеров конкурируют за позицию в `PortalResult.entries`.

**Консенсус** — `_consensus()` считает, сколько суб-агентов нашли реальные данные:

```python
# Интерпретация consensus["agreed"]:
# True  → ВСЕ адаптеры нашли что-то реальное по запросу
# False → часть адаптеров вернула только fallback или ничего

result = portal.query("мета-агент оркестрация")
if not result.consensus["agreed"]:
    gaps = result.consensus["missing_in"]
    print(f"Концепт не зафиксирован в: {gaps}")
    # → сигнал: стоит добавить в те базы знаний
```

---

## Q6 как семантическая маршрутизация

В теории «агентам нужна общая память и протокол коммуникации». В Nautilus — это Q6.

```python
# portal.py:24
def q6_neighbors(bits: str, max_distance: int = 1) -> list[str]:
    """Все Q6-координаты в радиусе Хэмминга от bits."""
    ...

# Пример: найти все адаптеры, семантически близкие к "AI-агенты" (110100)
neighbors = q6_neighbors("110100", max_distance=1)
# ['010100', '100100', '111100', '110000', '110101', '110110', '110111']
```

Q6 — это **адрес суб-агента в семантическом пространстве**. Мета-координатор может
выбрать «кого спрашивать» не перебором всех адаптеров, а навигацией по Q6-соседям.
Это масштабируется: при 64 адаптерах вместо `O(N)` опроса — `O(1)` навигация.

---

## Double-Triangle в Nautilus

Из `double_triangle_foundation.md`:
> «Anthropic-like company — upper triangle: meta-coordinator для distributed team.
> Каждый специалист — Node со своими AI-assistant'ами.»

В Nautilus:

```
┌─────────────────────────────────────┐
│          NautilusPortal              │ ← upper triangle
│          (мета-координатор)          │   видит всех, ранжирует, consensus
└──────┬────────┬────────┬────────────┘
       │        │        │
  ┌────▼──┐ ┌───▼──┐ ┌───▼──┐  ...
  │info1  │ │ pro2 │ │ meta │        ← nodes (суб-агенты)
  │(α-уровни│ │(Q6-граф│ │(CA-правила│   каждый знает только свой домен
  └───────┘ └──────┘ └──────┘
       │        │        │
  ┌────▼──┐ ┌───▼──┐ ┌───▼──┐
  │repos  │ │repos │ │repos │        ← domain specialists
  │info1/ │ │pro2/ │ │meta/ │           (реальные репозитории svend4)
  └───────┘ └──────┘ └──────┘
```

**Нижний треугольник** — репозитории как носители знаний.
**Верхний треугольник** — Portal как координатор.
**Bridges** (поле `links` в `PortalEntry`) — связи между узлами, пересекающие домены.

---

## Что пока не реализовано из теории

| Теоретический концепт | Статус в Nautilus | Следующий шаг |
|-----------------------|-------------------|---------------|
| Переключение agent.mode (ментор ↔ критик) | Только через `is_fallback` | Добавить `phase` parameter в `fetch()` |
| Межагентная коммуникация (суб-агенты говорят друг с другом) | Только через `links` в PortalEntry | Annotation system (см. `double_triangle_foundation.md:292`) |
| Персистентная память проекта | Нет | `snapshots/` + adapter для истории запросов |
| Branching conversations | Нет | `ConversationBranch` dataclass из `double_triangle_foundation.md:340` |
| Explicit phase tracking | Нет | `PortalSession` обёртка над `NautilusPortal` |

---

## Вывод

Nautilus реализует **уровни 1-2** из описанной теории:
- Мета-координатор (`NautilusPortal`) — работает.
- Суб-агенты с контрактом (`BaseAdapter`) — работают.
- Конкурс и консенсус — работают.
- Q6-навигация (семантическая маршрутизация) — уникальная черта, не описанная в стандартных
  agent-frameworks.

**Уровни 3-4** (реальная межагентная коммуникация, branching memory, phase-aware режимы)
требуют отдельной реализации. Они описаны в `double_triangle_foundation.md` и являются
естественным продолжением текущей архитектуры.

---

*Смежные документы:*
- `docs/sessions/ai_distributed_teams.md` — исходная теория агентной иерархии (Q6=110100)
- `docs/sessions/double_triangle_foundation.md` — Double-Triangle и features для уровней 3-4 (Q6=110001)
- `PORTAL-PROTOCOL.md` §4, §6 — формальная спецификация BaseAdapter и консенсус-алгоритма
- `docs/ADAPTER_ROADMAP.md` — следующие адаптеры-специалисты для добавления
