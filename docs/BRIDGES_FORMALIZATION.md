---
title: "Формализация Bridges через Double-Triangle"
q6: "110001"
type: "specification"
source: "synthesis: double_triangle_foundation.md + PORTAL-PROTOCOL.md §7.3"
date: "2026-04-19"
---

# Формализация поля `bridges` через Double-Triangle

**Контекст:** `PORTAL-PROTOCOL.md §7.3` определяет `bridges` как «natural-language
descriptions», а формальная алгебра отложена до v2.0. Этот документ предлагает
конкретную схему формализации, основанную на Double-Triangle Architecture из
`docs/sessions/double_triangle_foundation.md`.

---

## Что такое Bridge в Double-Triangle

Из `double_triangle_foundation.md`:
> «Каждый специалист — Node со своими AI-assistant'ами.
> Annotations — infrastructure для Protocol 3 (assistant-to-meta negotiation).»

В терминах Double-Triangle **bridge** — это **рёбра между узлами**. Не мета-координатор
управляет ими сверху, а сами узлы декларируют связи с соседями. Мета-координатор
их обнаруживает и использует для навигации.

```
     NautilusPortal (meta)
    /       |        \
  pro2 ──bridge── meta    ← рёбра между узлами = bridges
    \               /
     ──────────────
           info1
```

Каждое ребро — это **семантическое отображение** между двумя форматами знания.
Например, bridge от `pro2` к `meta`: «Q6-биты `[b0..b5]` ↔ номер гексаграммы».

---

## Текущее состояние (v1.1)

Паспорта уже содержат `bridges` как dict строк:

```markdown
## Мосты к другим репо       ← passports/pro2.md

| Цель  | Связь |
|-------|-------|
| meta  | Q6-биты `[b0..b5]` ↔ номер гексаграммы |
| info1 | глубина концепта ↔ α-уровень |
| data7 | bidir_train ↔ K₀→K₁→K₂ цикл |
| data2 | scarab_algorithm ↔ Q6-траектория |
```

Проблемы текущего подхода:
1. Нет машиночитаемого формата — только markdown-таблица.
2. Нет типизации (bidirectional? directed? approximate?).
3. Нет оценки надёжности (сильная связь или гипотеза?).
4. Нет операций над bridges (compose, invert, traverse).

---

## Расширенная схема `bridges` (v1.2 proposal)

### Структура одного Bridge

```json
{
  "target": "meta",
  "direction": "bidirectional",
  "mapping": "Q6-bits [b0..b5] ↔ hexagram number (1..64)",
  "confidence": 0.95,
  "type": "isomorphism",
  "example": {
    "from": {"q6": "110100", "concept": "оркестрация"},
    "to":   {"hexagram": 42, "name": "Увеличение"}
  }
}
```

### Поля

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|---------|
| `target` | string | ✓ | Имя целевого адаптера/репо |
| `direction` | `"→"` \| `"←"` \| `"↔"` | ✓ | Направление отображения |
| `mapping` | string | ✓ | Human-readable описание правила |
| `confidence` | 0.0..1.0 | — | Надёжность (1.0 = доказанный изоморфизм) |
| `type` | string | — | Класс отображения (см. ниже) |
| `example` | object | — | Конкретный пример преобразования |

### Типы отображений (`type`)

| Тип | Описание | Пример |
|-----|----------|--------|
| `isomorphism` | Взаимно однозначное соответствие | Q6 ↔ гексаграмма |
| `projection` | Lossy: A → часть B | α-уровень → Q6 первые 3 бита |
| `embedding` | B полностью входит в A | soz150-инструменты ⊂ info1-иерархия |
| `analogy` | Структурная аналогия без изоморфизма | CA-правила ~ правовые нормы |
| `derivation` | B вычисляется из A детерминировано | bidir_train → K₀→K∞ |

---

## Реализация: Bridge как `PortalEntry.links`

Каждый bridge на уровне данных реализуется через поле `links` в `PortalEntry`:

```python
# adapters/base.py:14 — текущий PortalEntry
@dataclass
class PortalEntry:
    id: str           # "pro2:hexagram_42"
    links: list[str]  # ["meta:hexagram_42", "info1:concept_orchestration"]
    ...
```

**Правило именования ссылок:** `{target_adapter}:{target_id}`.

Мета-координатор превращает это в граф:

```python
# portal.py:152
def _cross_links(self, entries: list) -> list:
    links = []
    for e in entries:
        for link_id in e.links:
            sr = e.id.split(":")[0]
            tr = link_id.split(":")[0]
            if sr != tr:                # только межадаптерные ссылки
                links.append({"from": e.id, "to": link_id,
                               "from_repo": sr, "to_repo": tr})
    return links
```

`PortalResult.cross_links` — это граф bridges в действии.

---

## Операции над Bridges (v2.0 algebra)

Три базовые операции для формальной алгебры мостов:

### 1. Inversion (инверсия)

Если существует bridge `A → B`, то существует `B → A` (с той же confidence или ниже).

```python
def invert_bridge(bridge: dict) -> dict:
    inv_dir = {"→": "←", "←": "→", "↔": "↔"}
    return {**bridge,
            "target": bridge["source"],
            "source": bridge["target"],
            "direction": inv_dir[bridge["direction"]],
            "confidence": bridge.get("confidence", 1.0) * 0.9}  # небольшое снижение
```

