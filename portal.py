"""
Nautilus Portal — движок портала для nautilus/ репо.
Использует адаптеры из adapters/ вместо монолитного portal.py.
"""

import html as _html
import json
import sys
import argparse
from dataclasses import dataclass, field
from typing import Optional

_e = _html.escape  # HTML-экранирование против XSS

from pathlib import Path
from adapters import (
    Info1Adapter, Pro2Adapter, MetaAdapter, Data2Adapter, Data7Adapter,
    InfoSystemsAdapter, AIAgentsAdapter, AutoAdapter,
)
from adapters.base import BaseAdapter, PortalEntry
from adapters.conversation import ConversationAdapter
from adapters.jsonl import JSONLAdapter
from bridge_registry import BridgeRegistry


def q6_neighbors(bits: str, max_distance: int = 1) -> list[str]:
    """Return all Q6 bit-strings within Hamming distance of bits."""
    if not bits or len(bits) != 6:
        return []
    result = set()
    queue = [(bits, 0)]
    visited = {bits}
    while queue:
        node, dist = queue.pop(0)
        if dist > 0:
            result.add(node)
        if dist < max_distance:
            for i in range(6):
                flipped = list(node)
                flipped[i] = "1" if node[i] == "0" else "0"
                nb = "".join(flipped)
                if nb not in visited:
                    visited.add(nb)
                    queue.append((nb, dist + 1))
    return sorted(result)


def _relevance_score(entry: PortalEntry, query: str) -> float:
    """Score an entry's relevance to query (0.0–1.0, higher = more relevant)."""
    q = query.lower()
    score = 0.0
    if not q:
        return 0.5 if not entry.is_fallback else 0.1

    title_l = entry.title.lower()
    content_l = entry.content.lower()
    # Exact match in title gets highest score
    if q == title_l:
        score += 1.0
    elif q in title_l:
        score += 0.7
    if q in content_l:
        score += 0.3
    if q in entry.id.lower():
        score += 0.4
    # Cross-links indicate richer connectivity
    score += min(len(entry.links) * 0.05, 0.2)
    # Penalize fallback entries
    if entry.is_fallback:
        score *= 0.5
    return min(score, 1.0)


@dataclass
class PortalResult:
    query: str
    entries: list
    cross_links: list
    consensus: Optional[dict] = None


