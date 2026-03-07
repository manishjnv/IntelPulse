# IntelWatch — ATT&CK Map Module

> Complete technical reference for the MITRE ATT&CK integration: technique sync, auto-mapping, matrix heatmap, detection gaps, and technique detail pages.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [MITRE ATT&CK Data Sync](#4-mitre-attck-data-sync)
5. [Auto-Mapping Engine](#5-auto-mapping-engine)
6. [Keyword-Technique Map](#6-keyword-technique-map)
7. [Matrix Heatmap](#7-matrix-heatmap)
8. [Detection Gaps](#8-detection-gaps)
9. [Database Schema](#9-database-schema)
10. [Scheduling & Worker Tasks](#10-scheduling--worker-tasks)
11. [Caching Strategy](#11-caching-strategy)
12. [Constants & Thresholds Reference](#12-constants--thresholds-reference)
13. [Techniques UI Layout](#13-techniques-ui-layout)
14. [Technique Detail UI Layout](#14-technique-detail-ui-layout)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                       Scheduler                              │
│  sync_attack_techniques (every 24h)                          │
│  map_intel_to_attack (every 10 min, batch 100)               │
│  remap_all_intel_to_attack (admin-triggered)                 │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              MITRE ATT&CK Service                            │
│  Fetch STIX bundle from GitHub │ Parse attack-patterns        │
│  Keyword-based auto-mapping │ 14 tactics kill-chain order     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL (TimescaleDB)                     │
│  attack_techniques │ intel_attack_links │ intel_items          │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│             FastAPI Routes (/techniques)                      │
│  List │ Matrix │ Detail │ Intel-Techniques                    │
│  Cache: Redis (120s)                                         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Frontend                             │
│  Matrix view (ATTACKMatrix) │ List view │ Detection gaps      │
│  Coverage ring │ Technique detail │ Related intel              │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend routes | `api/app/routes/techniques.py` |
| MITRE service | `api/app/services/mitre.py` |
| Worker tasks | `worker/tasks.py` |
| Frontend techniques page | `ui/src/app/(app)/techniques/page.tsx` |
| Frontend technique detail | `ui/src/app/(app)/techniques/[id]/page.tsx` |
| ATTACKMatrix component | `ui/src/components/ATTACKMatrix.tsx` |

---

## 3. API Endpoints

### `GET /api/v1/techniques`

Paginated technique list with filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tactic` | string | — | Filter by tactic slug |
| `search` | string | — | Full-text search on name |
| `has_intel` | bool | — | Only techniques with intel links |
| `page` | int | 1 | Page number |
| `page_size` | int | 50 | Max 500 |

**Cache:** 120 seconds

### `GET /api/v1/techniques/matrix`

Heatmap data grouped by tactic with intel hit counts.

**Cache:** 120 seconds

**Response:** Tactic → technique grid with `intel_count` for heatmap coloring.

### `GET /api/v1/techniques/{id}`

Single technique detail including related intel items and subtechniques.

**Response:** `{ technique, intel_items, subtechniques }`

### `GET /api/v1/techniques/intel/{item_id}/techniques`

Get ATT&CK techniques mapped to a specific intel item.

**Auth:** Viewer+

**Response:** Array of `IntelAttackLinkResponse`:
- `technique_id`, `confidence`, `mapping_type`
- `technique_name`, `tactic`, `tactic_label`, `url`

Ordered by tactic then technique ID.

### `POST /api/v1/admin/attack/remap`

Re-map ALL intel items to ATT&CK techniques using updated keyword map (admin only).

**Auth:** Admin only

**Behavior:** Enqueues `remap_all_intel_to_attack` on `low` queue with `job_timeout=600`. Audit-logged.

**Response:** `{ status: "queued", job_id: "..." }`

---

## 4. MITRE ATT&CK Data Sync

Source: MITRE CTI GitHub repository (STIX 2.1 JSON bundle).

```
URL: https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json
```

### Sync Process (`fetch_attack_data`)

1. Fetch full Enterprise ATT&CK STIX bundle (timeout: 60s)
2. Filter for `type = "attack-pattern"` objects
3. Skip revoked and deprecated techniques
4. Extract:
   - Technique ID from `external_references` (source: `mitre-attack`)
   - URL from `external_references`
   - Tactics from `kill_chain_phases`
   - Platforms from `x_mitre_platforms`
   - Detection guidance from `x_mitre_detection`
   - Data sources from `x_mitre_data_sources`
   - Subtechnique flag and parent ID
5. Multi-tactic techniques produce one record per tactic
6. Upsert into `attack_techniques` table

### Upsert Logic

- Existing techniques: update name, description, platforms, detection, etc.
- New techniques: insert if ID not already present under any tactic
- Multi-tactic handling: first tactic wins (PK is just `id`)

---

## 5. Auto-Mapping Engine

`map_intel_to_attack` — Maps unmapped intel items to ATT&CK techniques.

### Process

1. Get all valid technique IDs from `attack_techniques`
2. Find intel items with NO existing attack links
3. For each item, scan text (title + summary + description + tags) against `KEYWORD_TECHNIQUE_MAP`
4. Create `intel_attack_links` with confidence = 60
5. Process in batches of 100

### Remap All (Admin)

`POST /admin/attack/remap` — Clears all auto-mapped links and re-processes every intel item. Triggered when keyword map is updated.

---

## 6. Keyword-Technique Map

Located in `api/app/services/mitre.py` → `KEYWORD_TECHNIQUE_MAP`.

A large dictionary mapping keywords found in intel item text to ATT&CK technique IDs.

### Sample Mappings

| Keyword | Technique ID(s) | Tactic |
|---------|-----------------|--------|
| `phishing` | T1566 | Initial Access |
| `spearphishing` | T1566.001 | Initial Access |
| `drive-by` | T1189 | Initial Access |
| `supply chain` | T1195 | Initial Access |
| `trojanized` | T1195.002 | Initial Access |
| `powershell` | T1059.001 | Execution |
| `command injection` | T1059 | Execution |
| `scheduled task` | T1053 | Persistence |
| `privilege escalation` | T1068 | Privilege Escalation |
| `lateral movement` | T1021 | Lateral Movement |
| `data exfiltration` | T1041 | Exfiltration |
| `ransomware` | T1486 | Impact |
| `cobalt strike` | T1059.001 | Execution |
| `mimikatz` | T1003 | Credential Access |

The map covers CVE/vulnerability types, malware delivery mechanisms, network attacks, and common tool names from KEV, URLhaus, AbuseIPDB, NVD, and OTX feeds.

---

## 7. Matrix Heatmap

The `ATTACKMatrix` component renders a MITRE ATT&CK-style matrix view.

### Layout

- Columns: 14 tactics in kill-chain order
- Rows: Techniques within each tactic
- Heatmap coloring: Based on `max_risk` of linked intel items
- Click: Navigate to technique detail page

### Cell Heatmap Color Thresholds

| Condition | Background | Text Color |
|-----------|-----------|------------|
| `count === 0` | `bg-muted/20` | `text-muted-foreground/50` |
| `max_risk >= 80` | `bg-red-500/30` | `text-red-400` |
| `max_risk >= 60` | `bg-orange-500/25` | `text-orange-400` |
| `max_risk >= 40` | `bg-yellow-500/20` | `text-yellow-400` |
| else (count > 0) | `bg-blue-500/15` | `text-blue-400` |

### SeverityMicroBar Sub-Component

A stacked horizontal bar inside each technique cell showing severity distribution:

| Segment | Color | Label |
|---------|-------|-------|
| `critical` | `bg-red-500` | Critical |
| `high` | `bg-orange-500` | High |
| `medium` | `bg-yellow-500` | Medium |
| `low` | `bg-blue-500` | Low |

Width per segment = `(count / total) × 100%`. Only shown when `total > 0`.

### Per-Tactic Coverage Bar Thresholds

| Coverage % | Color Class |
|------------|------------|
| `>= 50%` | `bg-emerald-500` |
| `>= 25%` | `bg-amber-500` |
| `> 0%` | `bg-orange-500` |
| `0%` | transparent |

### ATT&CK Navigator JSON Export

Triggered from a button in the matrix header. Generates a JSON file compatible with MITRE ATT&CK Navigator.

**Layer Format:**

```json
{
  "name": "IntelWatch Coverage",
  "versions": {
    "attack": "15",
    "navigator": "5.1",
    "layer": "4.5"
  },
  "domain": "enterprise-attack",
  "techniques": [
    {
      "techniqueID": "T1566",
      "tactic": "initial_access",
      "score": 12,
      "color": "#ff6666",
      "comment": "12 intel hits, max risk: 85"
    }
  ]
}
```

**Score mapping:** `Math.min(count, 100)` — capped at 100.

**Color mapping:** Same thresholds as cell heatmap (`max_risk >= 80` → `#ff6666`, `>= 60` → `#ff9933`, `>= 40` → `#ffcc00`, else → `#6699ff`).

**Filename:** `intelwatch-attack-layer-YYYY-MM-DD.json`

Only techniques with `count > 0` are included. Tactic slugs are converted from kebab-case to underscore format.

---

## 8. Detection Gaps

Techniques with NO intel hits are flagged as detection gaps.

### Server-Side Algorithm (`routes/techniques.py`)

1. Identify all techniques with `count == 0` (unmapped)
2. Partition by **7 priority tactics**:
   - `initial-access`, `execution`, `persistence`, `privilege-escalation`, `defense-evasion`, `lateral-movement`, `impact`
3. Priority-tactic gaps listed first, then remaining tactics
4. Combined list truncated to **top 20 gaps**
5. Each gap includes: `id`, `name`, `tactic`, `tactic_label`, `platforms`, `url`

### Display

- Orange-tinted card on the techniques page
- Multi-column grid layout (1–4 columns)
- Shows first 12 gaps with "Show More" button
- Each gap links to `/techniques/{id}`
- Includes tactic summary chips for context

---

## 9. Database Schema

### `attack_techniques`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | VARCHAR(20) | PK (e.g., T1059, T1059.001) |
| `name` | VARCHAR(255) | NOT NULL |
| `tactic` | VARCHAR(50) | e.g., execution, persistence |
| `tactic_label` | VARCHAR(100) | e.g., Execution, Persistence |
| `description` | TEXT | Truncated to 2000 chars |
| `url` | TEXT | MITRE ATT&CK URL |
| `platforms` | TEXT[] | e.g., {Windows, Linux, macOS} |
| `detection` | TEXT | Detection guidance, 2000 chars |
| `is_subtechnique` | BOOLEAN | default FALSE |
| `parent_id` | VARCHAR(20) | e.g., T1059 for T1059.001 |
| `data_sources` | TEXT[] | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### `intel_attack_links`

| Column | Type | Constraints |
|--------|------|------------|
| `intel_id` | UUID | FK to intel_items |
| `intel_ingested_at` | TIMESTAMPTZ | Composite FK |
| `technique_id` | VARCHAR(20) | FK to attack_techniques |
| `confidence` | SMALLINT | 0–100, default 50 |
| `mapping_type` | VARCHAR(30) | `auto` \| `manual`, default `auto` |
| `created_at` | TIMESTAMPTZ | |

**PK:** `(intel_id, intel_ingested_at, technique_id)`

---

## 10. Scheduling & Worker Tasks

| Task | Interval | Queue | Description |
|------|----------|-------|-------------|
| `sync_attack_techniques` | 24 hours | `low` | Fetch MITRE STIX bundle and upsert techniques |
| `map_intel_to_attack` | 10 minutes | `low` | Auto-map unmapped intel items (batch 100) |
| `ingest_feed("mitre_attack")` | 24 hours | `low` | Feed connector for ATT&CK data |

Start delays: `sync` runs immediately, `map` starts after 2-minute delay.

---

## 11. Caching Strategy

| Endpoint | Cache TTL |
|----------|-----------|
| `GET /techniques` | 120 seconds |
| `GET /techniques/matrix` | 120 seconds |

---

## 12. Constants & Thresholds Reference

### 14 ATT&CK Tactics (Kill-Chain Order)

| # | Slug | Label |
|---|------|-------|
| 1 | `reconnaissance` | Reconnaissance |
| 2 | `resource-development` | Resource Development |
| 3 | `initial-access` | Initial Access |
| 4 | `execution` | Execution |
| 5 | `persistence` | Persistence |
| 6 | `privilege-escalation` | Privilege Escalation |
| 7 | `defense-evasion` | Defense Evasion |
| 8 | `credential-access` | Credential Access |
| 9 | `discovery` | Discovery |
| 10 | `lateral-movement` | Lateral Movement |
| 11 | `collection` | Collection |
| 12 | `command-and-control` | Command and Control |
| 13 | `exfiltration` | Exfiltration |
| 14 | `impact` | Impact |

### Tactic Colors (Frontend)

| Tactic | Tailwind Color |
|--------|---------------|
| initial-access | red-400 |
| execution | orange-400 |
| persistence | amber-400 |
| privilege-escalation | yellow-400 |
| defense-evasion | emerald-400 |
| lateral-movement | cyan-400 |
| impact | rose-400 |

### Coverage Ring Thresholds

| Coverage % | Color |
|------------|-------|
| ≥ 50% | Emerald |
| ≥ 25% | Amber |
| ≥ 10% | Orange |
| < 10% | Red |

### Coverage Ring SVG

- Radius: 38
- Stroke width: 6
- Viewport: 90×90px

### Auto-Mapping Confidence

Default confidence for auto-mapped links: **60**

---

## 13. Techniques UI Layout

Layout of `techniques/page.tsx`:

1. **Header** — Title + external MITRE ATT&CK link button
2. **Stats Grid** (4 items):
   - CoverageRing (SVG donut)
   - Total Techniques count
   - Techniques With Intel Hits
   - Tactics Covered
3. **Detection Gaps Card** — Orange-tinted card with grid, linked technique chips
4. **View Toggle** — Tabs: Matrix View / List View
5. **Search + Filters** — Search input + "Intel Hits Only" toggle + tactic pill buttons
6. **Matrix View** → `<ATTACKMatrix>` component
7. **List View** → `TechniqueRow` expandable accordion rows (description, data sources, MITRE link)

---

## 14. Technique Detail UI Layout

Layout of `techniques/[id]/page.tsx`:

1. **Back + Header** — Back button + technique ID badge + name + tactic badge + parent link + MITRE external link
2. **Stats Row** (4 stats): Intel Hits (blue), Sub-techniques (purple), Platforms (green), Data Sources (orange)
3. **Description Card**
4. **Detection Guidance Card** (green title, conditional)
5. **Platforms & Data Sources** — Two-column badge lists
6. **Sub-techniques Card** — Linked list with intel counts
7. **Related Intel Table** — Title, Severity, Risk, Source, Date columns

### Severity Colors in Detail Page

| Severity | Hex Color |
|----------|-----------|
| `critical` | `#ef4444` |
| `high` | `#f97316` |
| `medium` | `#eab308` |
| `low` | `#22c55e` |
| `info` / `unknown` | `#6b7280` |

---

## 15. Future Enhancements

- ML-based technique mapping (replace/augment keyword map)
- Technique-based alerting rules
- Campaign tracking through technique clustering
- ATT&CK coverage trend over time
- Custom technique annotations by analysts
- Detection rule generation from technique data sources
