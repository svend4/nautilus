# Nautilus Portal Protocol

**Version:** 1.2
**Status:** Current
**Date:** 2026-04-19
**Repository:** [svend4/nautilus](https://github.com/svend4/nautilus)
**License:** CC BY 4.0

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174]
when they appear in all capitals.

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
15. [Bridge Algebra](#15-bridge-algebra)
16. [Annotations and Protocol 3](#16-annotations-and-protocol-3)
17. [Extended REST API](#17-extended-rest-api)

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

NPP v1.2 distinguishes two consensus levels (see §10):

- **Universal** (`consensus.universal = True`) — all adapters return a real
  (non-fallback) entry. Confirmed cross-format fact.
- **Majority** (`consensus.majority = True`) — at least 50% of adapters return
  a real entry. Likely pattern, warrants bridging work.

**Absence is information.** A concept missing from an out-of-domain adapter
(e.g. `soz150` legal adapter does not know «quantum coherence») is NOT a gap —
it is expected. Adapters MAY declare a domain-relevance hint via
`describe().q6_range` so that out-of-domain misses do not penalise coverage.
Implementations SHOULD report `missing_in` split into `missing_in_domain`
and `out_of_domain` when `q6_range` is declared.

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

        REQUIRED keys:
          "format"        — format identifier matching nautilus.json
          "native_unit"   — natural-language description of atomic unit

        RECOMMENDED keys (consumed by health_check.py):
          "compatibility" — 0..3 integer (Level per §8)
          "total_*"       — any key prefixed "total_" with an int value,
                            e.g. "total_concepts", "total_tools"
          "description"   — one-sentence summary
          "q6_range"      — list of Q6 strings or "*" indicating domain
                            coverage; enables in-domain/out-of-domain split
                            in consensus reporting (§10)

        A conforming adapter MUST return at least the REQUIRED keys.
        Missing RECOMMENDED keys MUST NOT cause the portal to fail — but
        health_check.py will report lower scores for such adapters.
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

`repo`, `adapter`, `format`, `compatibility`.

The `passport` field is **REQUIRED** for registry entries where
`compatibility ≥ 1` AND the adapter is bound to a single repository.
The `passport` field is **OPTIONAL** for generic/parametric adapters
(`auto`, `obsidian`, `arxiv`, `github_topic`, `jsonl`) which are not
tied to one specific repository — their contract is defined by the
adapter class, not by a per-instance passport.

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

The `bridges` field declares typed semantic relationships between this
repository and other formats. As of v1.2, bridges are machine-readable
JSON arrays with formal typing. See **§15 Bridge Algebra** for the full
schema, the five bridge types, and the operations `invert`, `compose`,
and `transitive_closure`.

Legacy natural-language bridges (dict of strings) remain readable by
v1.2 implementations but SHOULD be migrated to the typed form.

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

### 8.1. Current Ecosystem Distribution (v1.2)

| Level | Count | Repositories |
|-------|------:|-------------|
| 3 | 1 | pro2 |
| 2 | 8 | data7, infosystems, ai_agents, graphrag, daten22, continuum, ai_research, legal |
| 1 | 3 | info1, meta, data2 |
| 0 | 2 | conversations, sessions (transient sources) |

Total registered adapters: **14**. Passports: **12** (generic adapters
`auto`, `obsidian`, `arxiv`, `github_topic`, `jsonl` are exempt per §6.2).

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

Q6 is **layered**: some bits carry semantic load, others are organisational.
Hamming distance is a useful proximity metric precisely because the
namespace is not random — but it is not a pure ontology either.

| Bits | Role | Axis |
|------|------|------|
| `b5 b4` | Semantic | CA-class (I–IV) from Wolfram classification |
| `b3 b2` | Semantic | Abstraction level (coarse α-projection) |
| `b1 b0` | Organisational | Intra-class discriminator, assigned by adapter |

- **Hamming distance** between two Q6 addresses is the semantic proximity
  metric. Distance 1 = one bit flip = "semantically adjacent".
- **Neighborhood query**: given a Q6 address and radius `k`, the portal
  returns all entries within Hamming distance ≤ k using BFS.
- **CA classification**: bits `b5 b4` map to Wolfram Cellular Automaton
  classes (I–IV), providing the primary semantic axis.
- **I-Ching correspondence**: all 64 vertices correspond bijectively to the
  64 hexagrams, providing a symbolic namespace.

Implementations MUST NOT assume full Q6 equality implies concept equality —
two entries with the same Q6 from different adapters are **Q6-collisions**
(§9.5), not duplicates.

### 9.3. Per-Format Projection Rules

Each adapter defines a rule mapping its native entities to Q6. The rule
MAY be deterministic (computable from source data) or curated (assigned
by the adapter author). Both are conformant; determinism is RECOMMENDED
but not REQUIRED.

| Adapter | Projection Rule | Type |
|---------|----------------|------|
| info1 | `alpha_level + 4` → top 3 bits | deterministic |
| pro2 | native Q6 coordinates | source-native |
| meta | `hex_id − 1 → bin(6)` | deterministic |
| data7 | `ordinal % 64 → bin(6)` | deterministic |
| data2 | curated (ETD volume → Q6) | curated |
| infosystems | `"101001"` (architecture domain) | domain-anchored |
| ai_agents | `"110100"` (multi-agent / orchestration) | domain-anchored |
| graphrag | `"110001"` (graph + retrieval) | domain-anchored |
| daten22 | `"101010"` (architecture / systems) | domain-anchored |
| legal | `"100010"` (analysis / rules / law) | domain-anchored |
| continuum | `"110100"` (multi-agent / orchestration) | domain-anchored |
| ai_research | `"110100"` (multi-agent / methodology) | domain-anchored |

**Domain-anchored** means all entries from that adapter share one Q6 base
address, with intra-adapter variation in bits `b1 b0` only. This is a
valid conformance pattern for adapters whose knowledge is uniformly located
in one semantic region.

### 9.4. Q6 Collisions

At 207 entries over 64 vertices, density averages ~3 entries/vertex.
Multiple entries MAY share a Q6 address. The portal MUST order colliding
entries by:

1. Relevance score (§5.1), descending
2. Adapter registration order (deterministic tie-break)
3. Entry `id` lexicographically (final tie-break)

### 9.5. Gap Detection

Vertices with no real (non-fallback) entries are **gaps**. The gap detector
(`gap_detection.py`) uses BFS to classify vertices as:

- **Real**: ≥1 non-fallback entry
- **Weak**: only fallback entries
- **Gap**: no entries

Current state: 14 real / 19 weak / 31 gap (48.4% uncovered).

> Note: §9.5 was renumbered from §9.4 in v1.2 to make room for §9.4 Q6 Collisions.

---

## 10. Consensus Algorithm

### 10.1. Definition (v1.2)

For a query `q`, the portal queries all registered adapters and computes:

```python
present_in          = [a for a in adapters if any non-fallback entry]
present_in_fallback = [a for a in adapters if only fallback entries]
missing_in          = [a for a in adapters if no entries at all]

# Denominator is in-domain adapters only when q6_range is declared (§3.3, §5)
in_domain_adapters  = [a for a in adapters
                         if a.q6_range == "*" or query_q6 ∈ a.q6_range]

coverage             = len(present_in ∩ in_domain_adapters) / len(in_domain_adapters)
coverage_with_fallback = (present + fallback) / in_domain

universal            = (coverage >= 1.0)     # all in-domain adapters agree
majority             = (coverage >= 0.5)     # ≥ half agree
agreed               = universal              # backward-compatible alias
```

The `agreed` field is retained as an alias for `universal` for v1.1
backward compatibility. New implementations SHOULD consume `universal`
and `majority` directly.

### 10.2. Consensus Record

```json
{
  "query": "синтез",
  "present_in": ["pro2", "info1"],
  "present_in_fallback": ["meta", "data2"],
  "missing_in_domain": ["data7"],
  "out_of_domain": ["legal", "soz150"],
  "coverage": 0.286,
  "coverage_with_fallback": 0.571,
  "universal": false,
  "majority": false,
  "agreed": false
}
```

### 10.3. Interpretation

| Coverage | State | Meaning |
|----------|-------|---------|
| 1.0 | `universal` | Confirmed cross-format fact, in-domain adapters all agree |
| 0.5–1.0 | `majority` | Likely pattern, warrants bridging work |
| < 0.5 | — | Hypothesis, present in few formats |
| 0.0 | — | Unknown to ecosystem |

Fallback entries are deliberately excluded from `coverage` to prevent
false-positive consensus. `coverage_with_fallback` is reported separately
as a diagnostic signal (§12.3) and MUST NOT feed `universal` or `majority`.

---

## 11. REST API Semantics

The reference implementation exposes an HTTP API defined in `openapi.yaml`.
All endpoints return JSON unless noted.

### 11.1. Core Endpoints

Core endpoints MUST be implemented by any conforming v1.2 portal:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/query` | Multi-adapter search |
| `GET` | `/api/health` | Ecosystem health score 0–100 |
| `GET` | `/api/links` | Cross-link validation report |
| `GET` | `/api/describe` | Adapter descriptions |
| `GET` | `/api/neighbors` | Q6 Hamming-neighborhood query |
| `GET` | `/metrics` | Prometheus text metrics |

Extended endpoints (added in v1.2) are OPTIONAL but RECOMMENDED — see
**§17 Extended REST API**:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/bridge` | Traverse bridge graph from an entry |
| `GET` | `/api/bridge_conflicts` | Protocol 3 conflict detection |
| `GET` | `/api/bridge_summary` | Bridge registry + transitive closure |
| `GET` | `/api/annotations` | List annotations for a target |
| `POST` | `/api/annotations` | Add an annotation |
| `GET` | `/api/flags` | List Protocol 3 `needs_review` flags |

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
| v1.1 | Superseded | 7 repos, REST API, Q6, TF-IDF, mypy clean |
| **v1.2** | **Current** | 14 repos, bridge algebra (§15), annotations (§16), extended REST (§17), layered Q6 (§9.2), domain-aware consensus (§10) |
| v1.5 | Planned | SQLite backend, JWT auth, WebSocket, bridge_path(from, to) |
| v2.0 | Future | Temporal model, learned Q6 projections, capability negotiation |

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

## 15. Bridge Algebra

Bridges are typed, machine-readable semantic relationships between
adapters. As of v1.2, the natural-language `bridges` dict from v1.1 is
superseded by a typed JSON array declared in each passport.

### 15.1. Bridge Record Schema

```json
{
  "target":      "pro2",
  "type":        "isomorphism",
  "description": "Q6-bits [b0..b5] ↔ hexagram number 1..64",
  "confidence":  0.95,
  "bidirectional": true
}
```

REQUIRED fields: `target`, `type`, `description`.
OPTIONAL fields: `confidence` (0.0–1.0, default 1.0), `bidirectional`
(default `false`), `example` (concrete from/to illustration).

### 15.2. Bridge Types

| Type | Description | Invertible? |
|------|-------------|:---:|
| `isomorphism` | Bijective correspondence; A ↔ B structurally identical | ✓ |
| `projection` | Lossy; A → subset of B | ✗ |
| `embedding` | A ⊂ B fully contained | partial |
| `analogy` | Structural similarity without strict mapping | ✓ |
| `derivation` | B computable from A deterministically | ✗ |

### 15.3. Operations

Implementations MUST support three algebraic operations over the
bridge graph:

**invert(bridge) → bridge**
  Flips direction. `confidence` × 0.95 (reflecting evidence decay on
  auto-derivation). Sets `_inverted = true` metadata flag.

**compose(ab, bc) → ac | None**
  Chains two bridges A→B and B→C into A→C. Returns `None` if
  `ab.target ≠ bc.source`. Composed bridge has `type = "derivation"`
  and `confidence = min(ab.confidence, bc.confidence)`.

**transitive_closure(source, max_hops) → list[bridge]**
  Breadth-first traversal from `source` adapter across the bridge
  graph, including auto-inverted edges. Returns reachable adapters
  with their shortest-path confidence and hop count. `max_hops`
  MUST be bounded (default 3) to prevent exponential blowup.

### 15.4. Protocol 3 Conflict Detection

`detect_conflicts(entries) → list[BridgeConflict]` inspects the
portal's entry set and emits a `BridgeConflict` record whenever:

- Two adapters declare the **same concept** (by normalised title)
  but assign it Q6 addresses with Hamming distance > 0, OR
- Two adapters declare bridges to each other with inconsistent
  types (e.g. A declares `isomorphism` to B, B declares `analogy`
  to A).

```json
{
  "entry_a":  "pro2:hexagram_42",
  "entry_b":  "meta:rule_110100",
  "from_repo": "pro2",
  "to_repo":   "meta",
  "reason":    "Q6 coordinate mismatch: 110100 vs 110001",
  "severity":  "warning"
}
```

Severity: `info` (Hamming ≤ 1), `warning` (Hamming = 2), `error`
(Hamming > 2 or bridge-type mismatch).

Conflicts feed the annotation system (§16) as automatic
`needs_review` flags authored by the portal itself.

---

## 16. Annotations and Protocol 3

Annotations are a first-class overlay on `PortalEntry` records, allowing
any participant — human user or adapter-agent — to attach notes, flags,
and links to any entry independent of its source format.

### 16.1. Annotation Record

```python
@dataclass
class Annotation:
    id: str               # "annot:<12-hex-chars>"
    target: str           # PortalEntry id being annotated
    author: str           # user name | adapter name | "assistant"
    content: str          # annotation body
    visibility: str       # "private" | "team" | "public"
    created_at: float     # Unix timestamp
    tags: list[str]       # free-form tags
    thread_parent: str    # parent annotation id (threading)
```

`id` MUST be globally unique and opaque. Adapters MUST NOT parse `id`
beyond the `annot:` prefix.

### 16.2. Visibility

| Level | Semantics |
|-------|-----------|
| `private` | Visible only to the author |
| `team` | Visible within a trust group (implementation-defined) |
| `public` | Visible to any portal consumer |

Visibility is advisory at the protocol level — enforcement is the
deployment's responsibility. Public portals MUST filter `private` and
`team` annotations from unauthenticated responses.

### 16.3. Protocol 3: Agent-Authored Flags

**Protocol 3** is the subset of the annotation system where an
adapter-agent automatically creates annotations to signal issues
requiring human attention.

```python
portal.flag_for_review(
    target="legal:dsgvo_art15",
    author="legal",
    reason="GDPR personal-data handling requires review",
    severity="warning",   # "info" | "warning" | "error"
)
```

Protocol 3 flags MUST have:

- `tags` containing `"needs_review"` and the severity level
- `visibility = "team"` (default; deployments MAY override)
- `content` prefixed with `[SEVERITY] ` for log-friendly parsing

### 16.4. Storage

`AnnotationStore` MUST support two backends:

- **Persistent** — SQLite by default; other durable backends are
  implementation-defined. File MUST be excluded from VCS.
- **In-memory** — for tests and ephemeral deployments. Selected
  when the store is constructed with `db_path=None`.

### 16.5. Conversation Branches (Forward-Compatibility)

The protocol reserves the `ConversationBranch` record for git-like
branching of conversations. v1.2 defines the data schema and store
methods but does not mandate REST exposure. Implementations MAY add
`/api/branches` endpoints; v1.5 is expected to standardise them.

---

## 17. Extended REST API

v1.2 adds six OPTIONAL endpoints. A conforming v1.2 portal SHOULD
implement all six; minimal deployments MAY implement only the core
six (§11.1).

### 17.1. Bridge Endpoints

```
GET /api/bridge?id=<entry_id>&hops=<n>    default n=1, max 3
```

Returns the entry graph reachable from `entry_id` through ≤ `hops`
bridge steps. Response: `PortalResult` shape with `query = "bridge:<id>±<n>"`.

```
GET /api/bridge_conflicts
```

Returns list of `BridgeConflict` records (§15.4). Empty list means
no conflicts detected.

```
GET /api/bridge_summary
```

Returns `{adapters_with_bridges, total_bridges, by_type,
transitive_closure}` where `transitive_closure` is a per-adapter
map of reachable targets with hop count and confidence.

### 17.2. Annotation Endpoints

```
GET  /api/annotations?target=<entry_id>[&vis=<level>][&author=<name>]
```

Returns annotations for `target`. Filters are AND-combined. Private
annotations MUST be filtered out unless the request is authenticated
as the author (authentication is deployment-defined).

```
POST /api/annotations
Content-Type: application/json

{
  "target":     "pro2:bidir",
  "author":     "svend4",
  "content":    "…",
  "visibility": "private",
  "tags":       ["wip"]
}
```

REQUIRED body fields: `target`, `author`, `content`. The portal MUST
sanitise `author` and `content` against XSS before storage.
Response: `{"id": "annot:…", "target": "…"}` with HTTP 201.

```
GET /api/flags[?severity=<level>]
```

Returns Protocol 3 annotations (tag `needs_review`), optionally
filtered by severity. Ordered by `created_at` descending.

### 17.3. CORS and Authentication

Extended endpoints inherit §11.4 CORS requirements. Write operations
(`POST /api/annotations`) SHOULD be authenticated in public
deployments — see §13.5. The reference implementation does not
enforce authentication; deployments exposing write endpoints publicly
MUST add authentication.

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
| Backstage (Spotify) | Push-model service catalog via `catalog-info.yaml`; NPP is pull-model — portal reads adapters. Closest in spirit, architecturally opposite. |
| IPLD / IPFS | Content-addressed federation with canonical hashing; NPP is query-time translation, identity via `{adapter}:{slug}`. |
| Bazel workspaces | Build-system federation via `WORKSPACE` files; NPP is knowledge federation — related framing, different domain. |

### Contrast with Backstage

Backstage aggregates engineering metadata by having each service
register a YAML manifest which Backstage scrapes on a schedule
(push model). NPP inverts this: adapters are active readers that
translate source data into `PortalEntry` records on query
(pull model). Push scales linearly with source count; pull scales
with query rate. NPP chose pull because knowledge sources (info1,
pro2, etc.) change on human edit cycles and rarely need real-time
propagation, whereas a portal may serve many query shapes from the
same underlying data.

---

*Nautilus Portal Protocol v1.2 · svend4/nautilus · 2026-04-19*
