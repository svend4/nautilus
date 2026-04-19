---
title: "Руководство: сессионные документы в Nautilus"
q6: "110001"
type: "guide"
---

# Руководство по работе с сессионными документами

Эта папка содержит **8 тематических документов**, автоматически извлечённых из
большой Claude-сессии (42 обмена, ~1 МБ) с помощью `split_sessions.py`.

---

## Файлы и темы

| Файл | Тема | Обменов | Q6 |
|------|------|--------:|-----|
| `anthropic_vacancies.md` | 436 вакансий Anthropic в 16 кластерах | 1 | `100101` |
| `profile_role_matching.md` | Маппинг профиля svend4 на роли Anthropic | 3 | `111110` |
| `repos_analysis.md` | Анализ 70 GitHub-репозиториев, 4 кластера | 7 | `100101` |
| `ai_distributed_teams.md` | AI-управляемые команды: Вариант C + MMORPG | 5 | `110100` |
| `protocol_spec.md` | PORTAL-PROTOCOL.md v1.1 формальная спецификация | 5 | `010101` |
| `nautilus_development.md` | Разработка Nautilus Portal (ветки, STATUS, docs) | 17 | `101010` |
| `double_triangle_foundation.md` | Double-Triangle: модель Human-AI коллаборации | 2 | `110001` |
| `misc_exchanges.md` | Прочие фрагменты (GitHub token, короткие вопросы) | 2 | `000000` |

---

## Способ 1 — TF-IDF семантический поиск (рекомендован)

Лучшая точность для поиска по содержанию. Работает на уже построенном индексе.

```bash
# Перестроить индекс (включает все docs/ и docs/sessions/)
python tfidf_search.py --build-index

# Поиск по теме
python tfidf_search.py "MMORPG профессиональная работа"
python tfidf_search.py "мета-агент оркестрация"
python tfidf_search.py "консолидация репозиториев"
python tfidf_search.py "double triangle human-ai"
python tfidf_search.py "вакансии anthropic sales"

# Топ-10 результатов + JSON-вывод
python tfidf_search.py "agent architecture" --top 10 --json
```

Результат включает:
- `[0.XXX]` — релевантность (cosine similarity)
- `Q6=XXXXXX` — тематическая координата раздела
- ID источника: `conv:ai_distributed_teams:6:...`

---

## Способ 2 — ConversationAdapter (fuzzy-поиск через portal)

```python
from adapters.conversation import ConversationAdapter

# Поиск в сессионных файлах
sessions = ConversationAdapter("docs/sessions/")
results = sessions.fetch("мета-агент команда")

for r in results:
    print(f"[{r.metadata['q6']}]  {r.title}")
    print(f"  Файл: {r.metadata['file']}")
    print(f"  {r.content[:200]}")
    print()
```

---

## Способ 3 — Мультиадаптерный запрос через NautilusPortal

Самый мощный вариант: **сравнивает сессионные данные с основной базой** знаний
(pro2, info1, meta, data2, data7).

```python
from portal import NautilusPortal

portal = NautilusPortal()
# portal уже содержит sessions-адаптер (docs/sessions/)

result = portal.query("multi-agent orchestration")

print(f"Найдено: {len(result.entries)} записей из {len(result.sources)} источников")
for e in result.entries[:5]:
    print(f"  [{e.metadata.get('q6','?')}]  {e.title}  ← {e.source}")

# Консенсус: сколько адаптеров согласились?
if result.consensus:
    print(f"\nКонсенсус: {result.consensus['coverage']:.0%}")
    print(f"Найдено в: {result.consensus['present_in']}")
    print(f"Отсутствует в: {result.consensus['missing_in']}")
```

---

## Способ 4 — REST API (после запуска `python api.py`)

```bash
# Поиск по теме
curl "http://localhost:8080/api/query?q=mmorpg+команда&ranked=1"

# Найти Q6-соседей (семантически близкие темы)
# sessions Q6=110100 → соседи на расстоянии 1
curl "http://localhost:8080/api/neighbors?q6=110100&dist=1"

# Все адаптеры и их статус
curl "http://localhost:8080/api/describe"
```

---

## Способ 5 — Сравнение с основной базой (консенсус-запрос)

Полезно для проверки: есть ли концепт из сессии в основной базе знаний?

```python
from portal import NautilusPortal

portal = NautilusPortal()

# Концепт из сессии: "иерархические агенты"
result = portal.query("иерархические агенты")
consensus = portal.consensus("иерархические агенты")

print("Источники с реальными данными:", consensus["present_in"])
print("Только fallback:", consensus["present_in_fallback"])
print("Не найдено:", consensus["missing_in"])
print("Согласованный факт:", consensus["agreed"])

# Если agreed=False — концепт пока только в сессии,
# но не зафиксирован в info1/pro2/meta.
# Это сигнал: стоит добавить в основную базу.
```

---

## Как пересоздать файлы (при обновлении сессии)

```bash
# Если появился новый файл сессии
cp новый_файл.md docs/_raw_sessions.md

# Пересоздать тематические документы
python split_sessions.py

# Пересоздать TF-IDF индекс
python tfidf_search.py --build-index --no-cache
```

Или для другого файла:
```bash
python split_sessions.py --input "docs/другая_сессия.md" --out "docs/sessions2"
```

---

## Q6-навигация по темам

Используйте Q6-расстояние для поиска «соседних» тем:

| Q6 | Тема сессии | Семантически близко к |
|----|-------------|----------------------|
| `110100` | AI-команды, агенты | `ai_agents` адаптер, bidir_train |
| `101010` | Nautilus разработка | `data7`, архитектурные концепты |
| `111110` | Маппинг профиля | стратегия, синтез, α+4 в info1 |
| `100101` | Анализ / оценка | CA-класс IV (сложность), data2 |
| `010101` | Спецификация протокола | pro2 Q6-граф, code-level |
| `110001` | Double-Triangle | meta CA-правила, знание/онтология |

```python
from portal import q6_neighbors

# Найти Q6-координаты, семантически близкие к теме "AI-команды"
neighbors = q6_neighbors("110100", max_distance=1)
print("Q6-соседи:", neighbors)
# ['010100', '100100', '111100', '110000', '110101', '110110', '110111']
# → это темы: research (010100), meta-learning (110001), implementation (010101)
```

---

*Дата создания: 2026-04-19 · Источник: Claude.ai сессия · Скрипт: `split_sessions.py`*
