# IntelPulse — Reports Module

> Complete technical reference for Report Management: templates, section editing, AI generation, linked items, status workflow, and multi-format export.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [Report Templates](#4-report-templates)
5. [Status Workflow](#5-status-workflow)
6. [Section Management](#6-section-management)
7. [AI Generation](#7-ai-generation)
8. [Linked Items](#8-linked-items)
9. [Export Formats](#9-export-formats)
10. [Database Schema](#10-database-schema)
11. [Constants & Thresholds Reference](#11-constants--thresholds-reference)
12. [Reports List UI Layout](#12-reports-list-ui-layout)
13. [Report Detail UI Layout](#13-report-detail-ui-layout)
14. [New Report UI Layout](#14-new-report-ui-layout)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL (TimescaleDB)                     │
│  reports │ report_items │ users                               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Routes (/reports)                        │
│  12 endpoints: CRUD │ Templates │ Stats │ Linked Items       │
│  AI Summary │ AI Sections │ Export (5 formats)               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Frontend                             │
│  Report list (/reports) │ Detail (/reports/[id])              │
│  New report wizard (/reports/new) │ MarkdownContent renderer  │
│  Inline section editing │ AI generation button                │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend routes | `api/app/routes/reports.py` |
| Backend service | `api/app/services/reports.py` |
| Frontend list page | `ui/src/app/(app)/reports/page.tsx` |
| Frontend detail page | `ui/src/app/(app)/reports/[id]/page.tsx` |
| Frontend new page | `ui/src/app/(app)/reports/new/page.tsx` |
| Markdown renderer | `ui/src/components/MarkdownContent.tsx` |
| StatCard | `ui/src/components/StatCard.tsx` |

---

## 3. API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/reports` | Paginated list with filters | `require_viewer` |
| `POST` | `/reports` | Create new report | `require_viewer` |
| `GET` | `/reports/templates` | Get all templates | `require_viewer` |
| `GET` | `/reports/stats` | Report statistics | `require_viewer` |
| `GET` | `/reports/{id}` | Single report detail | `require_viewer` |
| `PUT` | `/reports/{id}` | Update report | `require_viewer` |
| `DELETE` | `/reports/{id}` | Delete report | `require_viewer` |
| `GET` | `/reports/{id}/items` | Get linked items | `require_viewer` |
| `POST` | `/reports/{id}/items` | Link item to report | `require_viewer` |
| `DELETE` | `/reports/{id}/items/{item_id}` | Unlink item | `require_viewer` |
| `POST` | `/reports/{id}/ai-summary` | Generate AI summary | `require_viewer` |
| `POST` | `/reports/{id}/ai-sections` | Generate AI sections | `require_viewer` |
| `GET` | `/reports/{id}/export` | Export report | `require_viewer` |

### List Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | draft, review, published, archived |
| `report_type` | string | incident, threat_advisory, weekly_summary, ioc_bulletin, custom |
| `search` | string | Title search |
| `page` | int | Page number |
| `page_size` | int | Items per page |

---

## 4. Report Templates

5 built-in templates, each defining a set of sections:

### Incident Report (11 sections)

| # | Section |
|---|---------|
| 1 | Executive Summary |
| 2 | Incident Timeline |
| 3 | Technical Analysis |
| 4 | Indicators of Compromise |
| 5 | Affected Systems |
| 6 | Attack Vector Analysis |
| 7 | MITRE ATT&CK Mapping |
| 8 | Containment Actions |
| 9 | Remediation Steps |
| 10 | Lessons Learned |
| 11 | Appendix |

### Threat Advisory (11 sections)

| # | Section |
|---|---------|
| 1 | Executive Summary |
| 2 | Threat Overview |
| 3 | Technical Details |
| 4 | Affected Products |
| 5 | Exploitation Analysis |
| 6 | Indicators of Compromise |
| 7 | MITRE ATT&CK Mapping |
| 8 | Detection Guidance |
| 9 | Mitigation Recommendations |
| 10 | References |
| 11 | Appendix |

### Weekly Summary (7 sections)

| # | Section |
|---|---------|
| 1 | Executive Summary |
| 2 | Key Threats This Week |
| 3 | Vulnerability Highlights |
| 4 | IOC Summary |
| 5 | Trend Analysis |
| 6 | Recommendations |
| 7 | Appendix |

### IOC Bulletin (7 sections)

| # | Section |
|---|---------|
| 1 | Executive Summary |
| 2 | IOC Overview |
| 3 | Detailed IOC Analysis |
| 4 | Associated Threats |
| 5 | Detection Rules |
| 6 | Mitigation Steps |
| 7 | References |

### Custom (5 sections)

| # | Section |
|---|---------|
| 1 | Executive Summary |
| 2 | Analysis |
| 3 | Findings |
| 4 | Recommendations |
| 5 | Appendix |

---

## 5. Status Workflow

```
draft → review → published → archived
```

| From | To | Action Label |
|------|----|-------------|
| `draft` | `review` | Submit for Review |
| `review` | `published` | Publish |
| `published` | `archived` | Archive |

**Status metadata:**

| Status | Color | Icon |
|--------|-------|------|
| `draft` | gray | Clock |
| `review` | amber | Eye |
| `published` | emerald | CheckCircle |
| `archived` | zinc | Archive |

---

## 6. Section Management

Sections are stored in `content` JSONB field as an array:

```json
[
  {"title": "Executive Summary", "body": "...markdown content..."},
  {"title": "Technical Analysis", "body": ""},
  ...
]
```

### Editing Modes

1. **Global Edit** — All sections editable simultaneously via textareas
2. **Inline Edit** — Single section editing with Save/Cancel per section

### Section Progress Bar

The UI displays a progress bar showing `{filled}/{total} sections filled` where a section is "filled" if its body is non-empty.

### Executive Summary Sync

When saving the "Executive Summary" section inline, the report's `summary` field is automatically synced.

---

## 7. AI Generation

### AI Summary (Prompt B)

`POST /reports/{id}/ai-summary` — Generates an executive summary from linked items.

**Config:** `max_tokens=400`, `temperature=0.3`, cache prefix `report_ai_summary`

**System prompt:**
```
You are a cybersecurity threat intelligence analyst writing an executive summary
for a formal threat intelligence report. Based on the report title, sections, and
linked intelligence items provided, write a concise executive summary (3-5 sentences).
Cover: what the threat is, who/what is affected, the severity and urgency, and
recommended actions. Use professional, direct language suitable for C-level briefings.
```

### AI Full Section Generation (Prompt C)

`POST /reports/{id}/ai-generate` — Generates content for ALL sections.

**Config:** `max_tokens=4000`, `temperature=0.25`

**Research Phase:** Before generating, the system runs 4 parallel research queries via `services/research.py`:

| Source | Method | Details |
|--------|--------|---------|
| Local OpenSearch | Multi-match fuzzy | `title^3, description^2, summary` |
| NVD API | CVE lookup or keyword search | Parses CVSS, exploitability, affected CPEs, references |
| DuckDuckGo HTML | Web search | `"{keywords} cybersecurity threat advisory 2026"` |
| OTX API | Pulse search | Indicators, adversary, targeted countries |

Keyword extraction: removes 50+ stop words, takes first 8 meaningful tokens.

**System prompt (summarized key rules):**
- Respond ONLY with valid JSON: `{"summary": "...", "sections": {"section_key": "markdown content"}}`
- Section content MUST use Markdown: **bold**, bullet points, numbered lists, `### sub-headings`, `| tables |`, `inline code`, `> blockquotes`, `[links](URL)`, `---` rules
- Section-specific guidelines for: Executive Summary, Timeline, Confirmation Status, Exploitability, PoC/Exploit Availability, Impacted Technologies, Affected Organizations, IOC sections (table format), Recommendations, References
- Cite sources: "According to NVD...", "OTX pulse indicates..."
- Include actual CVE IDs, CVSS scores, dates, product names from research
- If research data lacks info: `> No confirmed data available — manual analysis recommended`

**User prompt:**
```
Generate content for all sections of this threat intelligence report.

REPORT CONTEXT:
{report title, type, severity, linked items}

LIVE RESEARCH DATA:
{formatted research from 4 sources}

SECTIONS TO FILL:
{section_key: section_title for each empty section}
```

---

## 8. Linked Items

Reports can link to multiple entity types:

| Item Type | Description |
|-----------|-------------|
| `intel` | Intel items from feeds |
| `ioc` | Indicators of Compromise |
| `technique` | MITRE ATT&CK techniques |

**Counter fields** updated on add/remove:
- `linked_intel_count`
- `linked_ioc_count`
- `linked_technique_count`

### Link Panel

The detail page has a search panel for finding and linking items:
- Search by title/value
- Shows type-colored badge, severity, risk score
- Remove button for unlinking

---

## 9. Export Formats

`GET /reports/{id}/export?format={format}`

| Format | Content Type | Description |
|--------|-------------|-------------|
| `markdown` | `text/markdown` | Full report as Markdown |
| `pdf` | `application/pdf` | Formatted PDF with TLP watermarks |
| `html` | `text/html` | Styled HTML document |
| `stix` | `application/json` | STIX 2.1 bundle (see below) |
| `csv` | `text/csv` | Flat CSV of sections |

### TLP Watermark

PDF exports include TLP-level watermarks when TLP is set. Toggle via `include_tlp_watermark` boolean parameter.

### STIX 2.1 Export

Generates a STIX 2.1 bundle JSON containing:
- `report` SDO with sections as description
- `vulnerability` SDOs for linked CVEs
- `indicator` SDOs for linked IOCs
- `attack-pattern` SDOs for linked techniques
- `relationship` SROs connecting report to all linked objects
- Bundle metadata: `type: "bundle"`, `spec_version: "2.1"`

---

## 10. Database Schema

### `reports`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `gen_random_uuid()` |
| `title` | VARCHAR(500) | NOT NULL |
| `summary` | TEXT | |
| `content` | JSONB | Section array, default `{}` |
| `report_type` | report_type | ENUM, default `custom` |
| `status` | report_status | ENUM, default `draft` |
| `severity` | severity_level | ENUM, default `medium` |
| `tlp` | tlp_level | ENUM, default `TLP:GREEN` |
| `author_id` | UUID | FK to users, NOT NULL |
| `template` | VARCHAR(50) | Template name used |
| `linked_intel_count` | INTEGER | default 0 |
| `linked_ioc_count` | INTEGER | default 0 |
| `linked_technique_count` | INTEGER | default 0 |
| `tags` | TEXT[] | GIN indexed |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `published_at` | TIMESTAMPTZ | nullable |

### `report_items`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK |
| `report_id` | UUID | FK to reports, CASCADE |
| `item_type` | VARCHAR(30) | intel, ioc, technique |
| `item_id` | TEXT | |
| `item_title` | TEXT | |
| `item_metadata` | JSONB | default `{}` |
| `added_by` | UUID | FK to users |
| `notes` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

**Unique:** `(report_id, item_type, item_id)`

---

## 11. Constants & Thresholds Reference

### Status Configuration

| Status | CSS Color | Icon | Next Status |
|--------|-----------|------|------------|
| `draft` | gray | Clock | review |
| `review` | amber | Eye | published |
| `published` | emerald | CheckCircle | archived |
| `archived` | zinc | Archive | — |

### Type Configuration

| Type | Icon | Color |
|------|------|-------|
| `incident` | AlertTriangle | red-400 |
| `threat_advisory` | Shield | blue-400 |
| `weekly_summary` | BarChart3 | emerald-400 |
| `ioc_bulletin` | FileWarning | orange-400 |
| `custom` | FileText | purple-400 |

### Severity Colors

| Severity | Tailwind Class |
|----------|---------------|
| `critical` | red-400 |
| `high` | orange-400 |
| `medium` | yellow-400 |
| `low` | blue-400 |
| `info` | cyan-400 |

### TLP Colors

| Level | Color |
|-------|-------|
| `TLP:RED` | Red |
| `TLP:AMBER+STRICT` | Amber |
| `TLP:AMBER` | Amber |
| `TLP:GREEN` | Green |
| `TLP:CLEAR` | Slate |

---

## 12. Reports List UI Layout

Layout of `reports/page.tsx`:

1. **Header** — Title + report count + Refresh/Filters/New Report buttons
2. **Stats Grid** (4 cards) — Total, Drafts, In Review, Published
3. **Filters Card** (collapsible) — Search input + status badge toggles + type badge toggles + Clear/Apply
4. **Report List** — `ReportRow` cards (loading skeleton / empty state / list):
   - Type icon + title + status badge + severity + type label
   - TLP level + linked count + tags
   - Time ago + chevron
5. **Pagination**

---

## 13. Report Detail UI Layout

Layout of `reports/[id]/page.tsx`:

1. **Header** — Back button + title (editable) + status/type/severity/TLP badges + author
2. **Action Buttons**:
   - Edit All / Cancel + Save
   - Status workflow (Submit/Publish/Archive)
   - AI Generate
   - Export dropdown (PDF/MD/HTML/STIX/CSV)
   - Delete
3. **Section Progress Bar** — `{filled}/{total} sections filled` + linked items count
4. **Metadata Row** (edit mode) — Severity badges, TLP badges, tags input
5. **Tags** (view mode)
6. **Content Sections** — Numbered cards:
   - Global edit mode: textarea per section
   - Inline edit mode: textarea with Save/Cancel per section
   - View mode: `<MarkdownContent>` or empty placeholder
7. **Link Intel Items** — Search panel + linked items list with `LinkedItemRow`
8. **Timestamps** — Created/updated/published

---

## 14. New Report UI Layout

Two-step wizard (`reports/new/page.tsx`):

### Step 1: Choose Report Type
- 3-column grid of type buttons with icons, descriptions, and animated pulse dot

### Step 2: Report Details
- Title input (type-specific placeholder)
- Severity selector (pill buttons)
- TLP selector (pill buttons with tooltip descriptions)
- Tags input (comma-separated)
- Create button

**Type-specific placeholders:**
- Incident: "Ransomware Incident — LockBit 3.0 Detected"
- Threat Advisory: "Critical Vulnerability Advisory — CVE-2024-XXXX"
- Weekly Summary: "Weekly Threat Intelligence Summary — Week X"
- IOC Bulletin: "IOC Bulletin — Emerging Malware Campaign"
- Custom: "Custom Report Title"

---

## 15. Future Enhancements

- Report scheduling (auto-generate weekly summaries)
- Collaborative editing with real-time sync
- Report versioning and diff view
- Email distribution for published reports
- Custom template builder
- Report sharing via public link with TLP enforcement
- PDF template customization
