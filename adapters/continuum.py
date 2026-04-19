"""
ContinuumAdapter — адаптер для svend4/meta1 (Continuum).
Формат: детерминированный AI-рантайм, step-based execution.
Q6: 110100 (мультиагент / оркестрация).
"""

from .base import BaseAdapter, PortalEntry, fuzzy_match

# -----------------------------------------------------------------------
# Концепты Continuum (meta1)
# -----------------------------------------------------------------------

_CONCEPTS = [
    ("continuum:core",
     "Continuum — детерминированный AI-рантайм",
     "Continuum — архитектура AI-рантайма с детерминированным выполнением: "
     "каждый шаг (step) полностью воспроизводим при одинаковых входных данных. "
     "Устраняет недетерминизм LLM через explicit state machine + snapshot/restore. "
     "Ключевое отличие от AutoGen/CrewAI: нет скрытого состояния.",
     "110100",
     ["continuum:step", "continuum:state_machine", "ai_agents:self_train"],
     ["deterministic", "runtime", "reproducible", "ai"]),

    ("continuum:step",
     "Step — атомарная единица выполнения",
     "Step = (input_state, action, output_state, metadata). "
     "Каждый step имеет: явный тип (LLM_CALL | TOOL_USE | BRANCH | MERGE), "
     "входной контекст, выходной контекст, метаданные (timestamp, cost, tokens). "
     "Шаги формируют DAG выполнения, не линейную цепочку.",
     "110100",
     ["continuum:core", "continuum:dag", "daten22:daten22:planner"],
     ["step", "atomic", "dag", "execution"]),

    ("continuum:state_machine",
     "State Machine — явное управление состоянием",
     "Continuum реализует явный конечный автомат: состояния = snapshots контекста, "
     "переходы = steps. Snapshot позволяет: (1) откат на любой предыдущий checkpoint, "
     "(2) ветвление (A/B exploration), (3) параллельное выполнение независимых веток. "
     "Хранилище: SQLite или в памяти.",
     "110100",
     ["continuum:step", "continuum:snapshot"],
     ["state-machine", "snapshot", "rollback", "checkpoint"]),

    ("continuum:snapshot",
     "Snapshot — снимок состояния",
     "Snapshot захватывает полное состояние агента в момент времени: "
     "conversation history, tool results, intermediate outputs, cost counter. "
     "Используется для: debugging (что пошло не так?), "
     "optimization (сравнение стратегий), reproducibility (тесты).",
     "110100",
     ["continuum:state_machine", "continuum:core"],
     ["snapshot", "serialization", "debugging", "optimization"]),

    ("continuum:dag",
     "DAG выполнения (Execution Graph)",
     "Граф направленных ациклических зависимостей шагов. "
     "Узлы = steps, рёбра = зависимости данных. "
     "DAG позволяет: автоматическое обнаружение параллелизма, "
     "визуализацию потока данных, оптимизацию порядка выполнения.",
     "110100",
     ["continuum:step", "continuum:state_machine"],
     ["dag", "graph", "parallel", "dependency"]),

    ("continuum:vs_autogen",
     "Continuum vs AutoGen/CrewAI: детерминизм",
     "AutoGen/CrewAI: агенты общаются через LLM-вызовы, состояние неявное "
     "(в conversation history). Воспроизводимость = проблема. "
     "Continuum: каждый шаг явный, state explicit, replay точный. "
     "Цена: больше overhead на serialization. "
     "Преимущество: тестируемость, отладка, A/B comparison стратегий.",
     "110100",
     ["continuum:core", "ai_agents:self_train"],
     ["comparison", "autogen", "crewai", "determinism"]),

    ("continuum:nautilus_integration",
     "Continuum ↔ Nautilus: агентный рантайм",
     "Continuum как рантайм для Nautilus-агентов: "
     "каждый NautilusPortal.query() = один Step в Continuum DAG. "
     "Мета-координатор видит весь граф выполнения, может откатить или переиграть. "
     "BridgeRegistry конфликты → BRANCH step для human review. "
     "Ближайший аналог: daten22 Planner, но с AI-steps вместо задач.",
     "110100",
     ["continuum:core", "continuum:dag", "daten22:daten22:planner"],
     ["nautilus", "integration", "meta-coordinator", "portal"]),
]


class ContinuumAdapter(BaseAdapter):
    name = "continuum"
    REPO = "svend4/meta1"

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        results = []

        for cid, title, content, q6, links, tags in _CONCEPTS:
            if not q or q in title.lower() or q in content.lower() or any(q in t for t in tags) or fuzzy_match(q, title):
                results.append(PortalEntry(
                    id=cid,
                    title=title,
                    source=self.REPO,
                    format_type="concept",
                    content=content,
                    metadata={"q6": q6, "tags": tags},
                    links=links,
                    is_fallback=not bool(q),
                ))

        if not results:
            e = PortalEntry(
                id="continuum:core",
                title=_CONCEPTS[0][1],
                source=self.REPO,
                format_type="concept",
                content=_CONCEPTS[0][2],
                metadata={"q6": "110100"},
                links=_CONCEPTS[0][4],
                is_fallback=True,
            )
            return [e]

        return results[:6]

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "continuum",
            "native_unit": "Step (атомарная единица детерминированного выполнения)",
            "q6": "110100",
            "total_concepts": len(_CONCEPTS),
            "compatibility": 1,
            "description": "Детерминированный AI-рантайм: явный state machine, snapshot/restore, DAG выполнения",
        }
