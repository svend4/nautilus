# Nautilus Portal Protocol

**Version:** 1.1  
**Status:** Working Draft  
**Date:** 2026-04-19  
**Repository:** [svend4/nautilus](https://github.com/svend4/nautilus)  
**License:** CC BY 4.0  

---

## Abstract

The Nautilus Portal Protocol (NPP) defines a minimal, open standard for
federating heterogeneous knowledge repositories without merging their native
formats. A conforming implementation discovers repositories, translates their
entries into a universal `PortalEntry` record, positions each entry in a
shared 6-bit coordinate space (Q6), and computes cross-repository consensus
on any query.

The central design commitment: **compatibility, not merger**. Each repository
retains sovereign control over its format, schema, and internal logic. The
protocol adds a shared read layer on top — analogous to how an office suite
reads `.docx`, `.pdf`, and `.xlsx` without converting them into a single format.

---

## Table of Contents

1. [Scope](#1-scope)
2. [Terminology](#2-terminology)
3. [Core Concepts](#3-core-concepts)
4. [PortalEntry Data Model](#4-portalentry-data-model)
5. [BaseAdapter Interface](#5-baseadapter-interface)
6. [Registry (nautilus.json)](#6-registry-nautilusjson)
7. [Passport Schema](#7-passport-schema)
8. [Compatibility Levels](#8-compatibility-levels)
9. [Q6 Address Space](#9-q6-address-space)
10. [Consensus Algorithm](#10-consensus-algorithm)
11. [REST API Semantics](#11-rest-api-semantics)
12. [Caching Semantics](#12-caching-semantics)
13. [Security Considerations](#13-security-considerations)
14. [Versioning](#14-versioning)

---

## 1. Scope

### 1.1. In Scope

- The `BaseAdapter` / `PortalEntry` interface contract
- The `nautilus.json` registry schema
- The Passport document schema
- Compatibility levels 0–3
- The Q6 coordinate system and Hamming-distance semantics
- The consensus algorithm
- The HTTP REST API surface
- Caching behaviour and TTL guarantees
- Security requirements for public deployments

### 1.2. Out of Scope

- Internal repository formats (`.info1`, `.pro2`, `.meta`, etc.)
- Authentication mechanisms (implementation-defined)
- Specific adapter implementations
- Transport layer below HTTP

---

## 2. Terminology

| Term | Definition |
|------|-----------|
| **Repository** | A source of structured knowledge with a native format |
| **Adapter** | A conforming implementation of `BaseAdapter` for one repository |
| **PortalEntry** | The universal record produced by every adapter |
| **Portal** | An instance of `NautilusPortal` aggregating multiple adapters |
| **Passport** | A Markdown document describing a repository's protocol metadata |
| **Registry** | The `nautilus.json` file listing registered repositories |
| **Q6** | A 6-bit binary address `[b5..b0]` identifying a vertex in {0,1}⁶ |
| **Consensus** | Agreement metric computed across all adapters for a query |
| **Fallback** | A static entry returned when live data is unavailable |
| **Bridge** | A declared semantic relationship between two formats |

---

## 3. Core Concepts

### 3.1. Federation without Merger

NPP does NOT define a canonical format. Repositories are not required to
migrate their data. The adapter translates on read — source data remains
untouched in its native structure.

### 3.2. Adapter as Contract

The adapter is the sole integration point. A repository achieves
compatibility by implementing two methods: `fetch()` and `describe()`.
Nothing else in the source repository needs to change.

### 3.3. Consensus as Epistemic Criterion

A concept is considered **agreed** (`consensus.agreed = True`) only when
all adapters return at least one real (non-fallback) entry for the query.
Partial consensus (some adapters match, others do not) is reported
explicitly and treated as a signal for future integration work.

### 3.4. Q6 as Universal Coordinate

Every `PortalEntry` carries a Q6 address. This enables:
- Semantic proximity queries (Hamming distance ≤ k)
- Cross-format clustering without shared vocabulary
- Gap detection (uncovered regions of the hypercube)
- Visual navigation (q6_map.html)

---

## 4. PortalEntry Data Model

The `PortalEntry` dataclass is defined in `adapters/base.py` and is the
**only** data structure that crosses adapter boundaries.

```python
@dataclass
class PortalEntry:
    id: str               # Globally unique. Format: "adapter_name:slug"
    title: str            # Human-readable title (≤ 200 chars)
    source: str           # GitHub slug, e.g. "svend4/info1"
    format_type: str      # See §4.1
    content: str          # Plain-text summary (≤ 1 000 chars recommended)
    metadata: dict        # See §4.2
    links: list[str]      # Cross-references to other PortalEntry IDs
    is_fallback: bool     # True if returned from static fallback data
```

### 4.1. `format_type` Values

| Value | Meaning |
|-------|---------|
| `document` | Markdown / prose document |
| `concept` | Named conceptual unit with Q6 coordinate |
| `rule` | Cellular automaton rule or formal constraint |
| `theory` | Multi-step theoretical framework |
| `schema` | Data schema or type definition |
| `archetype` | Pattern or archetype instance |
| `conversation` | Section extracted from a conversation export |

Implementations MAY define additional values. Unknown values MUST be
treated as `document` by consuming code.

### 4.2. Metadata Conventions

The `metadata` dict is free-form but the following keys are conventional:

| Key | Type | Meaning |
|-----|------|---------|
| `q6` | `str[6]` | Binary Q6 address, e.g. `"110001"` |
| `alpha` | `int` | Abstraction level −4..+4 (info1 convention) |
| `ca_class` | `str` | Wolfram CA class: `"I"`, `"II"`, `"III"`, `"IV"` |
| `hex_id` | `int` | I-Ching hexagram number 1–64 |
| `tags` | `list[str]` | Free-form tags |
| `file` | `str` | Source filename within repository |
| `section` | `int` | Section index within source file |

### 4.3. ID Format

```
id = "<adapter_name>:<slug>"
```

Where `slug` is a stable, URL-safe identifier. Adapters MUST ensure IDs
are stable across re-fetches of the same logical entry.

### 4.4. Fallback Entries

When live data is unavailable (network error, missing API token, etc.),
an adapter MUST return a non-empty list of static `PortalEntry` records
with `is_fallback=True`. An adapter MUST NOT raise an exception.

Relevance scoring applies a 0.5× penalty to fallback entries.

---

## 5. BaseAdapter Interface

Defined in `adapters/base.py`. All adapters MUST subclass `BaseAdapter`
and implement both abstract methods.

```python
class BaseAdapter(ABC):
    name: str = "unnamed"   # Unique adapter identifier (snake_case)

    @abstractmethod
    def fetch(self, query: str) -> list[PortalEntry]:
        """
        Search the repository for entries matching `query`.

        Requirements:
        - MUST return a list (empty list is valid)
        - MUST NOT raise any exception
        - MUST return fallback entries when live data is unavailable
        - query="" or query="all" SHOULD return a representative sample
        - Results SHOULD be ordered by relevance (descending)
        - Results SHOULD contain at most 20 entries
        """

    @abstractmethod
    def describe(self) -> dict[str, Any]:
        """
        Return repository metadata.

        Required keys: "format", "native_unit"
        Recommended keys: "total_entries" (or "total_*"), "compatibility"
        """
```

### 5.1. Relevance Scoring (normative recommendation)

Implementations SHOULD compute relevance using at minimum:

```
score = 0.0
if query == title.lower():          score += 1.0  # exact title match
elif query in title.lower():        score += 0.7  # title substring
if query in content.lower():        score += 0.3  # content substring
if query in entry.id.lower():       score += 0.4  # ID match
score += min(len(links) * 0.05, 0.2)             # connectivity bonus
if is_fallback:                     score *= 0.5  # fallback penalty
```

### 5.2. Registration

Adapters are registered at portal instantiation:

```python
portal = NautilusPortal()
portal.register("my-repo", MyRepoAdapter())
```

Auto-registration via `nautilus.json` entries with `"adapter": "auto"`
uses `AutoAdapter`, which reads `nautilus.json` from the target repository.

---

## 6. Registry (nautilus.json)

Every NPP deployment MUST include a `nautilus.json` file at the repository
root. This file is the machine-readable registry of participating repositories.

### 6.1. Schema

```json
{
  "name": "string",
  "version": "semver",
  "description": "string",
  "registry": [
    {
      "repo":          "owner/repo-name",
      "adapter":       "adapter_name | auto",
      "format":        "format-id",
      "compatibility": 0 | 1 | 2 | 3,
      "passport":      "path/to/passport.md",
      "note":          "optional annotation"
    }
  ],
  "consensus_threshold": 1.0,
  "github_pages": "owner.github.io/nautilus"
}
```

### 6.2. Required Fields (per registry entry)

`repo`, `adapter`, `format`, `compatibility`, `passport`

### 6.3. AutoAdapter Protocol

A repository declares itself auto-compatible by placing a `nautilus.json`
in its own root. Minimum required fields:

```json
{
  "name": "repo-name",
  "format": "format-id",
  "native_unit": "document | concept | rule",
  "compatibility": 1
}
```

---

## 7. Passport Schema

Each registered repository MUST have a passport — a Markdown document
validated against `passport_schema.json`.

### 7.1. Required Fields (JSON Schema)

```json
{
  "repo":          "owner/repo-name",
  "format":        "format-id",
  "native_unit":   "description of atomic unit",
  "compatibility": 0
}
```

### 7.2. Recommended Fields

```json
{
  "description":       "1–2 sentence description",
  "total_items":       "50+ | integer",
  "abstraction_range": "α -4..+4",
  "q6_key":            "projection rule description",
  "bridges": {
    "other-format": "semantic relationship description"
  },
  "access": {
    "type":           "github_api | local_files | static | http_api",
    "requires_token": false,
    "fallback":       "static entries description"
  },
  "example_queries": ["query1", "query2"]
}
```

### 7.3. Bridges

The `bridges` field declares semantic relationships between this repository
and other formats. Values are natural-language descriptions of the mapping.
Formal bridge algebra (composition, inversion, transitivity) is deferred
to NPP v2.0.

---

## 8. Compatibility Levels

The compatibility ladder defines the integration maturity of a repository.
Higher levels are strictly additive — a Level 3 repository satisfies all
requirements of Levels 0–2.

| Level | Name | Requirement | Minimum Adapter Behaviour |
|-------|------|-------------|--------------------------|
| **0** | Discoverable | Entry in `nautilus.json` | None — portal knows it exists |
| **1** | Readable | Static `PortalEntry` list | `fetch()` returns ≥1 entry |
| **2** | Linked | Q6 coordinates + cross-links | `metadata.q6` populated; `links` non-empty |
| **3** | Interactive | Live fetch via external API | `fetch()` queries live data source |

### 8.1. Current Ecosystem Distribution

| Level | Count | Repositories |
|-------|------:|-------------|
| 3 | 1 | pro2 |
| 2 | 3 | data7, infosystems, ai_agents |
| 1 | 3 | info1, meta, data2 |
| 0 | 0 | — |

---

## 9. Q6 Address Space

### 9.1. Definition

Q6 is a 6-bit binary string `b5b4b3b2b1b0 ∈ {0,1}⁶` representing a vertex
in the 64-vertex Boolean hypercube. It serves as a semantic coordinate for
every `PortalEntry`.

```
Q6 ∈ {"000000", "000001", …, "111111"}   # 64 vertices
```

### 9.2. Semantic Properties

- **Hamming distance** between two Q6 addresses is the semantic proximity
  metric. Distance 1 = one bit flip = "semantically adjacent".
- **Neighborhood query**: given a Q6 address and radius `k`, the portal
  returns all entries within Hamming distance ≤ k using BFS.
- **CA classification**: Q6 addresses map to Wolfram Cellular Automaton
  classes (I–IV), providing a second semantic axis.
- **I-Ching correspondence**: all 64 vertices correspond bijectively to the
  64 hexagrams, providing a symbolic namespace.

### 9.3. Per-Format Projection Rules

Each adapter defines a rule mapping its native entities to Q6:

| Adapter | Projection Rule |
|---------|----------------|
| info1 | `alpha_level + 4` → top 3 bits |
| pro2 | native Q6 coordinates |
| meta | `hex_id − 1 → bin(6)` |
| data7 | `ordinal % 64 → bin(6)` |

### 9.4. Gap Detection

Vertices with no real (non-fallback) entries are **gaps**. The gap detector
(`gap_detection.py`) uses BFS to classify vertices as:

- **Real**: ≥1 non-fallback entry
- **Weak**: only fallback entries
- **Gap**: no entries

Current state: 14 real / 19 weak / 31 gap (48.4% uncovered).

---

## 10. Consensus Algorithm

### 10.1. Definition

For a query `q`, the portal queries all registered adapters and computes:

```python
present_in          = [a for a in adapters if any non-fallback entry]
present_in_fallback = [a for a in adapters if only fallback entries]
missing_in          = [a for a in adapters if no entries at all]

coverage             = len(present_in) / len(adapters)
coverage_with_fallback = (len(present_in) + len(present_in_fallback)) / len(adapters)
agreed               = (coverage >= consensus_threshold)  # default: 1.0
```

### 10.2. Consensus Record

```json
{
  "query": "синтез",
  "present_in": ["pro2", "info1"],
  "present_in_fallback": ["meta", "data2"],
  "missing_in": ["data7"],
  "coverage": 0.286,
  "coverage_with_fallback": 0.571,
  "agreed": false
}
```

### 10.3. Interpretation

| Coverage | Meaning |
|----------|---------|
| 1.0 (agreed) | Confirmed cross-format fact |
| 0.5–1.0 | Likely pattern, warrants bridging |
| < 0.5 | Hypothesis, present in few formats |
| 0.0 | Unknown to ecosystem |

---

## 11. REST API Semantics

The reference implementation exposes an HTTP API defined in `openapi.yaml`.
All endpoints return JSON unless noted.

### 11.1. Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/query` | Multi-adapter search |
| `GET` | `/api/health` | Ecosystem health score 0–100 |
| `GET` | `/api/links` | Cross-link validation report |
| `GET` | `/api/describe` | Adapter descriptions |
| `GET` | `/api/neighbors` | Q6 Hamming-neighborhood query |
| `GET` | `/metrics` | Prometheus text metrics |

### 11.2. `/api/query` Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search query |
| `ranked` | 0\|1 | 1 | Apply relevance ranking |
| `adapter` | string | all | Limit to one adapter |

### 11.3. `/metrics` Format

Prometheus text exposition (Content-Type: `text/plain; version=0.0.4`).
TTL: 30 seconds. Metrics exposed:

```
nautilus_health_score
nautilus_adapters_count
nautilus_adapter_entries{adapter="..."}
nautilus_cache_age_hours{repo="..."}
```

### 11.4. CORS

All endpoints MUST include `Access-Control-Allow-Origin: *` for public
portal deployments.

---

## 12. Caching Semantics

### 12.1. Disk Cache

Adapters that fetch remote data SHOULD use the `CacheManager` from
`adapters/cache.py`. Default TTL: **24 hours**. Cache location: `cache/`.

### 12.2. Cache Entry Format

```json
{
  "data": { ... },
  "fetched_at": 1713456000.0,
  "source": "adapter_name"
}
```

### 12.3. Fallback on Cache Miss

If the cache is empty and the live source is unavailable, the adapter
MUST return static fallback entries rather than raising an exception.

### 12.4. Metrics Cache

`/metrics` endpoint caches its computation for 30 seconds to avoid
cascading health checks on every Prometheus scrape.

---

## 13. Security Considerations

### 13.1. XSS Prevention

All user-supplied strings rendered in HTML contexts MUST be escaped using
`html.escape()`. The reference implementation applies this at `portal.py:13`.

### 13.2. No Eval / Exec

Implementations MUST NOT use `eval()` or `exec()` on data received from
adapters or HTTP clients.

### 13.3. API Tokens

GitHub API tokens MUST be supplied via environment variables (`GITHUB_TOKEN`),
never hardcoded. Adapters MUST degrade gracefully when tokens are absent.

### 13.4. Rate Limiting

Public deployments SHOULD implement rate limiting on `/api/query` and
`/api/neighbors`. The reference implementation does not include rate
limiting (tracked as v1.2 roadmap item).

### 13.5. Authentication

The reference implementation provides no authentication. Deployments
exposing sensitive knowledge MUST add authentication before going public.
JWT / API-key patterns are recommended (v1.5 roadmap).

---

## 14. Versioning

### 14.1. Protocol Versions

| Version | Status | Notes |
|---------|--------|-------|
| v1.0 | Superseded | Original 3-repo proof of concept |
| **v1.1** | **Current** | 7 repos, REST API, Q6, TF-IDF, mypy clean |
| v1.2 | Planned | pyproject.toml, E2E tests, rate limiting |
| v1.5 | Planned | SQLite backend, JWT auth, WebSocket |
| v2.0 | Future | Formal bridge algebra, temporal model |

### 14.2. Breaking Changes

A change is **breaking** if it:
- Removes or renames a required field from `PortalEntry`
- Changes the signature of `fetch()` or `describe()`
- Removes an endpoint from the REST API
- Changes Q6 projection rules for existing adapters

Breaking changes increment the major version component of the protocol.

### 14.3. Extension Points

- `PortalEntry.metadata` — free-form; add keys without breaking compatibility
- `PortalEntry.format_type` — new values are backwards compatible
- New endpoints — always additive
- New adapters — always additive
- New passport fields — always additive

---

## Appendix A: Minimal Conforming Adapter

```python
from adapters.base import BaseAdapter, PortalEntry

class MinimalAdapter(BaseAdapter):
    name = "my-repo"

    def fetch(self, query: str) -> list[PortalEntry]:
        return [PortalEntry(
            id="my-repo:entry-1",
            title="Example Entry",
            source="owner/my-repo",
            format_type="document",
            content="Content matching the query.",
            metadata={"q6": "010100"},
            links=["pro2:q6:010100"],
        )]

    def describe(self) -> dict:
        return {"format": "my-format", "native_unit": "document"}
```

## Appendix B: nautilus.json Minimal Example

```json
{
  "name": "nautilus",
  "version": "1.1",
  "registry": [
    {
      "repo": "owner/my-repo",
      "adapter": "my-repo",
      "format": "my-format",
      "compatibility": 1,
      "passport": "passports/my-repo.md"
    }
  ],
  "consensus_threshold": 1.0
}
```

## Appendix C: Related Work

| System | Relation to NPP |
|--------|----------------|
| ActivityPub (W3C) | Federation at the social-graph level; NPP federates knowledge content |
| Solid (Inrupt) | Per-user data pods with SPARQL; NPP uses adapters not SPARQL |
| Model Context Protocol (Anthropic MCP) | Tool-calling protocol for AI; NPP is query-federation for humans + AI |
| Linked Data / RDF | Mandates canonical URIs; NPP preserves native formats |
| OpenAPI | REST API description; NPP uses OpenAPI for its own REST surface |

---

*Nautilus Portal Protocol v1.1 · svend4/nautilus · 2026-04-19*