class NautilusPortal:
    def __init__(self) -> None:
        self.adapters = {
            "info1":       Info1Adapter(),
            "pro2":        Pro2Adapter(),
            "meta":        MetaAdapter(),
            "data2":       Data2Adapter(),
            "data7":       Data7Adapter(),
            "infosystems":   InfoSystemsAdapter(),
            "ai_agents":     AIAgentsAdapter(),
            "conversations": ConversationAdapter("docs"),
            "sessions":      ConversationAdapter("docs/sessions"),
        }
        self._bridge_registry = BridgeRegistry("passports")
        self._load_auto_adapters()

    def _load_auto_adapters(self) -> None:
        """Загружает адаптеры из nautilus.json: auto → AutoAdapter, jsonl → JSONLAdapter."""
        registry_path = Path(__file__).parent / "nautilus.json"
        if not registry_path.exists():
            return
        try:
            registry = json.loads(registry_path.read_text())
            for entry in registry.get("registry", []):
                adapter_type = entry.get("adapter")
                repo = entry.get("repo", "")
                name = entry.get("name") or repo.split("/")[-1]
                if name in self.adapters:
                    continue
                if adapter_type == "auto":
                    self.adapters[name] = AutoAdapter(repo)
                elif adapter_type == "jsonl":
                    path = entry.get("path", "")
                    if path and Path(path).exists():
                        self.adapters[name] = JSONLAdapter(path)
        except Exception:
            pass

    def query(self, concept: str, ranked: bool = True) -> PortalResult:
        all_entries = []
        for adapter in self.adapters.values():
            all_entries.extend(adapter.fetch(concept))
        if ranked:
            all_entries.sort(key=lambda e: _relevance_score(e, concept), reverse=True)
        return PortalResult(
            query=concept,
            entries=all_entries,
            cross_links=self._cross_links(all_entries),
            consensus=self._consensus(all_entries),
        )

    def describe(self) -> dict:
        return {name: a.describe() for name, a in self.adapters.items()}

    def register(self, name: str, adapter: BaseAdapter) -> None:
        self.adapters[name] = adapter

    def query_neighbors(self, bits: str, max_distance: int = 1) -> "PortalResult":
        """Find entries whose Q6 coordinate is within Hamming distance of bits."""
        neighbors = q6_neighbors(bits, max_distance)
        target_bits = {bits} | set(neighbors)
        all_entries = []
        for adapter in self.adapters.values():
            for e in adapter.fetch(""):
                eq6 = e.metadata.get("q6", "")
                if isinstance(eq6, str) and eq6 in target_bits:
                    all_entries.append(e)
        # Sort by Hamming distance to query bits
        def dist(e: PortalEntry) -> int:
            eq6 = e.metadata.get("q6", bits)
            return sum(a != b for a, b in zip(eq6, bits)) if len(eq6) == 6 else 99
        all_entries.sort(key=dist)
        return PortalResult(
            query=f"q6:{bits}±{max_distance}",
            entries=all_entries,
            cross_links=self._cross_links(all_entries),
            consensus=self._consensus(all_entries),
        )

    def _cross_links(self, entries: list) -> list:
        links, seen = [], set()
        for e in entries:
            for link_id in e.links:
                key = tuple(sorted([e.id, link_id]))
                if key not in seen:
                    seen.add(key)
                    sr = e.id.split(":")[0]
                    tr = link_id.split(":")[0]
                    if sr != tr:
                        bridge_ann = self._bridge_registry.annotate_link(sr, tr)
                        links.append({"from": e.id, "to": link_id,
                                      "from_repo": sr, "to_repo": tr,
                                      **bridge_ann})
        return links

    def _consensus(self, entries: list) -> dict:
        all_sources = {e.id.split(":")[0] for e in entries}
        real_sources = {e.id.split(":")[0] for e in entries if not e.is_fallback}
        present_all = all_sources & set(self.adapters)
        present_real = real_sources & set(self.adapters)
        cov_real = len(present_real) / len(self.adapters) if self.adapters else 0
        cov_all = len(present_all) / len(self.adapters) if self.adapters else 0
        return {
            "present_in": sorted(present_real),
            "present_in_fallback": sorted(present_all - present_real),
            "missing_in": sorted(set(self.adapters) - present_all),
            "coverage": round(cov_real, 2),
            "coverage_with_fallback": round(cov_all, 2),
            "agreed": cov_real >= 1.0,
        }


