"""
BridgeRegistry — читает типизированные bridges из паспортов (v1.2).

Каждый паспорт (passports/*.md) может содержать секцию:

    ## Bridges (machine-readable)
    ```json
    [{"target": "...", "direction": "↔", "type": "isomorphism", ...}]
    ```

BridgeRegistry парсит эти блоки и предоставляет lookup по паре (source, target).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_DIRECTION_LABEL = {
    "→": "source→target",
    "←": "target→source",
    "↔": "bidirectional",
}

_BRIDGE_SECTION_RE = re.compile(
    r"##\s+Bridges\s+\(machine-readable\)\s*\n+```json\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class BridgeRegistry:
    """
    Реестр типизированных мостов между адаптерами.

    Загружается один раз при старте портала. Все методы read-only.
    """

    def __init__(self, passports_dir: str | Path = "passports") -> None:
        self._passports_dir = Path(passports_dir)
        # {source_adapter: [bridge_dict, ...]}
        self._bridges: dict[str, list[dict[str, Any]]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, source: str, target: str) -> dict[str, Any] | None:
        """Return bridge metadata for the (source, target) pair, or None."""
        for b in self._bridges.get(source, []):
            if b.get("target") == target:
                return b
        # Check reverse direction
        for b in self._bridges.get(target, []):
            if b.get("target") == source and b.get("direction") in ("↔", "←"):
                inverted = dict(b)
                inverted["target"] = source
                inverted["source"] = target
                d = inverted.get("direction", "↔")
                inverted["direction"] = "←" if d == "→" else ("→" if d == "←" else "↔")
                inverted["_inverted"] = True
                return inverted
        return None

    def all_for(self, source: str) -> list[dict[str, Any]]:
        """Return all bridges declared by source adapter."""
        return list(self._bridges.get(source, []))

    def annotate_link(self, from_repo: str, to_repo: str) -> dict[str, Any]:
        """
        Return bridge annotation dict suitable for embedding in cross_links.
        Falls back to minimal dict if no bridge is registered.
        """
        bridge = self.get(from_repo, to_repo)
        if bridge:
            return {
                "bridge_type":      bridge.get("type", "unknown"),
                "bridge_direction": bridge.get("direction", "↔"),
                "bridge_mapping":   bridge.get("mapping", ""),
                "bridge_confidence": bridge.get("confidence", None),
            }
        return {
            "bridge_type":      "unknown",
            "bridge_direction": "↔",
            "bridge_mapping":   "",
            "bridge_confidence": None,
        }

    def summary(self) -> dict[str, Any]:
        """Return a summary of all loaded bridges."""
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
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._passports_dir.exists():
            return
        for md_file in sorted(self._passports_dir.glob("*.md")):
            adapter_name = md_file.stem          # "pro2", "info1", …
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            m = _BRIDGE_SECTION_RE.search(text)
            if not m:
                continue
            try:
                bridges = json.loads(m.group(1))
                if isinstance(bridges, list):
                    # Inject source field for convenience
                    for b in bridges:
                        b.setdefault("source", adapter_name)
                    self._bridges[adapter_name] = bridges
            except (json.JSONDecodeError, ValueError):
                pass
