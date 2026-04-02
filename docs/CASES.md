# IntelPulse — Cases Module

> Complete technical reference for Case Management: case lifecycle, status transitions, linked items, bulk operations, activity timeline, comments, and export.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [Case Lifecycle & Status Transitions](#4-case-lifecycle--status-transitions)
5. [Case Properties & Types](#5-case-properties--types)
6. [Linked Items](#6-linked-items)
7. [Activity Timeline](#7-activity-timeline)
8. [Comments](#8-comments)
9. [Bulk Operations](#9-bulk-operations)
10. [Export](#10-export)
11. [Database Schema](#11-database-schema)
12. [Constants & Thresholds Reference](#12-constants--thresholds-reference)
13. [Cases UI Layout](#13-cases-ui-layout)
14. [Future Enhancements](#14-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL (TimescaleDB)                     │
│  cases │ case_items │ case_activities │ users                 │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                FastAPI Routes (/cases)                        │
│  16 endpoints: CRUD │ Stats │ Linked items │ Comments         │
│  Bulk status/assign/delete │ Export (JSON/CSV)               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Next.js Frontend                            │
│  Case list (/cases) │ Case detail (/cases/[id])               │
│  Create modal │ Bulk actions │ Filters │ Export                │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend routes | `api/app/routes/cases.py` |
| Backend service | `api/app/services/cases.py` |
| Frontend list page | `ui/src/app/(app)/cases/page.tsx` |
| Frontend detail page | `ui/src/app/(app)/cases/[id]/page.tsx` |
| StatCard | `ui/src/components/StatCard.tsx` |
| Pagination | `ui/src/components/Pagination.tsx` |

---

## 3. API Endpoints

### Case CRUD

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/v1/cases` | Paginated list with filters | `require_viewer` |
| `POST` | `/api/v1/cases` | Create new case | `require_viewer` |
| `GET` | `/api/v1/cases/stats` | Case statistics | `require_viewer` |
| `GET` | `/api/v1/cases/assignees` | Available assignees | `require_viewer` |
| `GET` | `/api/v1/cases/{id}` | Single case detail | `require_viewer` |
| `PUT` | `/api/v1/cases/{id}` | Update case | `require_viewer` |
| `DELETE` | `/api/v1/cases/{id}` | Delete case | `require_viewer` |

### Case List Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | new, in_progress, pending, resolved, closed |
| `priority` | string | critical, high, medium, low |
| `case_type` | string | incident_response, investigation, hunt, rfi |
| `assignee_id` | UUID | Filter by assignee |
| `search` | string | Title/description search |
| `severity` | string | Severity level filter |
| `tlp` | string | TLP level filter |
| `date_from` | datetime | Start date filter |
| `date_to` | datetime | End date filter |
| `tag` | string | Tag filter |

### Linked Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/cases/{id}/items` | Get linked items |
| `POST` | `/cases/{id}/items` | Link item to case |
| `DELETE` | `/cases/{id}/items/{item_id}` | Unlink item |

### Comments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/cases/{id}/comments` | Get case comments |
| `POST` | `/cases/{id}/comments` | Add comment |

### Bulk Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/cases/bulk/status` | Bulk status change |
| `POST` | `/cases/bulk/assign` | Bulk assign |
| `POST` | `/cases/bulk/delete` | Bulk delete |

### Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/cases/export` | Export JSON or CSV |

Export parameters: `format` (json/csv), `ids` (optional, specific case IDs).

---

## 4. Case Lifecycle & Status Transitions

### Status Machine

```
┌─────┐     ┌─────────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐
│ new │────→│ in_progress │────→│ pending │────→│ resolved │────→│ closed │
└─────┘     └─────────────┘     └─────────┘     └──────────┘     └────────┘
  │               ▲   │              ▲                │               │
  │               └───┘              │                │               │
  └──────────→ pending ──────────────┘                └──→ in_progress│
                                                                      │
  new ──────────→ closed                                              │
                                    closed ──────────→ in_progress ◄──┘
```

### Allowed Transitions

| From | Allowed To |
|------|-----------|
| `new` | in_progress, pending, closed |
| `in_progress` | pending, resolved, closed |
| `pending` | in_progress, resolved, closed |
| `resolved` | closed, in_progress |
| `closed` | in_progress |

### Auto-behaviors

| Event | Action |
|-------|--------|
| Status → `resolved` | Auto-set `closed_at` |
| Status → `closed` | Auto-set `closed_at` |
| Status → `in_progress` (from closed) | Clear `closed_at` |

---

## 5. Case Properties & Types

### Case Types

| Type | Purpose |
|------|---------|
| `incident_response` | Active incident response |
| `investigation` | Research and investigation |
| `hunt` | Proactive threat hunting |
| `rfi` | Request for Information |

### Priority Levels

| Priority | Icon Color |
|----------|-----------|
| `critical` | Red |
| `high` | Orange |
| `medium` | Yellow |
| `low` | Blue |

### Case Fields

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `title` | VARCHAR(500) | Yes | — |
| `description` | TEXT | No | — |
| `case_type` | ENUM | Yes | `investigation` |
| `status` | ENUM | Yes | `new` |
| `priority` | ENUM | Yes | `medium` |
| `severity` | ENUM | Yes | `medium` |
| `tlp` | ENUM | Yes | `TLP:GREEN` |
| `owner_id` | UUID | Yes | Current user |
| `assignee_id` | UUID | No | — |
| `tags` | TEXT[] | No | `{}` |

### Denormalized Counters

| Counter | Description |
|---------|-------------|
| `linked_intel_count` | Number of linked intel items |
| `linked_ioc_count` | Number of linked IOCs |
| `linked_observable_count` | Number of linked observables |

---

## 6. Linked Items

Cases can link to multiple entity types:

| Item Type | Description |
|-----------|-------------|
| `intel` | Intel items from feeds |
| `ioc` | Indicators of Compromise |
| `technique` | MITRE ATT&CK techniques |
| `observable` | Generic observables |

Each linked item stores:
- `item_type`, `item_id`, `item_title`
- `item_metadata` (JSONB) — severity, risk score, etc.
- `added_by` (user UUID)
- `notes` (analyst notes)

Counter fields on the case are updated automatically when items are added/removed.

---

## 7. Activity Timeline

All case mutations generate activity entries in `case_activities`:

| Action | Detail |
|--------|--------|
| `created` | Case creation |
| `status_changed` | Status transition (from → to) |
| `comment` | Comment added |
| `item_added` | Item linked to case |
| `item_removed` | Item unlinked from case |
| `assigned` | Assignee changed |
| `priority_changed` | Priority updated |

Each activity records: `user_id`, `action`, `detail` (text), `metadata` (JSONB), `created_at`.

---

## 8. Comments

Comments are stored as case activities with `action = 'comment'`.

---

## 9. Bulk Operations

### Bulk Status Change
- Input: `case_ids[]`, `status`
- Validates each transition against the status machine
- **Invalid transitions are silently skipped** (no error, case unchanged)
- Creates activity entries for each successful change

### Bulk Assign
- Input: `case_ids[]`, `assignee_id`
- Updates assignee for all specified cases
- Assignable users: `role IN ('admin', 'analyst') AND is_active = TRUE`

### Bulk Delete
- Input: `case_ids[]`
- Cascade deletes case items and activities

### Duplicate Item Detection
- Adding the same item to a case returns HTTP 409 Conflict
- Uniqueness enforced by `(case_id, item_type, item_id)` constraint

---

## 10. Export

### JSON Export
Full case data including linked items, serialized as JSON array.

### CSV Export
Flat export with columns: ID, Title, Status, Priority, Type, Severity, TLP, Owner, Assignee, Tags, Created, Updated, Closed.

---

## 11. Database Schema

### `cases`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `gen_random_uuid()` |
| `title` | VARCHAR(500) | NOT NULL |
| `description` | TEXT | |
| `case_type` | case_type | ENUM, default `investigation` |
| `status` | case_status | ENUM, default `new` |
| `priority` | case_priority | ENUM, default `medium` |
| `severity` | severity_level | ENUM, default `medium` |
| `tlp` | tlp_level | ENUM, default `TLP:GREEN` |
| `owner_id` | UUID | FK to users, NOT NULL |
| `assignee_id` | UUID | FK to users, nullable |
| `tags` | TEXT[] | GIN indexed |
| `linked_intel_count` | INTEGER | default 0 |
| `linked_ioc_count` | INTEGER | default 0 |
| `linked_observable_count` | INTEGER | default 0 |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `closed_at` | TIMESTAMPTZ | nullable |

### `case_items`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK |
| `case_id` | UUID | FK to cases, CASCADE |
| `item_type` | VARCHAR(30) | intel, ioc, technique, observable |
| `item_id` | TEXT | |
| `item_title` | TEXT | |
| `item_metadata` | JSONB | default `{}` |
| `added_by` | UUID | FK to users |
| `notes` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

**Unique:** `(case_id, item_type, item_id)`

### `case_activities`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK |
| `case_id` | UUID | FK to cases, CASCADE |
| `user_id` | UUID | FK to users |
| `action` | VARCHAR(100) | |
| `detail` | TEXT | |
| `metadata` | JSONB | default `{}` |
| `created_at` | TIMESTAMPTZ | |

---

## 12. Constants & Thresholds Reference

### Status Configuration (Frontend)

| Status | Color | Icon | Next Allowed |
|--------|-------|------|-------------|
| `new` | blue | Clock | in_progress, pending, closed |
| `in_progress` | amber | RefreshCw | pending, resolved, closed |
| `pending` | purple | Pause | in_progress, resolved, closed |
| `resolved` | emerald | CheckCircle | closed, in_progress |
| `closed` | zinc | XCircle | in_progress |

### Priority Configuration (Frontend)

| Priority | Color | CSS Classes |
|----------|-------|----|
| `critical` | Red | `bg-red-500` indicator bar |
| `high` | Orange | `bg-orange-500` indicator bar |
| `medium` | Yellow | `bg-yellow-500` indicator bar |
| `low` | Blue | `bg-blue-500` indicator bar |

### Type Configuration (Frontend)

| Type | Icon | Label |
|------|------|-------|
| `incident_response` | AlertTriangle | Incident Response |
| `investigation` | Search | Investigation |
| `hunt` | Crosshair | Threat Hunt |
| `rfi` | HelpCircle | RFI |

### Page Size

Default page size: **20** cases per page.

---

## 13. Cases UI Layout

Layout of `cases/page.tsx`:

1. **Header** — Title + case count + Filters/Refresh/Export CSV/New Case buttons
2. **Stats Grid** (4 cards) — Total Cases, Open Cases, Critical Priority, Closed (7d)
3. **Filters Card** (collapsible) — Search + Status/Priority/Type/Severity/TLP/Tag filters + Apply/Clear
4. **Bulk Action Bar** (when items selected) — Count + Status change / Assign / Delete dropdowns + Apply/Cancel
5. **Case List** — Select-all checkbox + case cards:
   - Checkbox + priority color bar
   - Title + status/priority badges
   - Description preview
   - Type, severity, linked counts
   - Dates, owner/assignee, tags
   - Delete button + chevron for navigation
6. **Empty State** — New Case CTA
7. **Pagination**

### Create Case Modal
- Title (required), Description, Type, Priority, Severity, TLP
- Tags with Enter-to-add and remove badges
- Assignee dropdown
- Cancel/Create buttons

---

## 14. Future Enhancements

- Case templates for common incident types
- SLA tracking with priority-based timers
- Integration with ticketing systems (Jira, ServiceNow)
- Automated case creation from notification rules
- Case merging for duplicate incidents
- Evidence attachment support
- Playbook integration for case types
