# Annotation System — Double-Triangle Protocol 3

**Версия:** 1.0 MVP  **Дата:** 2026-04-19  **Файл:** `annotations.py`

---

## Концепция

Аннотации — первый класс данных в Nautilus. Любой участник может аннотировать любую запись `PortalEntry` независимо от источника: юридический документ, концепт, исследовательская заметка — всё аннотируется одинаково.

**Protocol 3** — подмножество: агент-адаптер автоматически ставит флаг `needs_review`, когда обнаруживает проблему, требующую внимания человека.

---

## Структуры данных

### `Annotation`
```python
id: str              # "annot:b6211e6e7e7f"
target: str          # id PortalEntry
author: str          # "svend4" | "legal" | "assistant"
content: str         # текст аннотации
visibility: str      # "private" | "team" | "public"
created_at: float    # unix timestamp
tags: list[str]      # произвольные теги
thread_parent: str   # id родительской аннотации (threading)
```

### `ConversationBranch`
```python
id: str              # "branch:abc123"
parent_message_id: str
title: str
purpose: str
status: str          # "active" | "merged" | "abandoned"
messages: list[dict]
merge_result: str
```

---

## API портала

```python
portal.annotate(target, author, content, visibility="private", tags=[])
portal.annotations_for(target, visibility=None, author=None)
portal.flag_for_review(target, author, reason, severity="warning")
portal.get_flags(severity=None)
portal.annotation_stats()
```

## REST API

```bash
GET  /api/annotations?target=pro2:bidir           все аннотации к записи
GET  /api/annotations?target=...&vis=team         фильтр по видимости
POST /api/annotations                              добавить аннотацию
     {"target":"pro2:bidir","author":"svend4","content":"..."}
GET  /api/flags                                   все Protocol-3 флаги
GET  /api/flags?severity=error                    только критические
```

---

## Хранилище (`AnnotationStore`)

| Режим | Когда | Описание |
|-------|-------|---------|
| SQLite (`annotations.db`) | По умолчанию | Персистентное, файл в корне |
| In-memory (`None`) | Тесты | `AnnotationStore(db_path=None)` |

Таблицы: `annotations` + `branches`. Индексы: по `target`, по `author`.

Файл `annotations.db` добавлен в `.gitignore`.

---

## Protocol 3 — автоматические флаги

Агент-адаптер флагирует запись:
```python
portal.flag_for_review(
    target="legal:dsgvo_art15",
    author="legal",
    reason="GDPR данные требуют проверки",
    severity="warning",       # "info" | "warning" | "error"
)
```

Результат: аннотация с `tags=["needs_review", "warning"]`, `visibility="team"`.

---

## Что не реализовано (roadmap)

- Нет UI для просмотра аннотаций в `portal.py --serve`
- Нет поиска по аннотациям (`/api/annotations/search`)
- `ConversationBranch` сохраняется в БД, но нет API-эндпоинтов для веток
- Нет авторизации — любой `author` принимается без проверки