### 2. Composition (транзитивность)

Если `A → B` и `B → C`, то `A → C` (confidence = min двух мостов).

```python
def compose_bridges(ab: dict, bc: dict) -> dict | None:
    if ab["target"] != bc["source"]:
        return None
    return {
        "source": ab["source"],
        "target": bc["target"],
        "direction": "→",
        "mapping": f"{ab['mapping']} | {bc['mapping']}",
        "confidence": min(ab.get("confidence", 1.0), bc.get("confidence", 1.0)),
        "type": "derivation",
    }
```

### 3. Traversal (обход)

`portal.query_by_bridge("pro2:42", max_hops=2)` — найти все концепты, достижимые
через цепочку bridges длиной ≤ 2.

```python
def query_by_bridge(self, entry_id: str, max_hops: int = 1) -> PortalResult:
    """Обход графа bridges из entry_id на глубину max_hops."""
    visited = {entry_id}
    frontier = [entry_id]
    all_entries = []
    for _ in range(max_hops):
        next_frontier = []
        for eid in frontier:
            # Найти все cross_links от eid
            for e in self._entries_by_id(eid):
                for link in e.links:
                    if link not in visited:
                        visited.add(link)
                        next_frontier.append(link)
                        all_entries.extend(self._entries_by_id(link))
        frontier = next_frontier
    return PortalResult(query=f"bridge:{entry_id}±{max_hops}",
                        entries=all_entries,
                        cross_links=self._cross_links(all_entries))
```

---

## Passport JSON-Schema (дополнение к v1.2)

Добавить в `passport_schema.json` рядом с текущим `bridges`:

```json
{
  "$defs": {
    "Bridge": {
      "type": "object",
      "required": ["target", "direction", "mapping"],
      "properties": {
        "target":     {"type": "string"},
        "direction":  {"type": "string", "enum": ["→", "←", "↔"]},
        "mapping":    {"type": "string", "minLength": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "type":       {"type": "string",
                       "enum": ["isomorphism", "projection",
                                "embedding", "analogy", "derivation"]},
        "example":    {"type": "object"}
      }
    }
  },
  "properties": {
    "bridges": {
      "type": "array",
      "items": {"$ref": "#/$defs/Bridge"}
    }
  }
}
```

### Обновлённый паспорт pro2 (пример миграции)

```json
{
  "repo": "svend4/pro2",
  "format": "pro2",
  "native_unit": "Q6-концепт с 6-битной координатой",
  "compatibility": 3,
  "bridges": [
    {
      "target": "meta",
      "direction": "↔",
      "mapping": "Q6-bits [b0..b5] ↔ hexagram number (1..64)",
      "confidence": 0.95,
      "type": "isomorphism"
    },
    {
      "target": "info1",
      "direction": "→",
      "mapping": "concept depth ↔ α-level (-4..+4)",
      "confidence": 0.7,
      "type": "projection"
    },
    {
      "target": "data7",
      "direction": "↔",
      "mapping": "bidir_train cycle ↔ K₀→K₁→K₂ transformation",
      "confidence": 0.8,
      "type": "derivation"
    }
  ]
}
```

---

## Связь с Double-Triangle Protocol 3

`double_triangle_foundation.md:311`:
> «Author может быть assistant — что enables Protocol 3 (assistant annotates when
> detecting issue requiring human attention)»

В контексте Bridges это означает: когда bridge traversal обнаруживает **contradictory
entries** (одно и то же понятие с разными Q6 в двух адаптерах), адаптер может
автоматически создать `Annotation` с флагом `needs_review`:

```python
# Будущая реализация Protocol 3 для bridges
@dataclass
class BridgeConflict:
    entry_a: str    # "pro2:hexagram_42"
    entry_b: str    # "meta:rule_110100"
    reason: str     # "Q6 coordinate mismatch: 110100 vs 110001"
    severity: str   # "info" | "warning" | "error"
```

Это сигнал для человека: мосты «согласны» или «конфликтуют» по данному концепту.

---

## Дорожная карта

| Этап | Компонент | Усилие | Предусловие |
|------|-----------|--------|-------------|
| **v1.2** | Расширенный JSON в паспортах | 2ч | Обновить 7 passport/*.md |
| **v1.2** | `_cross_links()` использует типы bridge | 1ч | Паспорта обновлены |
| **v2.0** | `invert_bridge()`, `compose_bridges()` | 4ч | — |
| **v2.0** | `portal.query_by_bridge(id, max_hops)` | 3ч | Formal algebra |
| **v2.0** | `BridgeConflict` + Protocol 3 annotations | 6ч | Annotation dataclass |

---

*Смежные документы:*
- `PORTAL-PROTOCOL.md §7.3` — текущее определение bridges (v1.1)
- `docs/sessions/double_triangle_foundation.md` — источник Double-Triangle модели (Q6=110001)
- `docs/AGENT_ARCHITECTURE_ANALOGY.md` — как bridges встраиваются в агентную иерархию
- `passports/pro2.md` — пример существующего паспорта с bridges
