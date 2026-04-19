"""
MetaAdapter — адаптер для svend4/meta.
Формат: 256 CA-правил (Вольфрам) → 64 гексаграммы И-Цзин → Q6-координаты.
"""

from .base import BaseAdapter, PortalEntry


# Полная таблица 64 гексаграмм: id → (символ, имя, описание, CA-класс)
HEXAGRAM_TABLE = {
    1:  ("乾", "Творчество",       "Чистая созидательная сила",              "I"),
    2:  ("坤", "Исполнение",       "Принимающая сила, следование",           "I"),
    3:  ("屯", "Начальная трудность","Росток пробивается сквозь землю",       "II"),
    4:  ("蒙", "Незрелость",       "Учение через опыт",                      "II"),
    5:  ("需", "Ожидание",         "Терпение перед действием",               "II"),
    6:  ("訟", "Конфликт",         "Противостояние требует осторожности",    "III"),
    7:  ("師", "Армия",            "Организованная сила под руководством",   "II"),
    8:  ("比", "Единение",         "Сближение, поиск союзников",             "II"),
    9:  ("小畜", "Сдерживание",   "Накопление силы через малое терпение",   "II"),
    10: ("履", "Поступь",         "Движение по опасному пути с осторожностью","II"),
    11: ("泰", "Мир",              "Гармония неба и земли",                  "II"),
    12: ("否", "Застой",           "Разделение, блокировка",                 "III"),
    14: ("大有", "Великое владение","Изобилие и ответственность",            "II"),
    19: ("臨", "Приближение",      "Нарастание, прибытие, влияние",          "II"),
    21: ("噬嗑", "Прокусывание",   "Решительное устранение препятствия",     "II"),
    23: ("剥", "Разрушение",       "Отслаивание, конец цикла",               "III"),
    24: ("復", "Возврат",          "Поворотная точка, начало нового цикла",  "IV"),
    29: ("坎", "Бездна",           "Опасность, которую нужно пройти",        "III"),
    30: ("離", "Огонь",            "Прилипание, ясность, зависимость",       "III"),
    41: ("損", "Убывание",          "Уменьшение ради внутреннего роста",      "II"),
    42: ("益", "Прибавление",      "Рост через щедрость",                    "II"),
    49: ("革", "Революция",        "Преобразование в нужный момент",         "IV"),
    50: ("鼎", "Котёл",            "Трансформация через огонь",              "IV"),
    51: ("震", "Гром",             "Пробуждение через потрясение",           "III"),
    52: ("艮", "Гора",             "Неподвижность, медитация",               "I"),
    53: ("漸", "Постепенность",    "Медленный, устойчивый прогресс",         "II"),
    54: ("豐", "Изобилие",         "Полнота накопленной силы",               "II"),
    57: ("巽", "Ветер",            "Мягкое проникновение",                   "II"),
    58: ("兌", "Радость",          "Открытость, обмен",                      "II"),
    63: ("既濟", "После завершения","Равновесие достигнуто",                 "IV"),
    64: ("未濟", "До завершения",  "Движение к новому состоянию",            "IV"),
}

CA_CLASS_ALPHA = {"I": -3, "II": -1, "III": +1, "IV": +3}


