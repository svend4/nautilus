"""
AIResearchAdapter — объединённый адаптер для svend4/info3, info4, info30, info100.
Формат: методология AI-агентов, паттерны исследований.
Q6: 110100 (мультиагент / оркестрация).
"""

from .base import BaseAdapter, PortalEntry, fuzzy_match

# -----------------------------------------------------------------------
# Источники (4 репо объединены в один адаптер)
# -----------------------------------------------------------------------

_SOURCES = {
    "info3":   "svend4/info3",
    "info4":   "svend4/info4",
    "info30":  "svend4/info30",
    "info100": "svend4/info100",
}

# -----------------------------------------------------------------------
# Концепты агентной методологии (синтез из всех 4 репо)
# -----------------------------------------------------------------------

_CONCEPTS = [
    # --- info3: базовые паттерны агентов ---
    ("ai_research:react",
     "ReAct — Reasoning + Acting",
     "Паттерн ReAct: агент чередует Thought (рассуждение), Action (вызов инструмента), "
     "Observation (результат). Формирует Chain-of-Thought с tool use. "
     "Более надёжен, чем чистый CoT: агент может проверять промежуточные гипотезы.",
     "110100",
     "info3",
     ["ai_research:cot", "ai_agents:self_train"],
     ["react", "reasoning", "acting", "tool-use", "chain-of-thought"]),

    ("ai_research:cot",
     "Chain-of-Thought (CoT) prompting",
     "Техника: явное пошаговое рассуждение в prompt'е улучшает точность LLM "
     "на сложных задачах. Варианты: zero-shot CoT ('думай пошагово'), "
     "few-shot CoT (примеры рассуждений), Tree-of-Thought (ветвящиеся рассуждения).",
     "110100",
     "info3",
     ["ai_research:react", "ai_research:tot"],
     ["cot", "prompting", "reasoning", "llm"]),

    ("ai_research:tot",
     "Tree-of-Thoughts (ToT)",
     "Расширение CoT: вместо линейной цепочки — дерево рассуждений. "
     "Агент генерирует несколько вариантов на каждом шаге, оценивает их, "
     "выбирает лучший, backtrack при тупике. "
     "Аналог: BFS/DFS по пространству рассуждений.",
     "110101",
     "info3",
     ["ai_research:cot", "ai_research:mcts"],
     ["tot", "tree", "backtrack", "search"]),

    # --- info4: архитектуры мультиагентных систем ---
    ("ai_research:mas",
     "Multi-Agent Systems (MAS) — классификация",
     "Три архитектуры MAS: (1) Hierarchical — мета-агент координирует суб-агентов "
     "(= Nautilus Portal pattern), (2) Peer-to-peer — агенты равноправны, "
     "договариваются, (3) Market-based — агенты конкурируют за задачи через торги. "
     "Nautilus использует Hierarchical + Market (relevance ranking).",
     "110100",
     "info4",
     ["ai_research:react", "ai_agents:self_train"],
     ["mas", "multi-agent", "hierarchical", "peer-to-peer", "market"]),

    ("ai_research:tool_use",
     "Tool Use — вызов внешних инструментов",
     "Паттерн: LLM получает список инструментов (function signatures), "
     "решает какой вызвать, получает результат, продолжает рассуждение. "
     "Виды: calculator, web_search, code_exec, API_call, database_query. "
     "Ключевые вопросы: выбор инструмента, обработка ошибок, retry-логика.",
     "110100",
     "info4",
     ["ai_research:react", "ai_research:function_calling"],
     ["tools", "function-calling", "llm", "api"]),

    ("ai_research:function_calling",
     "Function Calling / Tool Schema",
     "Стандарт OpenAI/Anthropic: LLM возвращает структурированный JSON "
     "с именем функции и параметрами вместо текста. "
     "Позволяет детерминированно парсить tool calls. "
     "Anthropic tool_use: {'type': 'tool_use', 'name': ..., 'input': {...}}.",
     "110100",
     "info4",
     ["ai_research:tool_use"],
     ["function-calling", "json", "structured", "anthropic", "openai"]),

    # --- info30: паттерны поиска и оптимизации ---
    ("ai_research:mcts",
     "Monte Carlo Tree Search (MCTS) в LLM-агентах",
     "Применение MCTS для улучшения рассуждений LLM: "
     "каждое рассуждение = узел дерева, expansion = генерация вариантов, "
     "simulation = оценка через LLM, backpropagation = обновление UCB-весов. "
     "Используется в AlphaCode, AlphaGeometry.",
     "110101",
     "info30",
     ["ai_research:tot", "ai_research:cot"],
     ["mcts", "monte-carlo", "search", "optimization"]),

    ("ai_research:self_reflection",
     "Self-Reflection и Self-Critique агентов",
     "Техника: агент критикует собственный output, затем улучшает его. "
     "Варианты: (1) Reflexion — агент ведёт verbal memory ошибок, "
     "(2) Constitutional AI — набор принципов для самокритики, "
     "(3) Critic model — отдельная модель оценивает ответы.",
     "110100",
     "info30",
     ["ai_research:react", "ai_agents:bidir"],
     ["reflection", "critique", "self-improvement", "constitutional-ai"]),

    # --- info100: синтез, перспективы ---
    ("ai_research:agent_memory",
     "Типы памяти AI-агентов",
     "Классификация памяти: (1) In-context — в prompt'е, ограничена окном, "
     "(2) External short-term — vector DB, retrieval по запросу, "
     "(3) External long-term — episodic memory (MemGPT), обновляется между сессиями, "
     "(4) Procedural — закодирована в весах модели (fine-tuning). "
     "Nautilus sessions/ = external long-term memory для Claude.",
     "110100",
     "info100",
     ["ai_research:mas", "graphrag:retrieval"],
     ["memory", "vector-db", "episodic", "long-term", "memgpt"]),

    ("ai_research:agentic_workflow",
     "Agentic Workflow — паттерны оркестрации",
     "4 базовых паттерна (Anthropic, 2024): "
     "(1) Prompt Chaining — шаги последовательно, (2) Routing — выбор ветки, "
     "(3) Parallelization — параллельные субзадачи, "
     "(4) Orchestrator-Subagents — иерархия (= Nautilus). "
     "Сложные системы = комбинация паттернов.",
     "110100",
     "info100",
     ["ai_research:mas", "ai_agents:self_train", "continuum:dag"],
     ["workflow", "orchestration", "anthropic", "patterns", "agentic"]),

    ("ai_research:nautilus_pattern",
     "Nautilus как реализация агентного паттерна",
     "Nautilus Portal реализует Orchestrator-Subagents паттерн (Anthropic 2024): "
     "NautilusPortal = Orchestrator, BaseAdapter = Subagent contract, "
     "fetch() = subagent call, PortalEntry = message protocol. "
     "Дополнительно: Q6-routing (семантическая маршрутизация), "
     "BridgeRegistry (typed cross-agent links), consensus (voting). "
     "Уникальность: явная семантическая координата каждого агента.",
     "110100",
     "info100",
     ["ai_research:agentic_workflow", "ai_research:mas"],
     ["nautilus", "orchestrator", "subagents", "q6", "unique"]),
]