def render_html(result: PortalResult, portal: "NautilusPortal") -> str:
    c = result.consensus or {}
    coverage_pct = int(c.get("coverage", 0) * 100)
    present = ", ".join(c.get("present_in", []))
    missing = ", ".join(c.get("missing_in", []))

    entries_html = ""
    for e in result.entries:
        repo = _e(e.id.split(":")[0].upper())
        links_html = ""
        if e.links:
            links_html = "<div class='links'>→ " + ", ".join(
                f"<code>{_e(l)}</code>" for l in e.links[:4]
            ) + "</div>"
        entries_html += f"""
        <div class="entry">
            <div class="repo-tag">{repo}</div>
            <div class="title">{_e(e.title)}</div>
            <div class="content">{_e(e.content[:200])}</div>
            {links_html}
        </div>"""

    cross_html = ""
    for lnk in result.cross_links[:10]:
        cross_html += (
            f"<li><code>{_e(lnk['from'])}</code> → <code>{_e(lnk['to'])}</code> "
            f"<span class='repos'>({_e(lnk['from_repo'])} ↔ {_e(lnk['to_repo'])})</span></li>"
        )

    adapters_list = " · ".join(portal.adapters.keys())

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>⬡ Nautilus Portal — {_e(result.query)}</title>
<style>
  body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
  h1 {{ color: #58a6ff; }}
  .query-form {{ margin: 16px 0; }}
  .query-form input {{ background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
                       padding: 8px 12px; font-size: 16px; width: 300px; border-radius: 6px; }}
  .query-form button {{ background: #238636; color: #fff; border: none; padding: 8px 16px;
                        font-size: 16px; border-radius: 6px; cursor: pointer; margin-left: 8px; }}
  .consensus {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                padding: 12px 16px; margin: 16px 0; }}
  .coverage {{ font-size: 24px; color: {'#3fb950' if coverage_pct == 100 else '#d29922' if coverage_pct > 50 else '#f85149'}; }}
  .entry {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
            padding: 12px 16px; margin: 10px 0; }}
  .repo-tag {{ display: inline-block; background: #1f6feb; color: #fff; padding: 2px 8px;
               border-radius: 4px; font-size: 12px; margin-bottom: 6px; }}
  .title {{ font-size: 16px; font-weight: bold; color: #e6edf3; margin-bottom: 4px; }}
  .content {{ color: #8b949e; font-size: 13px; white-space: pre-wrap; }}
  .links {{ color: #58a6ff; font-size: 12px; margin-top: 6px; }}
  .cross-links {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                  padding: 12px 16px; margin: 16px 0; }}
  .cross-links li {{ margin: 4px 0; font-size: 13px; }}
  .repos {{ color: #8b949e; }}
  code {{ background: #21262d; padding: 1px 4px; border-radius: 3px; font-size: 12px; }}
  .adapters {{ color: #8b949e; font-size: 12px; margin-top: 24px; }}
</style>
</head>
<body>
<h1>⬡ Nautilus Portal</h1>
<form class="query-form" method="get">
  <input name="q" value="{_e(result.query)}" placeholder="запрос...">
  <button type="submit">Найти</button>
</form>

<div class="consensus">
  <span class="coverage">{coverage_pct}% покрытие</span> &nbsp;·&nbsp;
  найдено в: <strong>{_e(present) or '—'}</strong>
  {f'&nbsp;·&nbsp; отсутствует: {_e(missing)}' if missing else ''}
</div>

<div>{entries_html}</div>

{'<div class="cross-links"><strong>Межрепозиторные связи:</strong><ul>' + cross_html + '</ul></div>' if cross_html else ''}

<div class="adapters">адаптеры: {adapters_list}</div>
</body>
</html>"""


def render_text(result: PortalResult) -> str:
    lines = [f'\n⬡ NAUTILUS PORTAL — "{result.query}"', "=" * 50]
    for e in result.entries:
        repo = e.id.split(":")[0].upper()
        lines.append(f"\n[{repo}] {e.title}")
        lines.append(f"  {e.content[:120]}")
        if e.links:
            lines.append(f"  → {', '.join(e.links[:3])}")
    c = result.consensus or {}
    lines.append(f"\nКонсенсус: {c.get('coverage',0)*100:.0f}% · "
                 f"{', '.join(c.get('present_in',[]))}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", default="knowledge")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--describe", action="store_true")
    args = parser.parse_args()

    portal = NautilusPortal()

    if args.describe:
        print(json.dumps(portal.describe(), ensure_ascii=False, indent=2))
        return
    if args.serve:
        _serve(portal)
        return

    result = portal.query(args.query)

    if args.json:
        print(json.dumps({
            "query": result.query,
            "entries": [{"id": e.id, "title": e.title, "content": e.content[:200],
                         "metadata": e.metadata} for e in result.entries],
            "cross_links": result.cross_links,
            "consensus": result.consensus,
        }, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))


def _serve(portal: NautilusPortal) -> None:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            path = parsed.path.rstrip("/")

            # AJAX endpoint — returns JSON for live search
            if path == "/search":
                query = params.get("q", ["knowledge"])[0]
                result = portal.query(query)
                c = result.consensus or {}
                data = {
                    "query": query,
                    "coverage_pct": int(c.get("coverage", 0) * 100),
                    "coverage_fb_pct": int(c.get("coverage_with_fallback", 0) * 100),
                    "present": c.get("present_in", []),
                    "missing": c.get("missing_in", []),
                    "cross_links": result.cross_links[:10],
                    "entries": [
                        {
                            "id": _e(e.id),
                            "repo": _e(e.id.split(":")[0].upper()),
                            "title": _e(e.title),
                            "content": _e(e.content[:250]),
                            "links": [_e(l) for l in e.links[:4]],
                            "is_fallback": e.is_fallback,
                            "q6": e.metadata.get("q6", ""),
                        }
                        for e in result.entries
                    ],
                }
                body = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
                return

            # Main page — full AJAX-enabled SPA
            query = params.get("q", ["knowledge"])[0]
            html = _render_spa(portal, query)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        def log_message(self, *a: object) -> None:
            pass

    print("⬡ Nautilus Portal → http://localhost:8000/?q=crystal")
    HTTPServer(("", 8000), Handler).serve_forever()


def _render_spa(portal: NautilusPortal, initial_query: str = "knowledge") -> str:
    adapters_list = " · ".join(portal.adapters.keys())
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>⬡ Nautilus Portal</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
  h1 {{ color: #58a6ff; margin: 0 0 16px; }}
  .query-form {{ display: flex; gap: 8px; margin-bottom: 16px; }}
  .query-form input {{
    background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
    padding: 8px 12px; font-size: 16px; flex: 1; max-width: 400px;
    border-radius: 6px; font-family: monospace;
  }}
  .query-form input:focus {{ outline: none; border-color: #58a6ff; }}
  .query-form button {{
    background: #238636; color: #fff; border: none; padding: 8px 16px;
    font-size: 15px; border-radius: 6px; cursor: pointer;
  }}
  .query-form button:hover {{ background: #2ea043; }}
  #spinner {{ display: none; color: #58a6ff; margin-left: 8px; font-size: 13px; }}
  .consensus {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 16px; display: flex;
    align-items: center; gap: 12px; flex-wrap: wrap;
  }}
  .coverage {{ font-size: 22px; font-weight: bold; }}
  .cov-green {{ color: #3fb950; }}
  .cov-yellow {{ color: #d29922; }}
  .cov-red {{ color: #f85149; }}
  .tag {{ background: #1f6feb22; border: 1px solid #1f6feb55; border-radius: 4px;
          padding: 1px 6px; font-size: 12px; color: #58a6ff; }}
  .tag.miss {{ background: #f8514922; border-color: #f8514955; color: #f85149; }}
  #entries {{ display: grid; gap: 10px; }}
  .entry {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 16px; transition: border-color 0.15s;
  }}
  .entry:hover {{ border-color: #58a6ff44; }}
  .entry.fallback {{ opacity: 0.7; border-style: dashed; }}
  .repo-tag {{
    display: inline-block; background: #1f6feb; color: #fff;
    padding: 1px 7px; border-radius: 4px; font-size: 11px; margin-bottom: 5px;
  }}
  .q6-tag {{
    display: inline-block; background: #8b5cf622; border: 1px solid #8b5cf655;
    color: #a78bfa; padding: 1px 6px; border-radius: 4px; font-size: 11px;
    margin-left: 6px;
  }}
  .title {{ font-size: 15px; font-weight: bold; color: #e6edf3; }}
  .content {{ color: #8b949e; font-size: 13px; margin-top: 4px; white-space: pre-wrap; }}
  .links {{ color: #58a6ff; font-size: 12px; margin-top: 5px; }}
  .cross-section {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 16px;
  }}
  .cross-section h3 {{ margin: 0 0 8px; color: #8b949e; font-size: 13px; }}
  .cross-section li {{ font-size: 12px; margin: 3px 0; }}
  code {{ background: #21262d; padding: 1px 4px; border-radius: 3px; font-size: 11px; }}
  .adapters {{ color: #8b949e; font-size: 11px; margin-top: 20px; }}
  #result-count {{ color: #8b949e; font-size: 13px; margin-bottom: 10px; }}
</style>
</head>
<body>
<h1>⬡ Nautilus Portal</h1>

<div class="query-form">
  <input id="q" type="text" value="{_e(initial_query)}" placeholder="запрос..." autofocus>
  <button onclick="doSearch()">Найти</button>
  <span id="spinner">⟳ поиск...</span>
</div>

<div class="consensus" id="consensus"></div>
<div id="cross-links-wrap"></div>
<div id="result-count"></div>
<div id="entries"></div>
<div class="adapters">адаптеры: {adapters_list}</div>

<script>
let debounceTimer = null;
const input = document.getElementById("q");

input.addEventListener("input", () => {{
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(doSearch, 280);
}});
input.addEventListener("keydown", e => {{ if (e.key === "Enter") {{ clearTimeout(debounceTimer); doSearch(); }} }});

async function doSearch() {{
  const q = input.value.trim() || "knowledge";
  history.replaceState(null, "", "?q=" + encodeURIComponent(q));
  document.getElementById("spinner").style.display = "inline";

  try {{
    const res = await fetch("/search?q=" + encodeURIComponent(q));
    const data = await res.json();
    renderConsensus(data);
    renderCrossLinks(data.cross_links);
    renderEntries(data.entries);
    document.getElementById("result-count").textContent =
      data.entries.length + " записей";
  }} catch(e) {{
    document.getElementById("entries").innerHTML =
      "<div style='color:#f85149'>Ошибка: " + e + "</div>";
  }} finally {{
    document.getElementById("spinner").style.display = "none";
  }}
}}

function coverageClass(pct) {{
  return pct === 100 ? "cov-green" : pct > 50 ? "cov-yellow" : "cov-red";
}}

function renderConsensus(d) {{
  const pct = d.coverage_pct;
  const cls = coverageClass(pct);
  const present = d.present.map(n => `<span class="tag">${{n}}</span>`).join(" ");
  const missing = d.missing.map(n => `<span class="tag miss">${{n}}</span>`).join(" ");
  document.getElementById("consensus").innerHTML = `
    <span class="coverage ${{cls}}">${{pct}}%</span>
    <span style="color:#8b949e;font-size:13px">покрытие (реальное)</span>
    ${{present ? "· найдено: " + present : ""}}
    ${{missing ? "· отсутствует: " + missing : ""}}
  `;
}}

function renderCrossLinks(links) {{
  const wrap = document.getElementById("cross-links-wrap");
  if (!links || !links.length) {{ wrap.innerHTML = ""; return; }}
  const items = links.slice(0,8).map(l =>
    `<li><code>${{l.from}}</code> → <code>${{l.to}}</code> <span style="color:#8b949e">(${{l.from_repo}} ↔ ${{l.to_repo}})</span></li>`
  ).join("");
  wrap.innerHTML = `<div class="cross-section"><h3>Межрепозиторные связи</h3><ul>${{items}}</ul></div>`;
}}

function renderEntries(entries) {{
  const container = document.getElementById("entries");
  if (!entries.length) {{
    container.innerHTML = "<div style='color:#8b949e'>Ничего не найдено</div>";
    return;
  }}
  container.innerHTML = entries.map(e => {{
    const fb = e.is_fallback ? " fallback" : "";
    const q6 = e.q6 ? `<span class="q6-tag">Q6=${{e.q6}}</span>` : "";
    const links = e.links.length
      ? `<div class="links">→ ${{e.links.map(l => `<code>${{l}}</code>`).join(" ")}}</div>`
      : "";
    return `<div class="entry${{fb}}">
      <div><span class="repo-tag">${{e.repo}}</span>${{q6}}</div>
      <div class="title">${{e.title}}</div>
      <div class="content">${{e.content}}</div>
      ${{links}}
    </div>`;
  }}).join("");
}}

doSearch();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
