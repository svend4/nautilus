# Подключение репозиториев к Nautilus Portal

## Содержание

1. [Уровни совместимости](#уровни-совместимости)
2. [Требования к паспорту](#требования-к-паспорту)
3. [Структура адаптера](#структура-адаптера)
4. [Вариант A — ручной (5 минут)](#вариант-a--ручной)
5. [Вариант B — generate_passport.py](#вариант-b--generate_passportpy)
6. [Вариант C — nautilus.json в целевом репо](#вариант-c--nautilusjson-в-целевом-репо)
7. [Вариант D — scan_repo.py (авто-сканер)](#вариант-d--scan_repopy)
8. [Вариант E — GitHub Actions](#вариант-e--github-actions)
9. [Регистрация в портале](#регистрация-в-портале)
10. [Чеклист подключения](#чеклист-подключения)

---

## Уровни совместимости

| Уровень | Название | Что умеет | Что нужно |
|---------|----------|-----------|-----------|
| **0** | обнаруживаемый | Портал знает что репо существует | Только запись в `nautilus.json` |
| **1** | читаемый | Портал возвращает записи из репо | Адаптер со статическими данными |
| **2** | связанный | Записи содержат Q6-координаты и кросс-ссылки | Адаптер + заполненные `links` и `metadata.q6` |
| **3** | интерактивный | Живой поиск по репо через API | Адаптер + реальный fetch через GitHub API |

**Минимум для работы:** уровень 1. Уровень 2 делает репо полезным для всей экосистемы.

---

## Требования к паспорту

Паспорт — файл `passports/<format>.md`. Должен содержать:

### Обязательные поля

```markdown
# Паспорт: owner/repo-name

| Поле | Значение |
|------|----------|
| Репозиторий | owner/repo-name |
| Формат | `.myformat` — краткое описание |
| Единица | что является одной записью (документ, концепт, правило...) |
| Адаптер | `adapters/myformat.py` |
| Уровень совместимости | 1 — читаемый |
```

### Рекомендуемые разделы

```markdown
## Описание

Что хранит репо. 2-3 предложения.

## Объём

- Единиц: 74
- Связей: 1156

## Q6-отображение

Как концепты репо ложатся на 6-битное пространство.
Примеры:
  - "hex_id - 1 → bin(6)"
  - "alpha+4 → 3 старших бита"
  - "порядковый номер % 64 → bin(6)"
  - "не определено" — если связь с Q6 неочевидна

## Мосты к другим репозиториям

| Репо | Связь |
|------|-------|
| pro2 | ... ↔ ... |
| meta | ... ↔ ... |

## Примеры запросов

Запросы которые дают хорошие результаты:
- `knowledge`
- `синтез`
- `алгоритм`

## Доступ к данным

- Тип: static | github_api | http_api | local_files
- Требует токен: нет | да (GITHUB_TOKEN)
- Fallback: описание что происходит если данные недоступны
```

### Правила именования

```
passports/
  info1.md        ← по названию формата, не репо
  meta.md
  myformat.md     ← не my-repo.md

adapters/
  info1.py        ← то же имя
  meta.py
  myformat.py
```

---

## Структура адаптера

Минимальный рабочий адаптер (уровень 1):

```python
# adapters/myformat.py
from .base import BaseAdapter, PortalEntry


class MyformatAdapter(BaseAdapter):
    name = "myformat"           # уникальный идентификатор
    REPO = "owner/repo-name"    # GitHub slug

    def fetch(self, query: str) -> list[PortalEntry]:
        """Поиск по запросу. НЕ бросать исключения."""
        q = query.lower()
        results = [
            e for e in self._static_entries()
            if q in e.title.lower() or q in e.content.lower()
        ]
        return results or self._static_entries()[:2]  # fallback

    def _static_entries(self) -> list[PortalEntry]:
        return [
            PortalEntry(
                id="myformat:concept1",      # уникальный ID: format:slug
                title="Название концепта",
                source=self.REPO,
                format_type="document",      # document|concept|rule|theory
                content="Описание 1-3 предложения.",
                metadata={
                    "q6": "010011",          # 6-битная координата (если есть)
                    "alpha": 0,              # уровень абстракции (если есть)
                },
                links=[
                    "pro2:q6:010011",        # ссылка на концепт в другом репо
                    "meta:hexagram:20",      # формат: format:тип:id
                    "info1:alpha:0",
                ],
            ),
            # ... ещё 3-5 записей
        ]

    def describe(self) -> dict:
        """Метаданные адаптера для --describe."""
        return {
            "repo": self.REPO,
            "format": "myformat",
            "native_unit": "Markdown-документ",
            "total_items": "74+",
            "compatibility": 1,
        }
```

### Правила для `PortalEntry`

| Поле | Требование |
|------|-----------|
| `id` | `"format:slug"` — уникален в экосистеме |
| `title` | Короткое, информативное |
| `content` | 1-4 предложения, не HTML |
| `format_type` | `document`, `concept`, `rule`, `theory`, `schema`, `archetype` |
| `links` | Список ID из других репо: `"pro2:bidir"`, `"meta:hexagram:50"` |
| `metadata.q6` | 6-битная строка `"010011"` если есть отображение |

### Адаптер уровня 3 (живой поиск через GitHub API)

```python
import json, os, urllib.parse, urllib.request

class MyformatAdapter(BaseAdapter):
    name = "myformat"
    REPO = "owner/repo-name"

    def fetch(self, query: str) -> list[PortalEntry]:
        try:
            return self._github_search(query) or self._static_entries()
        except Exception:
            return self._static_entries()  # всегда fallback

    def _github_search(self, query: str) -> list[PortalEntry]:
        url = (
            "https://api.github.com/search/code"
            f"?q={urllib.parse.quote(query)}+repo:{self.REPO}+language:Markdown"
        )
        headers = {"User-Agent": "nautilus-portal/1.0"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        return [
            PortalEntry(
                id=f"myformat:{item['sha'][:8]}",
                title=item["name"],
                source=self.REPO,
                format_type="document",
                content=item.get("path", ""),
                metadata={"path": item["path"]},
                links=[],
            )
            for item in data.get("items", [])[:5]
        ]
```

---

## Вариант A — ручной

**Время:** 10–20 минут. Подходит если хорошо знаете репо.

```
1. Создать adapters/myformat.py  — скопировать шаблон выше, заполнить
2. Создать passports/myformat.md — заполнить по шаблону выше
3. Добавить в adapters/__init__.py:
       from .myformat import MyformatAdapter
4. Добавить в portal.py в NautilusPortal.__init__():
       "myformat": MyformatAdapter(),
5. Добавить запись в nautilus.json → registry[]
6. Проверить:
       python portal.py --describe
       python portal.py --query "ваш_запрос"
```

---

## Вариант B — generate_passport.py

**Время:** 2–5 минут. Генерирует заготовки, остаётся заполнить содержимое.

```bash
# Интерактивный режим (задаёт вопросы):
python generate_passport.py

# С параметрами + сразу создать адаптер:
python generate_passport.py \
  --repo owner/myrepo \
  --format myformat \
  --adapter

# Результат:
#   passports/myformat.md  ← заполнить разделы
#   adapters/myformat.py   ← заполнить _static_entries()

# Проверить существующие паспорта:
python generate_passport.py --list
python generate_passport.py --validate passports/myformat.md
```

После генерации остаётся вручную:
- Заполнить `_static_entries()` реальными концептами
- Дописать Q6-отображение в паспорте
- Добавить мосты к другим репо

---

## Вариант C — nautilus.json в целевом репо

**Идея:** репо объявляет себя совместимым с Nautilus сам, без изменений в nautilus.

### Шаг 1 — В целевом репо создать файл `nautilus.json`:

```json
{
  "nautilus_version": "1.0",
  "repo": "owner/myrepo",
  "format": "myformat",
  "native_unit": "Markdown-документ",
  "compatibility": 1,
  "description": "Краткое описание репозитория",
  "total_items": 50,
  "q6_key": "порядковый номер % 64 → bin(6)",
  "bridges": {
    "pro2": "концепты ↔ Q6-координаты",
    "meta": "категории ↔ CA-классы"
  },
  "example_queries": ["knowledge", "алгоритм"],
  "index": [
    {
      "id": "myformat:concept1",
      "title": "Название",
      "content": "Описание 1-2 предложения.",
      "q6": "010011",
      "links": ["pro2:q6:010011"]
    }
  ]
}
```

### Шаг 2 — В nautilus добавить `AutoAdapter`:

```python
# adapters/auto.py
import json, urllib.request, os
from .base import BaseAdapter, PortalEntry

class AutoAdapter(BaseAdapter):
    """Читает nautilus.json из корня любого GitHub-репо."""

    def __init__(self, repo: str):
        self.name = repo.split("/")[-1]
        self.REPO = repo
        self._data = self._fetch_nautilus_json()

    def _fetch_nautilus_json(self) -> dict:
        url = f"https://raw.githubusercontent.com/{self.REPO}/main/nautilus.json"
        try:
            headers = {"User-Agent": "nautilus-portal/1.0"}
            token = os.environ.get("GITHUB_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read())
        except Exception:
            return {}

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        index = self._data.get("index", [])
        results = [
            PortalEntry(
                id=item["id"],
                title=item["title"],
                source=self.REPO,
                format_type="document",
                content=item.get("content", ""),
                metadata={"q6": item.get("q6", "")},
                links=item.get("links", []),
            )
            for item in index
            if q in item["title"].lower() or q in item.get("content", "").lower()
        ]
        return results or [PortalEntry(
            id=f"{self.name}:overview",
            title=self._data.get("description", self.REPO),
            source=self.REPO,
            format_type="document",
            content=self._data.get("description", ""),
            metadata={},
            links=[],
        )]

    def describe(self) -> dict:
        return {k: v for k, v in self._data.items() if k != "index"}
```

### Шаг 3 — Авторегистрация в портале:

```python
# portal.py — добавить в NautilusPortal.__init__():
from adapters.auto import AutoAdapter

# Читать реестр авто-репо из nautilus.json
registry = json.loads(Path("nautilus.json").read_text())
for entry in registry.get("registry", []):
    if entry.get("adapter") == "auto":
        self.adapters[entry["repo"].split("/")[-1]] = AutoAdapter(entry["repo"])
```

```json
// nautilus.json — добавить запись:
{
  "repo": "owner/myrepo",
  "adapter": "auto",
  "compatibility": 1
}
```

**Плюсы:** ничего менять в nautilus не надо, репо регистрирует себя сам.  
**Минусы:** нужен интернет, медленнее статики, нет Q6-маппинга без `index`.

---

## Вариант D — scan_repo.py

**Идея:** скрипт анализирует репо через GitHub API и сам строит паспорт + адаптер.

```bash
python scan_repo.py owner/myrepo
# → passports/myrepo.md      (авто-заполнен по структуре)
# → adapters/myrepo.py       (статика из найденных файлов)
# → auto_report.json         (детальный отчёт)
```

**Что делает сканер:**

```
1. Читает дерево файлов через GitHub API (GET /repos/{owner}/{repo}/git/trees/main?recursive=1)
2. Определяет:
   - преобладающий тип файлов (.md, .py, .json, .txt...)
   - структуру директорий (src/, docs/, data/...)
   - количество файлов по типам
3. Читает README.md → извлекает описание (первые 3 абзаца)
4. Если есть существующий nautilus.json в репо → использует его
5. Генерирует паспорт с заполненными полями
6. Генерирует адаптер с записями из реальных файлов (первые 5)
```

**Псевдокод сканера:**

```python
def scan_repo(repo: str) -> dict:
    tree = github_api(f"/repos/{repo}/git/trees/main?recursive=1")
    files = [f for f in tree["tree"] if f["type"] == "blob"]

    # Тип контента
    extensions = Counter(Path(f["path"]).suffix for f in files)
    dominant_ext = extensions.most_common(1)[0][0]  # ".md", ".py" и т.д.

    # README
    readme = fetch_raw(f"{repo}/main/README.md")
    description = extract_first_paragraph(readme)

    # Проверить наличие nautilus.json в репо
    nautilus_json = try_fetch_raw(f"{repo}/main/nautilus.json")

    # Выбрать формат
    format_map = {".md": "markdown", ".py": "python", ".json": "json"}
    fmt = nautilus_json.get("format") if nautilus_json else format_map.get(dominant_ext, "text")

    # Примеры файлов как записи
    sample_files = [f for f in files if f["path"].endswith(dominant_ext)][:5]
    entries = [make_entry(repo, fmt, f) for f in sample_files]

    return {
        "repo": repo, "format": fmt,
        "description": description,
        "total_items": len(files),
        "entries": entries,
    }
```

Сканер — **отправная точка**, результат всё равно нужно проверить и уточнить Q6-маппинг вручную.

---

## Вариант E — GitHub Actions

**Идея:** при пуше в целевой репо — автоматически обновлять паспорт в nautilus.

### В целевом репо создать `.github/workflows/register_nautilus.yml`:

```yaml
name: Register with Nautilus

on:
  push:
    branches: [main]
    paths:
      - "nautilus.json"   # срабатывает только при изменении паспорта

jobs:
  register:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate nautilus.json
        run: |
          python -c "
          import json, sys
          d = json.load(open('nautilus.json'))
          required = ['repo','format','native_unit','compatibility']
          missing = [k for k in required if k not in d]
          if missing:
              print('Missing fields:', missing); sys.exit(1)
          print('OK:', d['repo'], 'compat=', d['compatibility'])
          "

      - name: Notify Nautilus Portal
        run: |
          curl -X POST https://api.github.com/repos/svend4/nautilus/dispatches \
            -H "Authorization: Bearer ${{ secrets.NAUTILUS_TOKEN }}" \
            -H "Accept: application/vnd.github+json" \
            -d '{"event_type":"repo_registered","client_payload":{"repo":"${{ github.repository }}"}}'
```

### В nautilus репо `.github/workflows/auto_update.yml`:

```yaml
name: Auto-update registry

on:
  repository_dispatch:
    types: [repo_registered]

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Scan and register
        run: |
          REPO="${{ github.event.client_payload.repo }}"
          python scan_repo.py "$REPO"
          python generate_passport.py --repo "$REPO" --adapter

      - name: Commit and push
        run: |
          git config user.name "nautilus-bot"
          git config user.email "bot@nautilus"
          git add passports/ adapters/
          git commit -m "Auto-register ${{ github.event.client_payload.repo }}" || echo "Nothing to commit"
          git push
```

**Плюсы:** полностью автоматически, без ручных действий в nautilus.  
**Минусы:** нужны GitHub токены с правами на оба репо, Q6-маппинг всё равно надо проверить.

---

## Регистрация в портале

После создания адаптера и паспорта — три файла требуют изменений:

### 1. `adapters/__init__.py`

```python
from .myformat import MyformatAdapter   # добавить эту строку

__all__ = [
    ...,
    "MyformatAdapter",                  # добавить в __all__
]
```

### 2. `portal.py`

```python
from adapters import (
    ...,
    MyformatAdapter,    # добавить импорт
)

class NautilusPortal:
    def __init__(self):
        self.adapters = {
            ...,
            "myformat": MyformatAdapter(),   # добавить адаптер
        }
```

### 3. `nautilus.json`

```json
{
  "registry": [
    ...,
    {
      "repo": "owner/myrepo",
      "adapter": "myformat",
      "format": "myformat",
      "compatibility": 1,
      "passport": "passports/myformat.md"
    }
  ]
}
```

### Проверка

```bash
# Описание всех адаптеров
python portal.py --describe

# Тест поиска
python portal.py --query "ваш_запрос"

# Проверить что новый адаптер отвечает
python -c "
from adapters.myformat import MyformatAdapter
a = MyformatAdapter()
results = a.fetch('knowledge')
print(f'{len(results)} записей')
for r in results:
    print(' ', r.id, '|', r.title)
"

# Валидация паспорта
python generate_passport.py --validate passports/myformat.md
```

---

## Чеклист подключения

```
ПАСПОРТ
[ ] passports/myformat.md создан
[ ] Все обязательные поля заполнены (repo, format, native_unit, compatibility)
[ ] Q6-отображение описано (или явно указано "не определено")
[ ] Мосты к другим репо заполнены
[ ] Примеры запросов добавлены

АДАПТЕР
[ ] adapters/myformat.py создан
[ ] fetch() возвращает list[PortalEntry], не бросает исключений
[ ] _static_entries() содержит 3-5 реальных концептов
[ ] describe() возвращает словарь с repo, format, native_unit
[ ] Каждый PortalEntry имеет уникальный id вида "myformat:slug"
[ ] links ссылаются на реальные ID из других адаптеров

РЕГИСТРАЦИЯ
[ ] adapters/__init__.py — импорт добавлен
[ ] portal.py — адаптер добавлен в self.adapters
[ ] nautilus.json — запись добавлена в registry

ПРОВЕРКА
[ ] python portal.py --describe  — новый адаптер виден
[ ] python portal.py --query "test" — возвращает записи нового репо
[ ] Кросс-ссылки работают (links из нового репо ведут в существующие)
```

---

## Сравнение вариантов

| Вариант | Время | Автоматизация | Качество результата |
|---------|-------|---------------|---------------------|
| A — ручной | 20 мин | нет | высокое |
| B — generate_passport.py | 5 мин | частичная | среднее (требует доработки) |
| C — nautilus.json в репо | 10 мин | авторегистрация | зависит от index |
| D — scan_repo.py | 2 мин | высокая | низкое (только структура) |
| E — GitHub Actions | настройка 30 мин | полная | низкое без Q6 |

**Рекомендуемый путь:** B → доработать вручную → в будущем C для новых репо.
