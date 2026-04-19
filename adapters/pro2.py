"""
Pro2Adapter — адаптер для svend4/pro2.
Формат: Q6-концепты (6-битное семантическое пространство), граф знаний.
"""

import json
import re
from pathlib import Path
from .base import BaseAdapter, PortalEntry


_REPO_ROOT = Path(__file__).parent.parent.parent


class Pro2Adapter(BaseAdapter):
    name = "pro2"
    REPO = "svend4/pro2"

    _LOCAL_LOG = _REPO_ROOT / "bidir_train_v2_log.json"
    _SELF_IMPROVEMENT = (
        _REPO_ROOT / "data" / "svend4_corpus" / "infosystems" / "info1" /
        "self_improvement_report.txt"
    )

    def fetch(self, query: str) -> list[PortalEntry]:
        results = []
        if self._LOCAL_LOG.exists():
            try:
                data = json.loads(self._LOCAL_LOG.read_text())
                results = self._search_log(query, data)
            except Exception:
                pass
        return results or self._static_entries()

    def _search_log(self, query: str, log: dict) -> list[PortalEntry]:
        results = []
        for key in ["final_stats", "training_summary", "domain_coverage"]:
            if key in log:
                results.append(PortalEntry(
                    id=f"pro2:log:{key}",
                    title=f"pro2 / {key}",
                    source=self.REPO,
                    format_type="concept",
                    content=str(log[key])[:300],
                    metadata={"log_key": key},
                    links=["info1:methodology", "meta:hexagram:50"],
                ))
        return results[:3]

    def _parse_self_improvement(self) -> dict | None:
        if not self._SELF_IMPROVEMENT.exists():
            return None
        text = self._SELF_IMPROVEMENT.read_text(encoding="utf-8")
        metrics = {}
        for key in ["CD", "VT", "CR", "DB"]:
            m = re.search(rf"{key}:\s+([\d.]+)%?", text)
            if m:
                metrics[key] = float(m.group(1))
        m_cycles = re.search(r"Циклов:\s+(\d+)", text)
        m_docs = re.search(r"Документов:\s+(\d+)", text)
        m_links = re.search(r"Связей:\s+(\d+)", text)
        if m_cycles:
            metrics["cycles"] = int(m_cycles.group(1))
        if m_docs:
            metrics["documents"] = int(m_docs.group(1))
        if m_links:
            metrics["connections"] = int(m_links.group(1))
        return metrics if metrics else None

    # Mapping of 6-bit patterns to semantic descriptions used across the ecosystem
    _Q6_LABELS = {
        "000000": ("Ката", "Зафиксированные паттерны движения", "I"),
        "000001": ("Архетипы", "Базовые архетипы движения ЕТД", "I"),
        "000010": ("Геймдизайн", "Игровые паттерны и механики", "I"),
        "000011": ("Петля", "Цикл, периодический паттерн", "II"),
        "000100": ("Алгоритмы", "Алгоритмические паттерны", "I"),
        "000110": ("7±2", "Мнемоническое ограничение Миллера", "II"),
        "000111": ("Три сферы", "Иерархия МВС/СВС/БВС", "II"),
        "001001": ("Нечётность", "Закон нечётности {1,3,5,7,9}", "II"),
        "010010": ("Шахматка", "Модульная тактическая сетка", "II"),
        "010100": ("Синтез I", "Единая теория синтез I", "II"),
        "010111": ("Возврат", "Поворотная точка, начало нового цикла", "IV"),
        "101000": ("Синтез II", "Конечный синтез II", "II"),
        "110001": ("Котёл", "Трансформация через огонь", "IV"),
        "110011": ("Резонанс", "ω_МВС = ω_СВС = ω_БВС → max", "IV"),
        "110100": ("Теория струн", "Физика высоких энергий", "IV"),
        "111110": ("Синтез", "Интеграция всех архетипов", "IV"),
        "111111": ("Финал", "Финальный синтез всех систем", "IV"),
        # Additional patterns from meta HEXAGRAM_TABLE
        "000101": ("Ожидание", "Терпение перед действием", "II"),
        "001000": ("Сдерживание", "Накопление силы через малое терпение", "II"),
        "001010": ("Мир", "Гармония неба и земли", "II"),
        "001011": ("Застой", "Разделение, блокировка", "III"),
        "001101": ("Великое владение", "Изобилие и ответственность", "II"),
        "010110": ("Разрушение", "Отслаивание, конец цикла", "III"),
        "011100": ("Бездна", "Опасность, которую нужно пройти", "III"),
        "011101": ("Огонь", "Прилипание, ясность, зависимость", "III"),
        "101001": ("Прибавление", "Рост через щедрость", "II"),
        "110000": ("Революция", "Преобразование в нужный момент", "IV"),
        "110010": ("Гром", "Пробуждение через потрясение", "III"),
        "110101": ("Изобилие", "Полнота накопленной силы", "II"),
        "111000": ("Ветер", "Мягкое проникновение", "II"),
        "111001": ("Радость", "Открытость, обмен", "II"),
    }

    def _q6_entry(self, bits: str) -> PortalEntry:
        label, desc, ca_class = self._Q6_LABELS.get(bits, (bits, f"Q6={bits}", "II"))
        alpha = {"I": -3, "II": -1, "III": +1, "IV": +3}.get(ca_class, 0)
        return PortalEntry(
            id=f"pro2:q6:{bits}",
            title=f"Q6={bits} · {label}",
            source=self.REPO,
            format_type="concept",
            content=desc,
            metadata={"q6": bits, "ca_class": ca_class, "alpha": alpha},
            links=[f"meta:hexagram:{int(bits, 2) + 1}", f"info1:alpha:{alpha}"],
            is_fallback=True,
        )

    def _static_entries(self) -> list[PortalEntry]:
        # is_fallback=True: эти записи возвращаются всегда, не только при совпадении
        entries = [
            PortalEntry(
                id="pro2:q6",
                title="Q6 Семантическое пространство",
                source=self.REPO,
                format_type="concept",
                content=(
                    "64 состояния (6-битное пространство). "
                    "Каждый концепт = координата Q6[b0..b5]. "
                    "Соответствует 64 гексаграммам И-Цзин."
                ),
                metadata={"dims": 6, "states": 64},
                links=["meta:hexagram:all", "info1:alpha:0"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:bidir",
                title="Bidirectional Training ⇑⇓ (замкнутый цикл)",
                source=self.REPO,
                format_type="concept",
                content=(
                    "ВПЕРЁД (специализация→обобщение): "
                    "Корпус→KnowledgeGraph→PageRank-центры→Q6-анкоры→Variant3GPT. "
                    "НАЗАД (обобщение→специализация): "
                    "GPT генерирует→QFilter оценивает→AdaptiveLearning обновляет граф"
                    "→identify_gaps()→generate_hypotheses()→новый корпус→снова вперёд. "
                    "Реализует НЕДОСТАЮЩУЮ ПЕТЛЮ из data7/knowledge_transformer.py."
                ),
                metadata={
                    "method": "bidirectional",
                    "file": "bidir_train.py",
                    "criterion": "модель генерирует тексты, граф признаёт 'достаточно центральными'",
                    "analogy": {
                        "data7:compute_centrality": "hex_weights",
                        "data7:identify_gaps": "domain_triplet_loss",
                        "data7:generate_hypotheses": "self_dialog stage 3",
                    },
                },
                links=["info1:methodology", "data7:missing_loop", "data7:theory:transformation"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:knowledge_graph",
                title="KnowledgeGraph — граф научных знаний",
                source=self.REPO,
                format_type="concept",
                content=(
                    "Аналог data7:KnowledgeGraph. "
                    "Отличие: рёбра взвешены качеством связи (обновляется AdaptiveLearning). "
                    "Типы рёбер: causes, extends, contradicts, related_to, is_a, part_of. "
                    "PageRank-центральность определяет Q6-анкоры для обучения."
                ),
                metadata={"file": "bidir_train.py", "class": "KnowledgeGraph"},
                links=["data7:concept", "data7:theory:transformation"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:adaptive_learning",
                title="AdaptiveLearning — динамический выбор концептов",
                source=self.REPO,
                format_type="concept",
                content=(
                    "Обновляет веса рёбер графа по результатам генерации GPT. "
                    "identify_gaps() ↔ domain_triplet_loss (из data7). "
                    "generate_hypotheses() ↔ self_dialog stage 3. "
                    "Критерий завершения: L_total = L_lm + α·L_domain + β·L_quality + γ·L_gate."
                ),
                metadata={
                    "file": "bidir_train.py",
                    "loss": "L_lm + 0.30*L_domain + 0.20*L_quality + 0.10*L_gate",
                },
                links=["data7:missing_loop", "pro2:bidir"],
                is_fallback=True,
            ),
            # Aliases and component entries referenced by other adapters
            PortalEntry(
                id="pro2:bidir_train",
                title="bidir_train.py — двунаправленное обучение",
                source=self.REPO,
                format_type="concept",
                content="Реализация замкнутого цикла forward+backward. Алиас pro2:bidir.",
                metadata={"file": "bidir_train.py"},
                links=["pro2:bidir"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:concept:knowledge",
                title="Концепт: Знание (Knowledge Graph)",
                source=self.REPO,
                format_type="concept",
                content="Узел типа 'knowledge' в Q6-пространстве. Связывает карточки info1 с граф-концептами pro2.",
                metadata={"q6": "000001", "domain": "knowledge"},
                links=["pro2:q6", "info1:methodology"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:moe",
                title="MoE — Mixture of Experts",
                source=self.REPO,
                format_type="concept",
                content="Смесь экспертов с доменной маршрутизацией. geometry/ffn.py: DomainMoE, 6 доменов.",
                metadata={"file": "geometry/ffn.py", "class": "DomainMoE"},
                links=["pro2:domain_routing", "infosystems:domain_moe"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:domain_routing",
                title="Domain Routing — доменная маршрутизация",
                source=self.REPO,
                format_type="concept",
                content="Маршрутизация токенов к специализированным экспертам по домену. Domain supervision loss.",
                metadata={"file": "geometry/ffn.py"},
                links=["pro2:moe"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:biangua",
                title="BianGuaTransform — навигация в Q6",
                source=self.REPO,
                format_type="concept",
                content="Преобразование гексаграмм: переход между категориями Q6-гиперкуба по Хэмминговому расстоянию.",
                metadata={"q6": True},
                links=["pro2:q6", "meta:hexagram:all"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:generate",
                title="AdvancedGenerator — генерация текста",
                source=self.REPO,
                format_type="concept",
                content="5 стратегий: greedy, nucleus, beam, speculative, dynamic_temp. inference/bridge_inference.py.",
                metadata={"file": "inference/bridge_inference.py", "strategies": 5},
                links=["pro2:speculative"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:speculative",
                title="Speculative Decoding — ускоренная генерация",
                source=self.REPO,
                format_type="concept",
                content="Draft model + verify: быстрая генерация с проверкой крупной моделью.",
                metadata={"file": "inference/bridge_inference.py"},
                links=["pro2:generate"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:hmoe",
                title="HMoE — иерархическая смесь экспертов",
                source=self.REPO,
                format_type="concept",
                content="Hierarchical MoE: эксперты CONCRETE→DYNAMIC→ABSTRACT. train_hmoe_curriculum.py.",
                metadata={"file": "train_hmoe_curriculum.py"},
                links=["pro2:moe", "pro2:domain_routing"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:nautilus",
                title="NautilusHierarchy — 7-камерная архитектура",
                source=self.REPO,
                format_type="concept",
                content="7 камер от микро до макро. Прогрессивная активация. geometry/nautilus.py.",
                metadata={"file": "geometry/nautilus.py", "chambers": 7},
                links=["pro2:six_sources"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:self_train",
                title="self_train.py — 3-стадийное самообучение",
                source=self.REPO,
                format_type="concept",
                content="Stage 0 (Q6 topology) → Stage 1 (RAG-buffer) → Stage 2 (filtered wild).",
                metadata={"file": "self_train.py", "stages": 3},
                links=["pro2:bidir"],
                is_fallback=True,
            ),
            PortalEntry(
                id="pro2:six_sources",
                title="Шесть источников (Six Sources)",
                source=self.REPO,
                format_type="concept",
                content="Шесть источников данных для обучения Nautilus: корпус, граф, архетипы, гексаграммы, Q6, ЕТД.",
                metadata={"sources": 6},
                links=["pro2:nautilus", "data2:etd"],
                is_fallback=True,
            ),
        ]
        # Add all Q6 bit-pattern entries
        for bits in self._Q6_LABELS:
            entries.append(self._q6_entry(bits))

        # Добавляем запись с метриками самосовершенствования если доступны
        si = self._parse_self_improvement()
        if si:
            cd_status = "⚠️" if si.get("CD", 0) > 20 else "✅"
            vt_status = "⚠️" if si.get("VT", 100) < 50 else "✅"
            entries.append(PortalEntry(
                id="pro2:self_improvement",
                title="Self-Improvement Metrics (info1, этап 6)",
                source=self.REPO,
                format_type="metrics",
                content=(
                    f"Документов: {si.get('documents', '?')} · "
                    f"Связей: {si.get('connections', '?')} · "
                    f"Циклов: {si.get('cycles', '?')}\n"
                    f"CD: {si.get('CD', '?')}% {cd_status} (цель: 20%) · "
                    f"VT: {si.get('VT', '?')}% {vt_status} (цель: 50%) · "
                    f"CR: {si.get('CR', '?')} ✅ · DB: {si.get('DB', '?')}% ✅\n"
                    f"Рекомендации: усилить ⇑⇓ связи, сократить ↔, "
                    f"создать ВЕРТИКАЛЬНАЯ-ТРАССИРУЕМОСТЬ.md"
                ),
                metadata=si,
                links=["info1:methodology", "pro2:bidir"],
            ))

        return entries

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "pro2",
            "native_unit": "Концепт с Q6-координатой",
            "abstraction_range": "Q6[b0..b5] = 64 состояния",
            "semantic_space": "6D бинарное пространство",
            "hexagram_mapping": "64 гексаграммы И-Цзин",
            "bidir_cycle": "bidir_train.py — замкнутый цикл (реализует data7 missing loop)",
        }