class MetaAdapter(BaseAdapter):
    name = "meta"
    REPO = "svend4/meta"

    _CA_CLASS_DESCRIPTIONS = {
        "I":   ("Стационарные",  "Паттерны, сходящиеся к точкам или исчезающие. α=-3"),
        "II":  ("Периодические", "Паттерны с устойчивыми циклами и стабильными структурами. α=-1"),
        "III": ("Хаотические",   "Сложные, непредсказуемые паттерны. α=+1"),
        "IV":  ("Сложные",       "Структуры на грани хаоса и порядка (класс Вольфрама IV). α=+3"),
    }

    def _ca_class_entry(self, ca_class: str) -> PortalEntry:
        title, desc = self._CA_CLASS_DESCRIPTIONS.get(ca_class, (ca_class, ""))
        alpha = CA_CLASS_ALPHA.get(ca_class, 0)
        hexagrams = [hid for hid, (_, _, _, cls) in HEXAGRAM_TABLE.items() if cls == ca_class]
        return PortalEntry(
            id=f"meta:ca_class:{ca_class}",
            title=f"CA-класс {ca_class}: {title}",
            source=self.REPO,
            format_type="rule",
            content=f"{desc}. Гексаграммы: {', '.join(str(h) for h in sorted(hexagrams))}.",
            metadata={"ca_class": ca_class, "alpha": alpha, "hexagrams": sorted(hexagrams)},
            links=[f"info1:alpha:{alpha}"],
            is_fallback=True,
        )

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        hex_results = []
        for hex_id, (char, name, desc, ca_class) in HEXAGRAM_TABLE.items():
            if q in name.lower() or q in desc.lower() or q in char:
                hex_results.append(self._make_entry(hex_id, char, name, desc, ca_class))

        # Structural entries are always discoverable (needed for link resolution)
        index = self._index_entries()
        index_matches = [e for e in index
                         if q in e.title.lower() or q in e.content.lower() or q in e.id]
        # If nothing matched, use fallback hexagrams + all index entries
        if not hex_results and not index_matches:
            fallback = []
            for hex_id in [50, 63, 24, 1]:
                char, name, desc, ca_class = HEXAGRAM_TABLE[hex_id]
                e = self._make_entry(hex_id, char, name, desc, ca_class)
                e.is_fallback = True
                fallback.append(e)
            return (fallback + index)[:8]

        # Merge: hex matches first, then index matches
        seen = set()
        merged = []
        for e in hex_results:
            if e.id not in seen:
                seen.add(e.id)
                merged.append(e)
        for e in index_matches + index:
            if e.id not in seen:
                seen.add(e.id)
                merged.append(e)
        return merged

    def _index_entries(self) -> list[PortalEntry]:
        """Structural entries for CA classes, rules index, and hexagram overview."""
        entries = [
            PortalEntry(
                id="meta:hexagram:all",
                title="Все 64 гексаграммы (обзор)",
                source=self.REPO,
                format_type="rule",
                content=f"Полное пространство {len(HEXAGRAM_TABLE)} гексаграмм в таблице. 4 CA-класса Вольфрама.",
                metadata={"total": 64, "in_table": len(HEXAGRAM_TABLE)},
                links=["meta:ca_class:I", "meta:ca_class:II", "meta:ca_class:III", "meta:ca_class:IV"],
                is_fallback=True,
            ),
            PortalEntry(
                id="meta:hexagram",
                title="Гексаграммы И-Цзин",
                source=self.REPO,
                format_type="rule",
                content="64 гексаграммы как категориальная онтология. Каждая = вершина Q6-гиперкуба.",
                metadata={"total": 64},
                links=["pro2:q6", "meta:hexagram:all"],
                is_fallback=True,
            ),
            PortalEntry(
                id="meta:ca_rules",
                title="CA-правила (Клеточные Автоматы)",
                source=self.REPO,
                format_type="rule",
                content="256 правил элементарных клеточных автоматов Вольфрама → 4 класса сложности → 64 гексаграммы.",
                metadata={"total_rules": 256, "classes": 4},
                links=["meta:ca_class:I", "meta:ca_class:II", "meta:ca_class:III", "meta:ca_class:IV"],
                is_fallback=True,
            ),
        ]
        for ca_class in ["I", "II", "III", "IV"]:
            entries.append(self._ca_class_entry(ca_class))
        return entries

    def _make_entry(self, hex_id, char, name, desc, ca_class) -> PortalEntry:
        ca_rule = (hex_id - 1) * 4  # примерное соответствие
        q6_bits = format(hex_id - 1, "06b")
        alpha = CA_CLASS_ALPHA.get(ca_class, 0)
        return PortalEntry(
            id=f"meta:hexagram:{hex_id}",
            title=f"[{hex_id}] {char} {name}",
            source=self.REPO,
            format_type="rule",
            content=desc,
            metadata={
                "hexagram_id": hex_id,
                "char": char,
                "ca_rule": ca_rule % 256,
                "ca_class": ca_class,
                "q6": q6_bits,
                "alpha_equiv": alpha,
            },
            links=[
                f"pro2:q6:{q6_bits}",
                f"info1:alpha:{alpha}",
            ],
        )

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "meta",
            "native_unit": "CA-правило (0..255) + гексаграмма",
            "symbolic_space": "256 правил (классы I–IV по Вольфраму)",
            "hexagram_mapping": f"64 гексаграммы ({len(HEXAGRAM_TABLE)} в таблице)",
            "q6_formula": "hex_id - 1 → bin(6)",
        }
