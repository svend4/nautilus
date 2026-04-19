#!/usr/bin/env bash
# bootstrap.sh — инициализация репозитория для Nautilus Portal.
#
# Запуск в корне вашего репо:
#   curl -sL https://raw.githubusercontent.com/svend4/nautilus/main/bootstrap.sh | bash
#   # или локально:
#   bash bootstrap.sh
#
# Что делает:
#   1. Анализирует структуру текущего репо
#   2. Создаёт nautilus.json с index[]
#   3. Создаёт .github/workflows/register_nautilus.yml
#   4. Выводит инструкцию следующих шагов

set -e

NAUTILUS_REPO="svend4/nautilus"
RAW_BASE="https://raw.githubusercontent.com/${NAUTILUS_REPO}/main"

# ── Цвета ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
info() { echo -e "   $*"; }

echo ""
echo "⬡ Nautilus Portal Bootstrap"
echo "════════════════════════════"

# ── 1. Определить репо ────────────────────────────────────────────────────────
if git rev-parse --git-dir > /dev/null 2>&1; then
    REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ "$REMOTE" =~ github\.com[:/]([^/]+/[^/.]+) ]]; then
        REPO="${BASH_REMATCH[1]}"
    else
        REPO=""
    fi
else
    REPO=""
fi

if [ -z "$REPO" ]; then
    warn "Не удалось определить GitHub репо автоматически."
    read -p "Введите owner/repo-name: " REPO
fi

FORMAT=$(echo "${REPO##*/}" | tr '-.' '_')
ok "Репозиторий: $REPO  (формат: $FORMAT)"

# ── 2. Анализ структуры ───────────────────────────────────────────────────────
echo ""
info "Анализируем структуру репо..."

