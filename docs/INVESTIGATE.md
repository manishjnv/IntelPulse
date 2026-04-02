# IntelPulse — Investigate (Graph Explorer) Module

> Complete technical reference for the Investigation Graph: relationship building, entity exploration, graph visualization, confidence scoring, and drill-down navigation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [Relationship Types](#4-relationship-types)
5. [Entity Types](#5-entity-types)
6. [Relationship Building Engine](#6-relationship-building-engine)
7. [Confidence Scoring Formulas](#7-confidence-scoring-formulas)
8. [Graph Exploration Logic](#8-graph-exploration-logic)
9. [Database Schema](#9-database-schema)
10. [Scheduling & Worker Tasks](#10-scheduling--worker-tasks)
11. [Caching Strategy](#11-caching-strategy)
12. [Constants & Thresholds Reference](#12-constants--thresholds-reference)
13. [Investigate UI Layout](#13-investigate-ui-layout)
14. [Future Enhancements](#14-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                       Scheduler                              │
│  build_relationships (every 15 min, batch 300)               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               Graph Builder Service                          │
│  IOC-based edges │ CVE-based edges │ Technique-based edges    │
│  Intel→IOC edges │ Confidence formulas │ Upsert w/ conflict  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL (TimescaleDB)                     │
│  relationships │ intel_items │ iocs │ intel_ioc_links         │
│  intel_attack_links │ attack_techniques                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                FastAPI Routes (/graph)                        │
│  Explore │ Related │ Stats │ Cache: Redis (60s–120s)         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Frontend                             │
│  Search bar + entity type + depth controls                    │
│  GraphExplorer (D3/force-directed) │ NodeDetailPanel          │
│  Click-to-select │ Double-click-to-navigate │ URL params      │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend routes | `api/app/routes/graph.py` |
| Backend service | `api/app/services/graph.py` |
| Worker task | `worker/tasks.py` → `build_relationships` |
| Frontend page | `ui/src/app/(app)/investigate/page.tsx` |
| Graph renderer | `ui/src/components/GraphExplorer.tsx` |

---

## 3. API Endpoints

### `GET /api/v1/graph/explore`

Explore entity relationships from a starting point.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_id` | string | required | UUID or string ID of starting entity |
| `entity_type` | string | required | `intel` \| `ioc` \| `technique` \| `cve` |
| `depth` | int | 2 | Hop depth (1–3) |
| `limit` | int | 100 | Max nodes returned (1–200) |

**Cache:** 60 seconds

**Response:** `{ nodes: GraphNode[], edges: GraphEdge[] }`

### `GET /api/v1/graph/related/{item_id}`

Get related intel items for a specific item.

**Cache:** 60 seconds

### `GET /api/v1/graph/stats`

Aggregate graph statistics (total relationships, avg confidence).

**Cache:** 120 seconds

---

## 4. Relationship Types

| Type | Description |
|------|-------------|
| `shares-ioc` | Two intel items share the same IOC |
| `shares-cve` | Two intel items reference the same CVE |
| `shares-technique` | Two intel items map to the same ATT&CK technique |
| `indicates` | IOC indicates threat described by intel item |
| `uses` | Threat uses a specific ATT&CK technique |
| `exploits` | Intel item exploits a specific CVE |
| `co-occurs` | Entities co-occur in the same context |

---

## 5. Entity Types

| Type | Color | Description |
|------|-------|-------------|
| `intel` | `#3b82f6` (blue) | Intel items from feeds |
| `ioc` | `#f97316` (orange) | Indicators of Compromise |
| `technique` | `#8b5cf6` (purple) | MITRE ATT&CK techniques |
| `cve` | `#ef4444` (red) | CVE identifiers |

---

## 6. Relationship Building Engine

Located in `api/app/services/graph.py` → `build_relationships_batch`.

The engine builds edges in 4 phases:

### Phase 1: IOC-Based Edges
Intel items sharing the same IOC get a `shares-ioc` relationship.
- Query: `intel_ioc_links` grouped by `ioc_id`
- Creates edges between all intel items sharing each IOC

### Phase 2: CVE-Based Edges
Intel items sharing CVE IDs get a `shares-cve` relationship.
- Query: Array overlap on `intel_items.cve_ids`
- Cross-matches items with common CVE references

### Phase 3: Technique-Based Edges
Intel items mapped to the same ATT&CK technique get a `shares-technique` relationship.
- Query: `intel_attack_links` grouped by `technique_id`
- Connects intel items through shared technique mappings

### Phase 4: Intel→IOC Direct Edges
Links each intel item directly to its associated IOCs with `indicates` relationship type.
- Query: `intel_ioc_links` join

### Upsert Strategy
Uses PostgreSQL `ON CONFLICT DO UPDATE`:
- Updates `last_seen` and `confidence` on conflict
- Prevents duplicate edges via unique index on `(source_id, source_type, target_id, target_type, relationship_type)`

---

## 7. Confidence Scoring Formulas

| Relationship Type | Formula | Cap |
|-------------------|---------|-----|
| IOC-based | `30 + (shared_count × 15)` | 90 |
| CVE-based | `40 + (shared_count × 20)` | 95 |
| Technique-based | `25 + (shared_count × 10)` | 85 |

Where `shared_count` is the number of shared items between two entities.

---

## 8. Graph Exploration Logic

The explore endpoint traverses the `relationships` table using recursive depth queries:

1. Start from `entity_id` + `entity_type`
2. Find all edges where entity is source OR target
3. For each connected entity, repeat up to `depth` hops
4. Collect unique nodes and edges up to `limit`
5. Return as graph structure with node properties

---

## 9. Database Schema

### `relationships`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `uuid_generate_v4()` |
| `source_id` | TEXT | NOT NULL |
| `source_type` | VARCHAR(30) | intel, ioc, technique, cve |
| `target_id` | TEXT | NOT NULL |
| `target_type` | VARCHAR(30) | intel, ioc, technique, cve |
| `relationship_type` | VARCHAR(50) | default `related-to` |
| `confidence` | SMALLINT | 0–100, default 50 |
| `auto_generated` | BOOLEAN | default TRUE |
| `first_seen` | TIMESTAMPTZ | |
| `last_seen` | TIMESTAMPTZ | |
| `metadata` | JSONB | Extra context (shared IOC values, keywords) |
| `created_at` | TIMESTAMPTZ | |

**Indexes:**
- `idx_rel_source` — `(source_id, source_type)`
- `idx_rel_target` — `(target_id, target_type)`
- `idx_rel_type` — `(relationship_type)`
- `idx_rel_confidence` — `(confidence DESC)`
- `idx_rel_unique_edge` — UNIQUE `(source_id, source_type, target_id, target_type, relationship_type)`

---

## 10. Scheduling & Worker Tasks

| Task | Interval | Queue | Batch Size |
|------|----------|-------|-----------|
| `build_relationships` | 15 minutes | `low` | 300 |

Start delay: 3 minutes after scheduler start (to let feeds ingest first).

---

## 11. Caching Strategy

| Endpoint | Cache TTL |
|----------|-----------|
| `GET /graph/explore` | 60 seconds |
| `GET /graph/related/{id}` | 60 seconds |
| `GET /graph/stats` | 120 seconds |

---

## 12. Constants & Thresholds Reference

### Node Type Colors (Frontend)

| Entity Type | Hex Color |
|-------------|-----------|
| `intel` | `#3b82f6` |
| `ioc` | `#f97316` |
| `technique` | `#8b5cf6` |
| `cve` | `#ef4444` |

### Risk Score Colors in Node Panel

| Threshold | Color |
|-----------|-------|
| `score >= 80` | Red |
| `score >= 50` | Orange |
| `score < 50` | Muted |

### Graph Defaults

| Setting | Value |
|---------|-------|
| Default depth | 2 |
| Min depth | 1 |
| Max depth | 3 |
| Node limit | 100 |
| Max limit | 200 |
| Graph height | 560px |
| Detail panel width | 320px |
| Connections display cap | 15 per type group |

### URL Parameters

| Param | Purpose |
|-------|---------|
| `id` | Entity ID to explore |
| `type` | Entity type |
| `depth` | Exploration depth |

---

## 13. Investigate UI Layout

Layout of `investigate/page.tsx`:

1. **Header** — Title + stats (relationship count, avg confidence)
2. **Search Card** — Input + entity-type select + depth ±stepper + Explore button
3. **Main Content** (conditional states):
   - **Loading** → `<Loading>` spinner
   - **Error** → Error card with message
   - **Graph loaded** → Flex row:
     - Left: `<GraphExplorer>` (D3/force-directed visualization)
     - Right: `<NodeDetailPanel>` (slide-in panel)
   - **Empty state** → CTA card with gradient icon

### NodeDetailPanel Sub-Component (~170 lines)

- Gradient top bar colored by entity type
- Entity icon and label
- Properties display (type-specific)
- Action buttons: Explore from here, View Detail, Open in new tab
- Connections card (grouped by relationship type, expandable)

### Interaction Model

| Action | Behavior |
|--------|----------|
| Single click on node | Select → show NodeDetailPanel, highlight connected edges |
| Double click on node | Navigate to entity detail page |
| "Explore" button | Re-center graph on selected node |
| Drag node | Reposition node within force layout (SVG point inversion) |
| Drag background | Pan the entire graph view |
| Scroll wheel | Zoom in (factor 1.12) / out (factor 0.89) |
| Hover on node | Highlight node + connected edges, dim others to opacity 0.12 |
| Hover on edge | Show tooltip with relationship type and confidence % |
| `+` / `−` buttons | Zoom in/out (factor 1.3) |
| Reset button | Return to `{ x: 0, y: 0, k: 1 }` |
| Fullscreen button | Toggle fixed `inset-0 z-50` fullscreen mode |
| `Escape` key | Exit fullscreen mode |

### Zoom Range

| Limit | Value |
|-------|-------|
| Min zoom | 0.15 (15%) |
| Max zoom | 4.0 (400%) |

Zoom percentage indicator shown at bottom-right when `k ≠ 1`.

### Fullscreen Mode

Toggled via top-right control. In fullscreen:
- Container: `fixed inset-0 z-50 bg-[#0a0e1a]`
- SVG dimensions: `100vw × calc(100vh - 60px)`
- Simulation re-runs with window dimensions
- ESC key listener added to exit

### HUD Overlays

| Position | Element |
|----------|--------|
| Top-left | Legend (color dots + type labels) |
| Top-right | Node/edge counts + zoom/reset/fullscreen buttons |
| Bottom-left | Interaction hints text |
| Bottom-right | Zoom percentage (when ≠ 100%) |

---

## 14. Future Enhancements

- Path finding between two entities
- Timeline view of relationship evolution
- Cluster detection for threat campaign analysis
- Manual relationship creation by analysts
- Export graph as image or STIX bundle
- Relationship type filtering in visualization
- Node grouping by source/type
- Saved investigation views
