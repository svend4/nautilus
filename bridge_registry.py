"""
BridgeRegistry — читает типизированные bridges из паспортов (v1.2).

Каждый паспорт (passports/*.md) может содержать секцию:

    ## Bridges (machine-readable)
    ```json
    [{"target": "...", "direction": "↔", "type": "isomorphism", ...}]
    ```

BridgeRegistry парсит эти блоки и предоставляет lookup по паре (source, target),
а также алгебру v2.0: инверсия, композиция, транзитивное замыкание, детекция конфликтов.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_BRIDGE_SECTION_RE = re.compile(
    r"##\s+Bridges\s+\(machine-readable\)\s*\n+```json\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)

_INV_DIR = {"→": "←", "←": "→", "↔": "↔"}


# ---------------------------------------------------------------------------
# BridgeConflict — Protocol 3 сигнал
# ---------------------------------------------------------------------------

@dataclass
class BridgeConflict:
    """
    Конфликт между двумя записями, которые декларируют bridge на одно понятие,
    но расходятся по Q6-координате или типу отображения.
    """
    entry_a: str          # "pro2:hexagram_42"
    entry_b: str          # "meta:rule_110100"
    from_repo: str
    to_repo: str
    reason: str           # описание расхождения
    severity: str         # "info" | "warning" | "error"

    def as_dict(self) -> dict[str, str]:
        return {
            "entry_a":   self.entry_a,
            "entry_b":   self.entry_b,
            "from_repo": self.from_repo,
            "to_repo":   self.to_repo,
            "reason":    self.reason,
            "severity":  self.severity,
        }


# ---------------------------------------------------------------------------
# BridgeRegistry
# ---------------------------------------------------------------------------

class BridgeRegistry:
    """
    Реестр типизированных мостов между адаптерами.

    Загружается один раз при старте портала.

    v1.2 API: get(), all_for(), annotate_link(), summary()
    v2.0 API: invert(), compose(), transitive_closure(), detect_conflicts()
    """

    def __init__(self, passports_dir: str | Path = "passports") -> None:
        self._passports_dir = Path(passports_dir)
        # {source_adapter: [bridge_dict, ...]}
        self._bridges: dict[str, list[dict[str, Any]]] = {}
        self._load()

    # ------------------------------------------------------------------
    # v1.2: basic lookup & annotation
    # ------------------------------------------------------------------

    def get(self, source: str, target: str) -> dict[str, Any] | None:
        """Return bridge metadata for the (source, target) pair, or None."""
        for b in self._bridges.get(source, []):
            if b.get("target") == target:
                return b
        # Auto-invert: check reverse direction
        for b in self._bridges.get(target, []):
            if b.get("target") == source and b.get("direction") in ("↔", "←"):
                return self.invert(b)
        return None

    def all_for(self, source: str) -> list[dict[str, Any]]:
        """Return all bridges declared by source adapter."""
        return list(self._bridges.get(source, []))

    def annotate_link(self, from_repo: str, to_repo: str) -> dict[str, Any]:
        """Bridge annotation dict for embedding in cross_links."""
        bridge = self.get(from_repo, to_repo)
        if bridge:
            return {
                "bridge_type":       bridge.get("type", "unknown"),
                "bridge_direction":  bridge.get("direction", "↔"),
                "bridge_mapping":    bridge.get("mapping", ""),
                "bridge_confidence": bridge.get("confidence"),
            }
        return {
            "bridge_type":       "unknown",
            "bridge_direction":  "↔",
            "bridge_mapping":    "",
            "bridge_confidence": None,
        }

    def summary(self) -> dict[str, Any]:
        """Summary of all loaded bridges."""
        total = sum(len(v) for v in self._bridges.values())
        by_type: dict[str, int] = {}
        for bridges in self._bridges.values():
            for b in bridges:
                t = b.get("type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
        return {
            "adapters_with_bridges": sorted(self._bridges.keys()),
            "total_bridges": total,
            "by_type": by_type,
        }

    # ------------------------------------------------------------------
    # v2.0: algebra — invert, compose, transitive_closure
    # ------------------------------------------------------------------

    @staticmethod
    def invert(bridge: dict[str, Any]) -> dict[str, Any]:
        """
        Инверсия bridge: A→B становится B→A.
        confidence слегка снижается (×0.95) чтобы отразить неточность инверсии.
        """
        inv = dict(bridge)
        inv["source"]    = bridge.get("target", "")
        inv["target"]    = bridge.get("source", "")
        inv["direction"] = _INV_DIR.get(bridge.get("direction", "↔"), "↔")
        if "confidence" in bridge:
            inv["confidence"] = round(bridge["confidence"] * 0.95, 3)
        inv["_inverted"] = True
        return inv

    @staticmethod
    def compose(ab: dict[str, Any], bc: dict[str, Any]) -> dict[str, Any] | None:
        """
        Транзитивная композиция A→B + B→C = A→C.
        Возвращает None если цепочка не соединяется.
        confidence = min(ab.confidence, bc.confidence).
        type = "derivation" (по умолчанию для составных мостов).
        """
        if ab.get("target") != bc.get("source"):
            return None
        conf_ab = ab.get("confidence", 1.0)
        conf_bc = bc.get("confidence", 1.0)
        return {
            "source":     ab.get("source", ""),
            "target":     bc.get("target", ""),
            "direction":  "→",
            "mapping":    f"{ab.get('mapping', '')} ▶ {bc.get('mapping', '')}",
            "confidence": round(min(conf_ab, conf_bc), 3),
            "type":       "derivation",
            "_composed":  True,
            "_via":       ab.get("target", ""),
        }

    def transitive_closure(
        self,
        source: str,
        max_hops: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Все bridges, достижимые из source за ≤ max_hops шагов.
        Включает прямые мосты (hop=1) и составные (hop=2+).
        Результат отсортирован по убыванию confidence.
        """
        found: dict[str, dict[str, Any]] = {}  # target → best bridge

        def _key(b: dict) -> str:
            return f"{b.get('source','')}→{b.get('target','')}"

        # Прямые (hop=1)
        for b in self._bridges.get(source, []):
            b2 = dict(b)
            b2.setdefault("source", source)
            b2["_hop"] = 1
            found[_key(b2)] = b2
            # Также добавляем инвертированные bidirectional как отдельные рёбра
            if b.get("direction") == "↔":
                inv = self.invert(b2)
                inv["_hop"] = 1
                found[_key(inv)] = inv

        if max_hops >= 2:
            # hop=2: compose каждый прямой с прямыми его цели
            direct = list(found.values())
            for ab in direct:
                mid = ab.get("target", "")
                for bc in self._bridges.get(mid, []):
                    bc2 = dict(bc)
                    bc2.setdefault("source", mid)
                    composed = self.compose(ab, bc2)
                    if composed and composed.get("target") != source:
                        composed["_hop"] = 2
                        k = _key(composed)
                        # Keep only highest confidence path
                        if k not in found or found[k].get("confidence", 0) < composed.get("confidence", 0):
                            found[k] = composed

        result = sorted(found.values(), key=lambda b: b.get("confidence", 0.5), reverse=True)
        return result

    # ------------------------------------------------------------------
    # v2.0: Protocol 3 — conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(
        self,
        entries: list,  # list[PortalEntry] — avoid circular import
    ) -> list[BridgeConflict]:
        """
        Ищет конфликты между PortalEntry из разных адаптеров:
        - одинаковый концепт (нормализованный title), разные Q6-координаты
        - два адаптера декларируют bridge с несовместимым direction
        """
        conflicts: list[BridgeConflict] = []

        # Группируем по нормализованному заголовку
        by_title: dict[str, list] = {}
        for e in entries:
            key = _normalize_title(e.title)
            by_title.setdefault(key, []).append(e)

        for title_key, group in by_title.items():
            if len(group) < 2:
                continue
            for i, ea in enumerate(group):
                for eb in group[i + 1:]:
                    repo_a = ea.id.split(":")[0]
                    repo_b = eb.id.split(":")[0]
                    if repo_a == repo_b:
                        continue
                    q6_a = ea.metadata.get("q6", "")
                    q6_b = eb.metadata.get("q6", "")
                    if q6_a and q6_b and q6_a != q6_b:
                        dist = sum(x != y for x, y in zip(q6_a, q6_b)) if len(q6_a) == len(q6_b) == 6 else -1
                        severity = "error" if dist > 2 else "warning" if dist > 1 else "info"
                        conflicts.append(BridgeConflict(
                            entry_a=ea.id,
                            entry_b=eb.id,
                            from_repo=repo_a,
                            to_repo=repo_b,
                            reason=f"Q6 mismatch: {q6_a} vs {q6_b} (Hamming={dist})",
                            severity=severity,
                        ))

        # Проверяем bridge direction consistency
        for src, bridges in self._bridges.items():
            for b in bridges:
                tgt = b.get("target", "")
                reverse = self.get(tgt, src)
                if reverse and not reverse.get("_inverted"):
                    # Оба адаптера декларируют bridge — проверяем совместимость type
                    type_src = b.get("type", "")
                    type_rev = reverse.get("type", "")
                    if type_src and type_rev and type_src != type_rev:
                        conflicts.append(BridgeConflict(
                            entry_a=f"{src}:passport",
                            entry_b=f"{tgt}:passport",
                            from_repo=src,
                            to_repo=tgt,
                            reason=f"Bridge type conflict: {src} declares '{type_src}', {tgt} declares '{type_rev}'",
                            severity="warning",
                        ))

        return conflicts

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._passports_dir.exists():
            return
        for md_file in sorted(self._passports_dir.glob("*.md")):
            adapter_name = md_file.stem
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            m = _BRIDGE_SECTION_RE.search(text)
            if not m:
                continue
            try:
                bridges = json.loads(m.group(1))
                if isinstance(bridges, list):
                    for b in bridges:
                        b.setdefault("source", adapter_name)
                    self._bridges[adapter_name] = bridges
            except (json.JSONDecodeError, ValueError):
                pass


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _normalize_title(title: str) -> str:
    """Lowercase, strip special chars for fuzzy title comparison."""
    import unicodedata
    t = unicodedata.normalize("NFC", title).lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t
