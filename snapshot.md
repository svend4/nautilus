# ⬡ Nautilus Ecosystem Snapshot

![health](https://img.shields.io/badge/health-82%25-brightgreen)
![entries](https://img.shields.io/badge/entries-90-blue)
![links](https://img.shields.io/badge/cross--links-127-blue)

*Generated: 2026-04-19T11:58:53Z*

**Score: 82/100** `[████████████████░░░░]`

## Adapters

| Adapter | Entries (real) | Entries (fallback) | Q6 | Links |
|---------|---------------|-------------------|----|----|
| ✅ ai_agents | 1 | 0 | ✓ | 0ms |
| ✅ data2 | 0 | 3 | ✓ | 0ms |
| ✅ data7 | 4 | 0 | ✓ | 0ms |
| ✅ info1 | 0 | 11 | ✓ | 69ms |
| ✅ infosystems | 3 | 0 | ✓ | 0ms |
| ✅ meta | 0 | 8 | ✓ | 0ms |
| ✅ pro2 | 0 | 46 | ✓ | 0ms |

## Cross-Adapter Links (sample)

- `ai_agents:bidir_agent` → `data7:missing_loop` (ai_agents ↔ data7)
- `ai_agents:self_train` → `data7:theory:transformation` (ai_agents ↔ data7)
- `ai_agents:bidir_agent` → `infosystems:knowledge_graph` (ai_agents ↔ infosystems)
- `ai_agents:bidir_agent` → `pro2:bidir` (ai_agents ↔ pro2)
- `ai_agents:nautilus_hierarchy` → `pro2:nautilus` (ai_agents ↔ pro2)
- `ai_agents:nautilus_hierarchy` → `pro2:six_sources` (ai_agents ↔ pro2)
- `ai_agents:self_train` → `pro2:self_train` (ai_agents ↔ pro2)
- `ai_agents:generator` → `pro2:generate` (ai_agents ↔ pro2)
- `ai_agents:generator` → `pro2:speculative` (ai_agents ↔ pro2)
- `ai_agents:hmoe_curriculum` → `pro2:hmoe` (ai_agents ↔ pro2)
- `ai_agents:hmoe_curriculum` → `pro2:domain_routing` (ai_agents ↔ pro2)
- `data2:etd` → `info1:methodology` (data2 ↔ info1)
- `data2:three_spheres` → `info1:alpha:-1` (data2 ↔ info1)
- `data2:arch:синтез` → `info1:alpha:3` (data2 ↔ info1)
- `data2:vol:20` → `info1:alpha:0` (data2 ↔ info1)
- `data2:vol:40` → `info1:alpha:1` (data2 ↔ info1)
- `data2:vol:150` → `info1:alpha:3` (data2 ↔ info1)
- `data2:vol:310` → `info1:alpha:3` (data2 ↔ info1)
- `data2:vol:4` → `info1:alpha:-1` (data2 ↔ info1)
- `data2:vol:2` → `info1:alpha:-1` (data2 ↔ info1)

## Issues

- ⚠️  Только fallback-записи: info1, pro2, meta, data2
- ⚠️  Низкий консенсус: knowledge, синтез

## Ecosystem Graph

```mermaid
graph LR
    ai_agents["ai_agents\n[real=8 fb=0]"]
    data2["data2\n[real=6 fb=9]"]
    data7["data7\n[real=5 fb=0]"]
    info1["info1\n[real=0 fb=55]"]
    infosystems["infosystems\n[real=7 fb=0]"]
    meta["meta\n[real=0 fb=40]"]
    pro2["pro2\n[real=0 fb=230]"]

    ai_agents --> data7
    ai_agents --> infosystems
    ai_agents --> pro2
    data2 --> info1
    data2 --> meta
    data2 <--> pro2
    data7 <--> pro2
    info1 <--> meta
    info1 <--> pro2
    infosystems --> data2
    infosystems --> data7
    infosystems --> meta
    infosystems <--> pro2
    meta <--> pro2

    %% Adapter colours
    style ai_agents fill:#ec4899,color:#fff,stroke:#333
    style data2 fill:#10b981,color:#fff,stroke:#333
    style data7 fill:#f59e0b,color:#fff,stroke:#333
    style info1 fill:#1f6feb,color:#fff,stroke:#333
    style infosystems fill:#ef4444,color:#fff,stroke:#333
    style meta fill:#8b5cf6,color:#fff,stroke:#333
    style pro2 fill:#388bfd,color:#fff,stroke:#333
```
