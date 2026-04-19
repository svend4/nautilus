"""
LegalAdapter — адаптер для svend4/soz150 (Writing OS).
Формат: юридические инструменты, социальное право, документы.
Q6: 100010 (анализ / правила / право).

Расширенные metadata-ключи (Humanities Extension):
  jurisdiction, valid_from, language, gdpr_contains_personal_data
"""

from .base import BaseAdapter, PortalEntry, fuzzy_match

# -----------------------------------------------------------------------
# Категории инструментов Writing OS (soz150)
# -----------------------------------------------------------------------

_TOOL_CATEGORIES = [
    ("writing:letters",
     "Письма и обращения",
     "Шаблоны официальных писем: обращения в органы власти, жалобы, апелляции, "
     "уведомления. 40+ шаблонов на немецком языке для немецкоязычных юрисдикций.",
     "100010",
     ["DE", "AT", "CH"],
     ["letter", "official", "complaint", "appeal"]),

    ("writing:sozialrecht",
     "Социальное право (Sozialrecht)",
     "Инструменты для работы с немецким социальным правом: SGB II, SGB XII, "
     "Grundsicherung, Wohngeld, BAföG. Включает калькуляторы пособий и "
     "генераторы заявлений.",
     "100010",
     ["DE"],
     ["sozialrecht", "sgb", "grundsicherung", "social", "benefits"]),

    ("writing:widerspruch",
     "Widerspruch (Апелляции)",
     "Шаблоны возражений (Widerspruch) против решений органов социального "
     "обеспечения. Структура: факты → правовое основание → требование. "
     "Поддерживает SGB II §44, §45, §48.",
     "100010",
     ["DE"],
     ["widerspruch", "appeal", "objection", "sgb2"]),

    ("writing:datenschutz",
     "Защита данных (Datenschutz / DSGVO)",
     "GDPR-инструменты: запросы на доступ к данным (Art. 15 DSGVO), "
     "требования об удалении (Art. 17), возражения против обработки (Art. 21). "
     "Шаблоны писем в немецкие органы надзора (DSK).",
     "100011",
     ["DE", "EU"],
     ["gdpr", "dsgvo", "datenschutz", "privacy", "data"]),

    ("writing:mietrecht",
     "Жилищное право (Mietrecht)",
     "Инструменты для арендаторов: уведомления о дефектах (Mängelanzeige), "
     "требования возврата залога, возражения против повышения аренды, "
     "расторжение договора. Актуально для BGB §§535-580a.",
     "100010",
     ["DE"],
     ["mietrecht", "rental", "bgb", "tenant"]),

    ("writing:budget",
     "Персональный бюджет (Persönliches Budget)",
     "Инструменты для получения персонального бюджета согласно SGB IX §29. "
     "Заявления, отчёты, протоколы переговоров с органами. "
     "Документация расходов и обоснование потребностей.",
     "100010",
     ["DE"],
     ["budget", "sgb9", "disability", "persönliches-budget"]),

    ("writing:templates",
     "Общие шаблоны документов",
     "300+ шаблонов документов: доверенности, согласия, протоколы, заявления. "
     "Форматы: Markdown, DOCX, PDF. Параметризованные через JavaScript. "
     "Поддержка переменных: {name}, {date}, {address}, {claim}.",
     "100010",
     ["DE", "AT", "CH", "EU"],
     ["template", "document", "docx", "pdf", "javascript"]),
]

# -----------------------------------------------------------------------
# Правовые концепты (узлы графа знаний)
# -----------------------------------------------------------------------

