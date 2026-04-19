# Карта адаптеров: потенциальные источники для Nautilus

**Источник:** анализ 70 репозиториев svend4 (docs/sessions/repos_analysis.md)  
**Дата:** 2026-04-19  

Репозитории распределены по 4 кластерам. Те, что уже имеют адаптер, отмечены ✅.
Приоритет для нового адаптера определяется: уникальностью данных × Q6-покрытием × доступностью.

---

## Кластер 1: Legal / Sozialrecht (11 репо)

Тема: социальное право, юридические документы, бюджеты, права граждан.  
Q6-координата кластера: **`100010`** (анализ / правила / право)

| Репо | Статус | Данные | Приоритет адаптера |
|------|--------|--------|--------------------|
| `soz150` / Writing OS | Public | 300+ инструментов, JavaScript | 🔴 высокий — уникальный |
| `info50` | Public | Персональный бюджет | 🟡 средний |
| `soz120`, `soz50`, `soz7`, `soz140` | Private | Юридические документы | 🟢 низкий — private |
| `soz4`, `soz5`, `soz1`, `soz2`, `soz10`, `soz20` | Private | — | 🟢 низкий |

**Что нужно для адаптера:**
```python
# adapters/legal.py — читает soz150 через GitHub API или локальные файлы
class LegalAdapter(BaseAdapter):
    name = "legal"
    # format_type = "document"
    # Q6: документы по закону → область 100010-100011
    # bridges: {"info1": "α-уровень ↔ степень сложности закона"}
```

**Humanites Extension:** этот кластер требует дополнительных metadata-ключей:
`jurisdiction`, `valid_from`, `language`, `gdpr_contains_personal_data`.

---

## Кластер 2: Information OS / Rationalisation (≈20 репо)

Тема: операционная система мышления, рационализация, динамические планировщики.  
Q6-координата кластера: **`101010`** (архитектура / системы)

| Репо | Статус | Данные | Приоритет |
|------|--------|--------|-----------|
| `daten` ⭐1 | Public | Internet Function OS (Python) | 🔴 высокий — flagship |
| `daten4` ⭐1 | Public | Dynamic planner с AI | 🔴 высокий |
| `daten22` | Public | SQLite FTS4 RAG + 16 архетипов | 🔴 высокий — уникально |
| `universal-file-storage-mcp` ⭐1 | Public | MCP Registry, TypeScript | 🔴 высокий — shipping-ready |
| `daten1`, `daten5`, `daten7`, `daten12`, `daten14` | Public | Дубли / фрагменты | 🟢 низкий |
| `daten23`, `daten40`, `data30-40` | Public | Итерации концепции | 🟢 низкий — архивировать |

**Что нужно для адаптера:**
```python
# adapters/infoOS.py — читает daten/daten4/daten22
class InfoOSAdapter(BaseAdapter):
    name = "infoOS"
    # format_type = "concept"
    # Q6: рационализация / архитектура → 101010, 101011
    # bridges: {"pro2": "Function Registry ↔ Q6-граф концептов"}
```

---

## Кластер 3: AI / Agents / Novel Architectures (≈13 репо)

Тема: AI-агенты, нейросетевые архитектуры, граф-RAG, локальный inference.  
Q6-координата кластера: **`110100`** (мультиагент / оркестрация)

| Репо | Статус | Данные | Приоритет |
|------|--------|--------|-----------|
| `pro2` ⭐1 | Public | Q6-граф, YiJing-Transformer | ✅ адаптер есть |
| `meta` ⭐1 | Public | 256 CA-правил, гексаграммы | ✅ адаптер есть |
| `infom` / GraphRAG | Public | Graph RAG реализация | 🔴 высокий — горячая тема |
| `meta1` / Continuum | Public | Детерминированный AI рантайм | 🔴 высокий — уникально |
| `in4` | Public | Home AI clusters / prima.cpp | 🟡 средний |
| `in4n` | Public | Вариант in4 | 🟡 средний |
| `info3`, `info4`, `info30`, `info100` | Public | Agent methodology | 🟡 средний — объединить |
| `data7` ⭐1 | Public | K₀→K∞ трансформация, Meta-Orchestrator | ✅ адаптер есть |

**Что нужно для адаптера `graphrag`:**
```python
# adapters/graphrag.py — читает infom / GraphRAG
class GraphRAGAdapter(BaseAdapter):
    name = "graphrag"
    # format_type = "concept"
    # Q6: граф-знаний → 110001 (семантика / онтология)
    # bridges: {"data7": "graph traversal ↔ K₀→K∞",
    #           "pro2": "GraphRAG nodes ↔ Q6 vertices"}
```

---

## Кластер 4: Archives & Experiments (≈8 репо)

Тема: корпуса, теория движения, MMORPG-симулятор, энциклопедии.  
Q6-координата кластера: **`010100`** (исследование / теория)

| Репо | Статус | Данные | Приоритет |
|------|--------|--------|-----------|
| `data2` ⭐1 | Public | ЕТД Крюкова, робототехника | ✅ адаптер есть |
| `data7` ⭐1 | Public | Диссертации, энциклопедии, MMORPG | ✅ адаптер есть |
| `data70` | Public | ChatGPT corpus archive | 🟡 средний — JSONLAdapter |
| `info` | Public | Базовая информационная ОС | 🟢 низкий — архивировать |

**data70 можно подключить прямо сейчас через JSONLAdapter:**
```python
from adapters.jsonl import JSONLAdapter
portal.register("corpus", JSONLAdapter("path/to/data70/"))
```

---

## Сводная таблица приоритетов

| Приоритет | Репо | Усилие | Результат |
|-----------|------|--------|-----------|
| 🔴 1 | `infom` / GraphRAG | 3-4ч | Новый Q6-кластер `110001`, покрытие +5% |
| 🔴 2 | `daten22` (FTS4-RAG) | 2-3ч | JSONLAdapter или новый адаптер |
| 🔴 3 | `soz150` / Writing OS | 4-6ч | Первый юридический/гуманитарный адаптер |
| 🟡 4 | `meta1` / Continuum | 3-4ч | Уникальная ниша, ArxivAdapter-стиль |
| 🟡 5 | `info3/4/30/100` | 2-3ч | Объединить в один `ai_research` адаптер |
| 🟢 6 | `data70` | 30мин | `JSONLAdapter("data70/")` уже работает |

---

## Как создать новый адаптер (5 шагов)

```bash
# 1. Создать файл адаптера
cp adapters/jsonl.py adapters/my_adapter.py

# 2. Реализовать BaseAdapter (fetch + describe)
# 3. Назначить Q6 из таблицы выше
# 4. Зарегистрировать в portal.py
# 5. Добавить passport в passports/my_adapter.md
```

Полное руководство: [INTEGRATION.md](../INTEGRATION.md)  
Протокол: [PORTAL-PROTOCOL.md](../PORTAL-PROTOCOL.md) §5, §7, §8

---

*Следующий шаг: реализовать адаптер `graphrag` для `infom` — наибольший прирост Q6-покрытия.*