# Определить преобладающий тип файлов
MD_COUNT=$(find . -name "*.md" -not -path "./.git/*" 2>/dev/null | wc -l | tr -d ' ')
PY_COUNT=$(find . -name "*.py" -not -path "./.git/*" 2>/dev/null | wc -l | tr -d ' ')
JSON_COUNT=$(find . -name "*.json" -not -path "./.git/*" 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((MD_COUNT + PY_COUNT + JSON_COUNT))

info "Файлов: .md=$MD_COUNT  .py=$PY_COUNT  .json=$JSON_COUNT"

if [ "$MD_COUNT" -ge "$PY_COUNT" ] && [ "$MD_COUNT" -ge "$JSON_COUNT" ]; then
    DOMINANT="md"; NATIVE_UNIT="Markdown-документ"
elif [ "$PY_COUNT" -ge "$JSON_COUNT" ]; then
    DOMINANT="py"; NATIVE_UNIT="Python-модуль"
else
    DOMINANT="json"; NATIVE_UNIT="JSON-запись"
fi

info "Преобладающий формат: .$DOMINANT ($NATIVE_UNIT)"

# Извлечь описание из README
DESCRIPTION=""
for readme in README.md readme.md README.rst; do
    if [ -f "$readme" ]; then
        DESCRIPTION=$(python3 -c "
import re, sys
text = open('$readme').read()
lines = text.splitlines()
paragraphs = []
current = []
for line in lines:
    s = line.strip()
    if s.startswith('#'): continue
    if s:
        current.append(s)
    elif current:
        paragraphs.append(' '.join(current))
        current = []
if current:
    paragraphs.append(' '.join(current))
p = paragraphs[0] if paragraphs else ''
p = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', p)
p = re.sub(r'[*_\`]', '', p)
print(p[:200])
" 2>/dev/null || echo "")
        break
    fi
done

if [ -z "$DESCRIPTION" ]; then
    DESCRIPTION="$FORMAT репозиторий"
fi
info "Описание: ${DESCRIPTION:0:80}..."

# ── 3. Собрать index[] из файлов ─────────────────────────────────────────────
echo ""
info "Формируем index из первых 5 файлов..."

INDEX=$(python3 - <<EOF
import os, re
from pathlib import Path

ext = ".$DOMINANT"
files = sorted(
    [f for f in Path(".").rglob(f"*{ext}")
     if ".git" not in str(f) and "test" not in str(f).lower()],
    key=lambda f: f.stat().st_size, reverse=True
)[:5]

fmt = "$FORMAT"
index = []
for i, f in enumerate(files):
    name = f.stem.replace("-", " ").replace("_", " ").title()
    try:
        content = f.read_text(errors="replace")[:300].strip().replace("\n", " ")
        content = re.sub(r'#+ ', '', content)[:200]
    except Exception:
        content = str(f)
    q6 = format(i % 64, "06b")
    index.append(
        '    {\n'
        f'      "id": "{fmt}:{f.stem[:30]}",\n'
        f'      "title": "{name}",\n'
        f'      "content": {repr(content[:180])},\n'
        f'      "q6": "{q6}",\n'
        '      "links": []\n'
        '    }'
    )

print(",\n".join(index))
EOF
)

# ── 4. Создать nautilus.json ──────────────────────────────────────────────────
if [ -f "nautilus.json" ]; then
    warn "nautilus.json уже существует — создаём nautilus.json.new"
    OUTPUT="nautilus.json.new"
else
    OUTPUT="nautilus.json"
fi

cat > "$OUTPUT" <<JSONEOF
{
  "nautilus_version": "1.0",
  "repo": "$REPO",
  "format": "$FORMAT",
  "native_unit": "$NATIVE_UNIT",
  "compatibility": 1,
  "description": "$DESCRIPTION",
  "total_items": $TOTAL,
  "q6_key": "порядковый номер % 64 → bin(6)  (уточнить)",
  "bridges": {
    "pro2": "концепты ↔ Q6-координаты  (уточнить)",
    "meta":  "категории ↔ CA-классы    (уточнить)"
  },
  "example_queries": ["knowledge", "$FORMAT"],
  "access": {
    "type": "github_api",
    "requires_token": false,
    "fallback": "static_entries"
  },
  "index": [
$INDEX
  ]
}
JSONEOF

ok "Создан $OUTPUT"

# ── 5. Создать GitHub Actions workflow ────────────────────────────────────────
WORKFLOW_DIR=".github/workflows"
WORKFLOW_FILE="$WORKFLOW_DIR/register_nautilus.yml"

if [ -f "$WORKFLOW_FILE" ]; then
    warn "$WORKFLOW_FILE уже существует — пропускаем"
else
    mkdir -p "$WORKFLOW_DIR"
    curl -sL "$RAW_BASE/.github/workflows/register_nautilus.yml" \
         -o "$WORKFLOW_FILE" 2>/dev/null \
    && ok "Создан $WORKFLOW_FILE" \
    || warn "Не удалось скачать register_nautilus.yml — скопируйте вручную из svend4/nautilus"
fi

# ── 6. Итог ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
ok "Bootstrap завершён!"
echo ""
echo "Следующие шаги:"
echo ""
echo "  1. Откройте $OUTPUT и уточните:"
echo "     - q6_key: как ваши концепты отображаются на 6-бит"
echo "     - bridges: связи с другими репо экосистемы"
echo "     - index[].links: добавьте ссылки на концепты в других репо"
echo ""
echo "  2. Добавьте секрет NAUTILUS_TOKEN в настройки репо:"
echo "     Settings → Secrets → Actions → New repository secret"
echo "     Значение: Personal Access Token с правом repo на svend4/nautilus"
echo ""
echo "  3. Закоммитьте и запушьте:"
if [ "$OUTPUT" = "nautilus.json.new" ]; then
    echo "     mv nautilus.json.new nautilus.json"
fi
echo "     git add nautilus.json .github/workflows/register_nautilus.yml"
echo "     git commit -m 'feat: add Nautilus Portal passport'"
echo "     git push"
echo ""
echo "  4. GitHub Action автоматически уведомит svend4/nautilus."
echo "     Репо будет добавлено в экосистему в течение минуты."
echo ""
echo "  Документация: https://github.com/svend4/nautilus/blob/main/INTEGRATION.md"
