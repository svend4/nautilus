"""
Info1Adapter — адаптер для svend4/info1.
Формат: Markdown-документы с α-уровнями абстракции (-4..+4).
"""

import json
import os
import urllib.parse
import urllib.request
from .base import BaseAdapter, PortalEntry


class Info1Adapter(BaseAdapter):
    name = "info1"
    REPO = "svend4/info1"

    ALPHA_MAP = {
        "онтология": +4, "философия": +3, "методология": +2,
        "руководства": +1, "концепция": 0, "спецификации": -1,
        "реализация": -2, "примеры": -3, "код": -4,
    }

    def _github_headers(self) -> dict:
        headers = {"User-Agent": "nautilus-portal/1.0"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def fetch(self, query: str) -> list[PortalEntry]:
        try:
            url = (
                f"https://api.github.com/search/code"
                f"?q={urllib.parse.quote(query)}+repo:{self.REPO}+language:Markdown"
            )
            req = urllib.request.Request(url, headers=self._github_headers())
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            results = []
            for item in data.get("items", [])[:5]:
                alpha = self._guess_alpha(item["path"])
                results.append(PortalEntry(
                    id=f"info1:{item['sha'][:8]}",
                    title=item["name"],
                    source=self.REPO,
                    format_type="document",
                    content=item.get("path", ""),
                    metadata={"alpha": alpha, "path": item["path"]},
                    links=[f"pro2:depth:{abs(alpha)}"],
                ))
            return results or self._static_entries()
        except Exception:
            return self._static_entries()

    def _guess_alpha(self, path: str) -> int:
        for keyword, alpha in self.ALPHA_MAP.items():
            if keyword in path.lower():
                return alpha
        return 0

    # Alpha level descriptions: int → (title, description, example_domain)
    # alpha → (title, description, domain, q6 bit pattern)
    _ALPHA_LEVELS = {
        -4: ("Код",         "Исходный код, скрипты, конкретные реализации",  "код",        "000000"),
        -3: ("Примеры",     "Примеры, туториалы, демонстрации",              "примеры",    "000001"),
        -2: ("Реализация",  "Детали реализации, компоненты, модули",         "реализация", "000011"),
        -1: ("Спецификации","Спецификации, API, форматы данных",             "спецификации","000111"),
         0: ("Концепция",   "Концепции, идеи, принципы",                     "концепция",  "010100"),
        +1: ("Руководства", "Руководства, процессы, методики",               "руководства","010111"),
        +2: ("Методология", "Методологии, системные подходы",                "методология","101010"),
        +3: ("Философия",   "Философские основания, аксиомы",                "философия",  "111110"),
        +4: ("Онтология",   "Онтологии, высший уровень абстракции",         "онтология",  "111111"),
    }

    def _alpha_entry(self, alpha: int) -> PortalEntry:
        title, desc, domain, q6 = self._ALPHA_LEVELS.get(alpha, (f"α={alpha}", "", "", "010100"))
        return PortalEntry(
            id=f"info1:alpha:{alpha}",
            title=f"α={alpha:+d} · {title}",
            source=self.REPO,
            format_type="document",
            content=f"Уровень абстракции α={alpha}: {desc}.",
            metadata={"alpha": alpha, "domain": domain, "q6": q6},
            links=["info1:methodology"],
            is_fallback=True,
        )

    def _static_entries(self) -> list[PortalEntry]:
        base = [
            PortalEntry(
                id="info1:methodology",
                title="Методология ⇑⇓↔",
                source=self.REPO,
                format_type="document",
                content=(
                    "Параллельное двунаправленное развитие. "
                    "8 уровней абстракции (α=-4..+4). 74 документа, 1156 связей."
                ),
                metadata={"alpha": +2, "path": "README.md#methodology", "q6": "101010"},
                links=["pro2:bidir", "meta:hexagram:50"],
                is_fallback=True,
            ),
            PortalEntry(
                id="info1:cards",
                title="Карточная система",
                source=self.REPO,
                format_type="document",
                content=(
                    "Карточки как атомарные единицы знания. "
                    "8 типов карточек. Аналог концептов Q6 в pro2."
                ),
                metadata={"alpha": -1, "path": "02-Информационная-система/", "q6": "000111"},
                links=["pro2:concept:knowledge"],
                is_fallback=True,
            ),
        ]
        # Add alpha-level index entries so links like info1:alpha:3 resolve
        for alpha in self._ALPHA_LEVELS:
            base.append(self._alpha_entry(alpha))
        return base

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "info1",
            "native_unit": "Markdown-документ с α-уровнем",
            "abstraction_range": "α от -4 (код) до +4 (онтология)",
            "total_docs": "74+",
            "total_links": 1156,
        }
