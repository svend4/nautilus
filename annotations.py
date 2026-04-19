"""
annotations.py — система аннотаций Nautilus (Double-Triangle, Protocol 3).

Реализует концепцию из double_triangle_foundation.md:
  «Каждый participant может annotate любой PortalEntry:
   добавить personal note, flag for attention, link to related concept.»

Аннотации переносимы между источниками — annotate PortalEntry независимо
от того, это юридический документ, код, или концепт.

Хранилище: SQLite (файл annotations.db) или in-memory (для тестов).
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Annotation:
    """
    Аннотация к PortalEntry.

    Атрибут author может быть:
      - именем пользователя ("svend4")
      - именем адаптера-агента ("legal", "graphrag")  — Protocol 3
      - "assistant" — аннотация Claude
    """
    id: str
    target: str                   # id PortalEntry, который аннотируется
    author: str                   # "svend4" | adapter-name | "assistant"
    content: str                  # текст аннотации
    visibility: str               # "private" | "team" | "public"
    created_at: float             # unix timestamp
    tags: list[str] = field(default_factory=list)
    thread_parent: str | None = None   # id родительской аннотации (threading)

    @classmethod
    def new(
        cls,
        target: str,
        author: str,
        content: str,
        visibility: str = "private",
        tags: list[str] | None = None,
        thread_parent: str | None = None,
    ) -> "Annotation":
        return cls(
            id=f"annot:{uuid.uuid4().hex[:12]}",
            target=target,
            author=author,
            content=content,
            visibility=visibility,
            created_at=time.time(),
            tags=tags or [],
            thread_parent=thread_parent,
        )

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_iso"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.created_at)
        )
        return d


@dataclass
class ConversationBranch:
    """
    Ветка разговора (git-like branching для conversations).

    Из double_triangle_foundation.md:
    «Fork разговора в специфической точке,
     annotate branch для последующего merge,
     compare результаты branches.»
    """
    id: str
    parent_message_id: str        # точка ветвления
    title: str
    purpose: str
    status: str                   # "active" | "merged" | "abandoned"
    created_at: float
    messages: list[dict] = field(default_factory=list)
    merge_result: str | None = None

    @classmethod
    def new(
        cls,
        parent_message_id: str,
        title: str,
        purpose: str,
    ) -> "ConversationBranch":
        return cls(
            id=f"branch:{uuid.uuid4().hex[:12]}",
            parent_message_id=parent_message_id,
            title=title,
            purpose=purpose,
            status="active",
            created_at=time.time(),
        )

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "ts": time.time(),
        })

    def merge(self, result: str) -> None:
        self.status = "merged"
        self.merge_result = result

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_iso"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.created_at)
        )
        return d


# ---------------------------------------------------------------------------
# AnnotationStore
# ---------------------------------------------------------------------------

class AnnotationStore:
    """
    Хранилище аннотаций. Поддерживает SQLite (persistent) и dict (in-memory).

    Protocol 3 — автоматические аннотации от агентов:
      store.add(Annotation.new(
          target="legal:dsgvo_art15",
          author="legal",         # адаптер-агент
          content="⚠️ Требует проверки: GDPR-данные",
          tags=["needs_review", "gdpr"],
          visibility="team",
      ))
    """

    def __init__(self, db_path: str | Path | None = "annotations.db") -> None:
        self._in_memory = db_path is None
        if self._in_memory:
            self._mem: dict[str, Annotation] = {}
            self._branches: dict[str, ConversationBranch] = {}
        else:
            self._db_path = Path(db_path)
            self._init_db()

    # ------------------------------------------------------------------
    # Annotations CRUD
    # ------------------------------------------------------------------

    def add(self, ann: Annotation) -> str:
        """Save annotation. Returns annotation id."""
        if self._in_memory:
            self._mem[ann.id] = ann
        else:
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO annotations VALUES (?,?,?,?,?,?,?,?)",
                    (ann.id, ann.target, ann.author, ann.content,
                     ann.visibility, ann.created_at,
                     json.dumps(ann.tags, ensure_ascii=False),
                     ann.thread_parent),
                )
        return ann.id

    def get(self, ann_id: str) -> Annotation | None:
        if self._in_memory:
            return self._mem.get(ann_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM annotations WHERE id=?", (ann_id,)
            ).fetchone()
        return self._row_to_ann(row) if row else None

    def for_target(
        self,
        target: str,
        visibility: str | None = None,
        author: str | None = None,
    ) -> list[Annotation]:
        """All annotations on a given PortalEntry id."""
        if self._in_memory:
            anns = [a for a in self._mem.values() if a.target == target]
        else:
            q = "SELECT * FROM annotations WHERE target=?"
            params: list[Any] = [target]
            if visibility:
                q += " AND visibility=?";  params.append(visibility)
            if author:
                q += " AND author=?";      params.append(author)
            with self._conn() as conn:
                rows = conn.execute(q, params).fetchall()
            anns = [self._row_to_ann(r) for r in rows]
        if visibility:
            anns = [a for a in anns if a.visibility == visibility]
        if author:
            anns = [a for a in anns if a.author == author]
        return sorted(anns, key=lambda a: a.created_at)

    def thread(self, parent_id: str) -> list[Annotation]:
        """All replies to a given annotation id."""
        if self._in_memory:
            return [a for a in self._mem.values() if a.thread_parent == parent_id]
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM annotations WHERE thread_parent=?", (parent_id,)
            ).fetchall()
        return [self._row_to_ann(r) for r in rows]

    def search(self, query: str, visibility: str = "public") -> list[Annotation]:
        """Simple substring search in annotation content."""
        q = query.lower()
        if self._in_memory:
            return [a for a in self._mem.values()
                    if q in a.content.lower() and a.visibility == visibility]
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM annotations WHERE visibility=? AND content LIKE ?",
                (visibility, f"%{query}%"),
            ).fetchall()
        return [self._row_to_ann(r) for r in rows]

    def delete(self, ann_id: str) -> bool:
        if self._in_memory:
            return self._mem.pop(ann_id, None) is not None
        with self._conn() as conn:
            conn.execute("DELETE FROM annotations WHERE id=?", (ann_id,))
        return True

    def stats(self) -> dict[str, Any]:
        if self._in_memory:
            anns = list(self._mem.values())
        else:
            with self._conn() as conn:
                rows = conn.execute("SELECT * FROM annotations").fetchall()
            anns = [self._row_to_ann(r) for r in rows]
        by_author: dict[str, int] = {}
        by_vis: dict[str, int] = {}
        for a in anns:
            by_author[a.author] = by_author.get(a.author, 0) + 1
            by_vis[a.visibility] = by_vis.get(a.visibility, 0) + 1
        return {
            "total": len(anns),
            "by_author": by_author,
            "by_visibility": by_vis,
        }

    # ------------------------------------------------------------------
    # ConversationBranch CRUD
    # ------------------------------------------------------------------

    def add_branch(self, branch: ConversationBranch) -> str:
        if self._in_memory:
            self._branches[branch.id] = branch
        else:
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO branches VALUES (?,?,?,?,?,?,?,?)",
                    (branch.id, branch.parent_message_id, branch.title,
                     branch.purpose, branch.status, branch.created_at,
                     json.dumps(branch.messages, ensure_ascii=False),
                     branch.merge_result),
                )
        return branch.id

    def get_branch(self, branch_id: str) -> ConversationBranch | None:
        if self._in_memory:
            return self._branches.get(branch_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM branches WHERE id=?", (branch_id,)
            ).fetchone()
        return self._row_to_branch(row) if row else None

    def list_branches(self, status: str | None = None) -> list[ConversationBranch]:
        if self._in_memory:
            branches = list(self._branches.values())
        else:
            q = "SELECT * FROM branches"
            params: list[Any] = []
            if status:
                q += " WHERE status=?"; params.append(status)
            with self._conn() as conn:
                rows = conn.execute(q, params).fetchall()
            branches = [self._row_to_branch(r) for r in rows]
        if status:
            branches = [b for b in branches if b.status == status]
        return sorted(branches, key=lambda b: b.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Protocol 3 helpers
    # ------------------------------------------------------------------

    def flag_for_review(
        self,
        target: str,
        author: str,
        reason: str,
        severity: str = "warning",
    ) -> str:
        """Agent flags a PortalEntry for human review (Protocol 3)."""
        tags = ["needs_review", severity]
        ann = Annotation.new(
            target=target,
            author=author,
            content=f"[{severity.upper()}] {reason}",
            visibility="team",
            tags=tags,
        )
        return self.add(ann)

    def get_flagged(self, severity: str | None = None) -> list[Annotation]:
        """Return all Protocol-3 flags, optionally filtered by severity."""
        if self._in_memory:
            flags = [a for a in self._mem.values() if "needs_review" in a.tags]
        else:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM annotations WHERE tags LIKE '%needs_review%'"
                ).fetchall()
            flags = [self._row_to_ann(r) for r in rows]
        if severity:
            flags = [f for f in flags if severity in f.tags]
        return sorted(flags, key=lambda a: a.created_at, reverse=True)

    # ------------------------------------------------------------------
    # DB internals
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    visibility TEXT NOT NULL DEFAULT 'private',
                    created_at REAL NOT NULL,
                    tags TEXT DEFAULT '[]',
                    thread_parent TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_target ON annotations(target)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_author ON annotations(author)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS branches (
                    id TEXT PRIMARY KEY,
                    parent_message_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    messages TEXT DEFAULT '[]',
                    merge_result TEXT
                )
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    @staticmethod
    def _row_to_ann(row: tuple) -> Annotation:
        ann_id, target, author, content, visibility, created_at, tags_json, thread_parent = row
        return Annotation(
            id=ann_id, target=target, author=author, content=content,
            visibility=visibility, created_at=created_at,
            tags=json.loads(tags_json or "[]"),
            thread_parent=thread_parent,
        )

    @staticmethod
    def _row_to_branch(row: tuple) -> ConversationBranch:
        bid, parent_msg, title, purpose, status, created_at, msgs_json, merge_result = row
        return ConversationBranch(
            id=bid, parent_message_id=parent_msg, title=title, purpose=purpose,
            status=status, created_at=created_at,
            messages=json.loads(msgs_json or "[]"),
            merge_result=merge_result,
        )