_LEGAL_CONCEPTS = [
    ("legal:sgb2",
     "SGB II — Grundsicherung für Arbeitsuchende",
     "Немецкий закон о базовом доходе для безработных. "
     "Регулирует: Bürgergeld (с 2023), Regelbedarf, Mehrbedarf, Kosten der Unterkunft. "
     "Ключевые параграфы: §7 (право на получение), §20 (стандартные нужды), "
     "§22 (жильё), §44 (обратная сила).",
     "100010",
     "DE", "2023-01-01", False,
     ["sgb2", "bürgergeld", "grundsicherung", "arbeitslosengeld"]),

    ("legal:dsgvo_art15",
     "DSGVO Art. 15 — Auskunftsrecht",
     "Право субъекта данных на получение информации об обрабатываемых персональных данных. "
     "Оператор обязан ответить в течение 1 месяца. "
     "При отказе — жалоба в надзорный орган (Datenschutzbehörde).",
     "100011",
     "EU", "2018-05-25", True,
     ["gdpr", "dsgvo", "art15", "auskunft", "data-access"]),

    ("legal:wohngeld",
     "Wohngeld — жилищное пособие",
     "Государственная субсидия на жильё для лиц с низким доходом (WoGG). "
     "Размер зависит от: числа членов домохозяйства, фактической аренды, дохода. "
     "Реформа 2023: расширение круга получателей, повышение выплат.",
     "100010",
     "DE", "2023-01-01", False,
     ["wohngeld", "housing", "subsidy", "wogg"]),

    ("legal:writing_os",
     "Writing OS — система создания правовых документов",
     "svend4/soz150: JavaScript-система из 300+ инструментов для автоматизации "
     "создания юридических документов. Концепция: 'операционная система письма' — "
     "каждый документ создаётся из модульных компонентов (header, claim, basis, request). "
     "Ориентирована на немецкое социальное право и права граждан.",
     "100010",
     "DE", "2024-01-01", False,
     ["writing-os", "soz150", "javascript", "legal-tools", "automation"]),
]


class LegalAdapter(BaseAdapter):
    name = "legal"
    REPO = "svend4/soz150"

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        results = []

        # Поиск по категориям инструментов
        for cid, title, content, q6, jurisdictions, tags in _TOOL_CATEGORIES:
            if not q or q in title.lower() or q in content.lower() or any(q in t for t in tags) or fuzzy_match(q, title):
                results.append(PortalEntry(
                    id=f"legal:{cid}",
                    title=title,
                    source=self.REPO,
                    format_type="document",
                    content=content,
                    metadata={
                        "q6": q6,
                        "tags": tags,
                        "jurisdiction": ", ".join(jurisdictions),
                        "language": "de",
                        "gdpr_contains_personal_data": False,
                    },
                    links=["legal:writing_os"],
                    is_fallback=False,
                ))

        # Поиск по правовым концептам
        for cid, title, content, q6, jurisdiction, valid_from, gdpr, tags in _LEGAL_CONCEPTS:
            if not q or q in title.lower() or q in content.lower() or any(q in t for t in tags) or fuzzy_match(q, title):
                results.append(PortalEntry(
                    id=cid,
                    title=title,
                    source=self.REPO,
                    format_type="document",
                    content=content,
                    metadata={
                        "q6": q6,
                        "tags": tags,
                        "jurisdiction": jurisdiction,
                        "valid_from": valid_from,
                        "language": "de",
                        "gdpr_contains_personal_data": gdpr,
                    },
                    links=["legal:writing_os"],
                    is_fallback=False,
                ))

        if not results:
            fb = self._fallback_entries()
            return fb

        if not q:
            # Без запроса: все концепты + первые 2 инструментальных категории
            concepts = [e for e in results if not e.id.startswith("legal:writing:")]
            tools = [e for e in results if e.id.startswith("legal:writing:")][:2]
            return concepts + tools

        return results[:8]

    def _fallback_entries(self) -> list[PortalEntry]:
        cid, title, content, q6, _, valid_from, gdpr, tags = _LEGAL_CONCEPTS[3]  # writing_os
        return [PortalEntry(
            id=cid, title=title, source=self.REPO,
            format_type="document", content=content,
            metadata={"q6": q6, "jurisdiction": "DE", "valid_from": valid_from,
                      "language": "de", "gdpr_contains_personal_data": gdpr, "tags": tags},
            links=[], is_fallback=True,
        )]

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "legal",
            "native_unit": "юридический инструмент / правовой документ",
            "q6": "100010",
            "total_tools": "300+",
            "total_categories": len(_TOOL_CATEGORIES),
            "jurisdictions": ["DE", "AT", "CH", "EU"],
            "language": "de",
            "compatibility": 1,
            "humanities_extension": ["jurisdiction", "valid_from", "language", "gdpr_contains_personal_data"],
            "description": "Writing OS: 300+ инструментов для немецкого социального права и прав граждан",
        }
