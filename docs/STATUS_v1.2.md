# Nautilus Portal — Технический статус v1.2

**Дата:** 2026-04-19  **Ветка:** `claude/review-nautilus-changes-tdywx`

---

## Метрики кода

| Показатель | Значение |
|-----------|---------|
| Python LOC | **8 733** |
| Адаптеров | **14** |
| Паспортов | **12** |
| Записей в портале | **217** |
| Кросс-ссылок | **317** (0 битых) |
| Мостов (bridges) | **33** |
| TF-IDF индекс | **207** документов |
| Тестов | **60 / 60** ✅ |
| mypy ошибок | **0** ✅ |
| Внешних зависимостей | **0** (stdlib only) |

---

## Адаптеры (14 штук)

| Имя | Репо | Тип | Q6 |
|-----|------|-----|-----|
| info1 | svend4/info1 | статические | 100001 |
| pro2 | svend4/pro2 | статические | 110011 |
| meta | svend4/meta | статические | 000100 |
| data2 | svend4/data2 | статические | 001000 |
| data7 | svend4/data7 | граф знаний | 110001 |
| infosystems | svend4/pro2 | домен | 101001 |
| ai_agents | svend4/pro2 | домен | 110100 |
| **graphrag** | svend4/infom | новый | 110001 |
| **daten22** | svend4/daten22 | новый | 101010 |
| **legal** | svend4/soz150 | новый | 100010 |
| **continuum** | svend4/meta1 | новый | 110100 |
| **ai_research** | svend4/info3+4+30+100 | новый | 110100 |
| conversations | docs/ | конвертации | — |
| sessions | docs/sessions/ | конвертации | — |

---

## REST API — эндпоинты (11 штук)

```
GET  /api/query?q=<текст>           поиск с ранжированием
GET  /api/health                    диагностика (score 0–100)
GET  /api/links                     валидация ссылок
GET  /api/describe                  описание адаптеров
GET  /api/neighbors?q6=110001       Q6-соседи (Хэмминг)
GET  /api/bridge?id=<id>&hops=2     обход графа bridges
GET  /api/bridge_conflicts          Protocol 3: конфликты
GET  /api/bridge_summary            сводка bridges + closure
GET  /api/annotations?target=<id>  аннотации к записи
POST /api/annotations               добавить аннотацию
GET  /api/flags[?severity=warning]  Protocol 3: флаги
GET  /metrics                       Prometheus text/plain
```

---

## Изменения v1.1 → v1.2

- +5 адаптеров: graphrag, daten22, legal, continuum, ai_research
- +5 паспортов с типизированными bridges
- Bridge algebra v2.0: `invert`, `compose`, `transitive_closure`, `detect_conflicts`
- Annotation system: `AnnotationStore` (SQLite + in-memory), Protocol 3
- 3 новых API-эндпоинта (bridge*) + 3 annotation-эндпоинта
- TF-IDF пересобран: 207 документов
- `nautilus.json` bumped 1.1 → 1.2
