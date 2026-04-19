"""
GraphRAGAdapter — адаптер для svend4/infom.
Формат: Graph RAG — узлы знаний + рёбра семантических связей.
Q6: 110001 (семантика / онтология).
"""

from .base import BaseAdapter, PortalEntry, fuzzy_match

# -----------------------------------------------------------------------
# Граф концептов GraphRAG (статические записи по infom)
# -----------------------------------------------------------------------

# (id, title, content, q6, links, tags)
_GRAPH_NODES = [
    ("graphrag:pipeline",
     "GraphRAG Pipeline",
     "Полный конвейер граф-RAG: извлечение сущностей → построение графа знаний "
     "→ community detection → суммаризация → контекстный retrieval. "
     "Превосходит vanilla RAG на задачах с глобальными вопросами по корпусу.",
     "110001",
     ["graphrag:entity_extraction", "graphrag:community_detection", "pro2:q6"],
     ["rag", "graph", "pipeline", "retrieval"]),

    ("graphrag:entity_extraction",
     "Сущностное извлечение (Entity Extraction)",
     "NLP-этап: из сырого текста извлекаются сущности (люди, понятия, места) "
     "и отношения между ними. Используются LLM + NER. "
     "Результат: список (entity, type, description) + список (source, target, relation).",
     "110001",
     ["graphrag:pipeline", "graphrag:knowledge_graph"],
     ["nlp", "entity", "extraction", "ner"]),

    ("graphrag:knowledge_graph",
     "Граф знаний (Knowledge Graph)",
     "Направленный взвешенный граф: узлы = сущности, рёбра = отношения. "
     "Веса рёбер — частота совстречаемости + LLM-оценка семантической близости. "
     "Хранится в памяти (networkx) или персистентно (Neo4j, SQLite).",
     "110001",
     ["graphrag:entity_extraction", "graphrag:community_detection", "pro2:q6"],
     ["knowledge-graph", "graph", "networkx", "semantic"]),

    ("graphrag:community_detection",
     "Обнаружение сообществ (Community Detection)",
     "Алгоритм Leiden/Louvain делит граф на кластеры-сообщества. "
     "Каждое сообщество суммаризируется LLM — получается иерархический контекст. "
     "Уровни иерархии = разные степени обобщения.",
     "110001",
     ["graphrag:knowledge_graph", "graphrag:summarization"],
     ["leiden", "community", "clustering", "hierarchy"]),

    ("graphrag:summarization",
     "Суммаризация сообществ (Community Summarization)",
     "LLM генерирует summary для каждого community на каждом уровне иерархии. "
     "Global query использует суммари всех сообществ (map-reduce). "
     "Local query использует суммари ближайших узлов (vector similarity).",
     "110001",
     ["graphrag:community_detection", "graphrag:retrieval"],
     ["summarization", "llm", "map-reduce"]),

    ("graphrag:retrieval",
     "Граф-ориентированный Retrieval",
     "Два режима: (1) Global — вопрос → суммаризация всего графа → ответ. "
     "(2) Local — вопрос → ближайшие узлы → expand по рёбрам → контекст → ответ. "
     "Преимущество перед chunk-RAG: понимает структурные отношения между концептами.",
     "110001",
     ["graphrag:summarization", "graphrag:pipeline", "data7:theory:transformation"],
     ["retrieval", "global", "local", "rag"]),

    ("graphrag:vs_vanilla_rag",
     "GraphRAG vs Vanilla RAG: сравнение",
     "Vanilla RAG: текст → чанки → embedding → cosine similarity → top-k → LLM. "
     "GraphRAG: текст → граф → community summary → structured context → LLM. "
     "GraphRAG выигрывает на: (1) глобальных вопросах 'что общего у всего документа?', "
     "(2) multi-hop reasoning 'как A связано с C через B?'. "
     "Vanilla RAG лучше на точечных фактических вопросах.",
     "110001",
     ["graphrag:pipeline", "graphrag:retrieval"],
     ["comparison", "rag", "vanilla", "benchmark"]),

    ("graphrag:nautilus_bridge",
     "GraphRAG ↔ Nautilus Q6-граф",
     "Концептуальный мост: GraphRAG-граф знаний изоморфен Q6-пространству Nautilus. "
     "Узлы GraphRAG ↔ PortalEntry с Q6-координатами. "
     "Рёбра GraphRAG ↔ PortalEntry.links + bridge_type. "
     "Community detection ↔ Q6-кластеры (Hamming-шары). "
     "GraphRAGAdapter позволяет запрашивать граф через стандартный portal.query().",
     "110001",
     ["graphrag:knowledge_graph", "pro2:q6", "graphrag:retrieval"],
     ["nautilus", "bridge", "q6", "integration"]),

    ("graphrag:implementation",
     "Реализация: infom / GraphRAG",
     "Репозиторий svend4/infom содержит Python-реализацию GraphRAG. "
     "Ключевые файлы: graph_builder.py, community_detector.py, "
     "summarizer.py, query_engine.py. "
     "Зависимости: networkx, openai/anthropic API, numpy.",
     "110001",
     ["graphrag:pipeline"],
     ["implementation", "python", "infom", "svend4"]),
]


class GraphRAGAdapter(BaseAdapter):
    name = "graphrag"
    REPO = "svend4/infom"

    def fetch(self, query: str) -> list[PortalEntry]:
        q = query.lower()
        if not q:
            return [self._make(n) for n in _GRAPH_NODES]

        results = []
        for node in _GRAPH_NODES:
            _, title, content, _, _, tags = node
            if (q in title.lower() or q in content.lower()
                    or any(q in t for t in tags)
                    or fuzzy_match(q, title)):
                results.append(self._make(node))

        if not results:
            # Fallback: первые 3 записи
            results = [self._make(n) for n in _GRAPH_NODES[:3]]
            for e in results:
                e.is_fallback = True

        return results

    def _make(self, node: tuple) -> PortalEntry:
        nid, title, content, q6, links, tags = node
        return PortalEntry(
            id=nid,
            title=title,
            source=self.REPO,
            format_type="concept",
            content=content,
            metadata={"q6": q6, "tags": tags, "repo": self.REPO},
            links=links,
            is_fallback=False,
        )

    def describe(self) -> dict:
        return {
            "repo": self.REPO,
            "format": "graphrag",
            "native_unit": "граф-узел (сущность или концепт) + рёбра",
            "q6": "110001",
            "total_nodes": len(_GRAPH_NODES),
            "compatibility": 1,
            "description": "Graph RAG реализация: сущности, граф знаний, community detection, иерархическая суммаризация",
        }