class AIResearchAdapter(BaseAdapter):
    name = "ai_research"
    REPO = "svend4/info3+info4+info30+info100"

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        results = []

        for cid, title, content, q6, source_repo, links, tags in _CONCEPTS:
            if not q or q in title.lower() or q in content.lower() or any(q in t for t in tags) or fuzzy_match(q, title):
                full_source = _SOURCES.get(source_repo, source_repo)
                results.append(PortalEntry(
                    id=cid,
                    title=title,
                    source=full_source,
                    format_type="concept",
                    content=content,
                    metadata={"q6": q6, "tags": tags, "sub_repo": source_repo},
                    links=links,
                    is_fallback=not bool(q),
                ))

        if not results:
            # Fallback: паттерн Nautilus и agentic workflow
            for cid, title, content, q6, source_repo, links, tags in _CONCEPTS[-2:]:
                results.append(PortalEntry(
                    id=cid, title=title,
                    source=_SOURCES.get(source_repo, source_repo),
                    format_type="concept", content=content,
                    metadata={"q6": q6, "tags": tags},
                    links=links, is_fallback=True,
                ))
            return results

        if not q:
            return results[:5]

        return results[:8]

    def describe(self) -> dict:
        return {
            "repos": list(_SOURCES.values()),
            "format": "ai_research",
            "native_unit": "агентный паттерн / методология",
            "q6": "110100",
            "total_concepts": len(_CONCEPTS),
            "compatibility": 1,
            "sub_repos": list(_SOURCES.keys()),
            "description": "Методология AI-агентов: ReAct, CoT, ToT, MAS, Tool Use, Memory, Agentic Workflow",
        }
