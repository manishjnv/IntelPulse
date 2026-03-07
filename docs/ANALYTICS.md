# IntelWatch — Analytics Module

> Complete technical reference for the Analytics dashboard: stat cards, trend charts, distribution breakdowns, and composite visualizations.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [Data Sources](#3-data-sources)
4. [Stat Cards](#4-stat-cards)
5. [Ingestion Trend Chart](#5-ingestion-trend-chart)
6. [Exploit & Vulnerability Posture](#6-exploit--vulnerability-posture)
7. [Severity & Category Charts](#7-severity--category-charts)
8. [Top CVEs Section](#8-top-cves-section)
9. [Distribution Grids](#9-distribution-grids)
10. [UI Layout](#10-ui-layout)
11. [Caching & Performance](#11-caching--performance)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│         Analytics Page — Read-Only Aggregation View          │
│  Consumes existing dashboard + intel stats endpoints          │
│  No dedicated backend — reuses Dashboard & Intel APIs         │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│  GET /dashboard          │  │  GET /intel/stats                │
│  KPIs, severity dist,    │  │  Category & field breakdowns     │
│  ingestion trends,       │  │  Top CVEs, EPSS data             │
│  materialized views      │  │  Source/tag/product counts        │
└─────────────────────────┘  └─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Analytics Page                       │
│  8 StatCards │ Ingestion trend │ Exploit posture               │
│  Severity donut │ Category bar │ Top CVEs                      │
│  3-column distribution grids (9 charts total)                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend dashboard route | `api/app/routes/dashboard.py` |
| Backend intel routes | `api/app/routes/intel.py` |
| Database service (views) | `api/app/services/database.py` |
| Frontend analytics page | `ui/src/app/(app)/analytics/page.tsx` |
| DonutChart component | `ui/src/components/DonutChart.tsx` |
| HorizontalBarChart | `ui/src/components/HorizontalBarChart.tsx` |

---

## 3. Data Sources

The Analytics page does **not** have its own dedicated API. It reuses:

| Endpoint | Data Used |
|----------|-----------|
| `GET /api/v1/dashboard` | KPIs, severity distribution, ingestion trends, top risks |
| `GET /api/v1/intel/stats` | Category breakdowns, field distributions, top CVEs |

Both endpoints benefit from materialized views:
- `mv_severity_distribution` — Pre-computed severity counts
- `mv_top_risks` — Pre-computed highest-risk items

---

## 4. Stat Cards

8 KPI cards arranged in 2 rows of 4:

### Row 1

| Card | Metric | Source |
|------|--------|--------|
| Total Intel Items | Count of all items | Dashboard KPI |
| Critical Items | Severity = critical | Dashboard KPI |
| High Risk (≥80) | Items with risk_score ≥ 80 | Dashboard KPI |
| KEV Items | CISA KEV flagged items | Dashboard KPI |

### Row 2

| Card | Metric | Source |
|------|--------|--------|
| Active Sources | Distinct source names | Intel stats |
| CVE References | Total CVE mentions | Intel stats |
| Active IOCs | Total IOCs in database | Dashboard KPI |
| Avg Risk Score | Mean risk_score | Dashboard KPI |

Each card shows:
- Metric value (large font)
- Label description
- Trend indicator (up/down/flat with color coding)

---

## 5. Ingestion Trend Chart

- **Type:** Area chart (Recharts `AreaChart`)
- **Data:** Daily ingestion counts over last 30 days
- **Source:** Dashboard endpoint `ingestion_trend` field
- **Features:**
  - Gradient fill under the line
  - Tooltip with date and count
  - Responsive sizing

---

## 6. Exploit & Vulnerability Posture

A panel showing 5 key exploit/vulnerability metrics:

| Metric | Description |
|--------|-------------|
| KEV Percentage | % of items in CISA KEV |
| EPSS > 0.5 | Items with high exploit probability |
| Active Exploits | Items with known active exploitation |
| Critical CVSS | Items with CVSS ≥ 9.0 |
| Patch Available | Items where a patch/fix is available |

Each metric displayed as a progress bar with percentage and absolute count.

---

## 7. Severity & Category Charts

### Severity Distribution (Donut)
- **Type:** Donut chart (Recharts `PieChart`)
- **Segments:** Critical, High, Medium, Low, Info
- **Colors:** Red (#ef4444), Orange (#f97316), Yellow (#eab308), Green (#22c55e), Blue (#3b82f6)
- **Center label:** Total count
- **Source:** `mv_severity_distribution` materialized view

### Category Distribution (Bar)
- **Type:** Horizontal bar chart
- **Categories:** Dynamic based on feed types in data
- **Sorted:** Descending by count
- **Source:** Intel stats endpoint

---

## 8. Top CVEs Section

- Displays top CVEs by risk score
- Each CVE shows: ID, risk score, severity badge, title (truncated)
- Clickable — navigates to Intel Item detail
- Source: Dashboard `top_risks` field

---

## 9. Distribution Grids

Three rows of 3-column grids showing distribution breakdowns:

### Row 1

| Chart | Type | Data |
|-------|------|------|
| Geographic Distribution | Horizontal bar | Countries from intel item metadata |
| Industry Targets | Horizontal bar | Targeted industries |
| ATT&CK Techniques | Horizontal bar | Top mapped techniques |

### Row 2

| Chart | Type | Data |
|-------|------|------|
| Threat Actors | Horizontal bar | Actor attribution from items |
| Ransomware Families | Horizontal bar | Ransomware family names |
| Malware Families | Horizontal bar | Malware classifications |

### Row 3

| Chart | Type | Data |
|-------|------|------|
| Intelligence Sources | Horizontal bar | Feed source names |
| Popular Tags | Horizontal bar | Most common tags |
| Asset Types | Horizontal bar | Targeted asset categories |

Each chart:
- Shows top N entries
- Color-coded bars
- Count labels on bars
- Sorted descending by count

---

## 10. UI Layout

Full layout of `analytics/page.tsx` (~580 lines):

```
┌─────────────────────────────────────────────────┐
│  Analytics Header                                │
├─────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │ Stat │ │ Stat │ │ Stat │ │ Stat │  Row 1     │
│  └──────┘ └──────┘ └──────┘ └──────┘           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │ Stat │ │ Stat │ │ Stat │ │ Stat │  Row 2     │
│  └──────┘ └──────┘ └──────┘ └──────┘           │
├─────────────────────────────────────────────────┤
│  Ingestion Trend (area chart, full width)        │
├─────────────────────────────────────────────────┤
│  Exploit & Vulnerability Posture                 │
├────────────────────┬────────────────────────────┤
│  Severity Donut    │  Category Bars              │
├────────────────────┴────────────────────────────┤
│  Top CVEs                                        │
├─────────────┬─────────────┬─────────────────────┤
│  Geo Dist   │  Industries │  ATT&CK Techniques  │
├─────────────┼─────────────┼─────────────────────┤
│  Actors     │  Ransomware │  Malware            │
├─────────────┼─────────────┼─────────────────────┤
│  Sources    │  Tags       │  Asset Types        │
└─────────────┴─────────────┴─────────────────────┘
```

---

## 11. Caching & Performance

| Aspect | Strategy |
|--------|----------|
| Dashboard data | Cached 60s in Redis |
| Intel stats | Cached 300s in Redis |
| Materialized views | Refreshed every 5 min by scheduler |
| Frontend | Single fetch on page load, no polling |
| Chart rendering | Recharts with lazy loading |

The Analytics page is read-only with no write operations, making it safe to cache aggressively.

---

## 12. Future Enhancements

- Custom date range selection
- Export analytics as PDF report
- Trend comparison (week-over-week, month-over-month)
- Custom metric builder
- Anomaly detection alerts
- Real-time streaming updates
- Drill-down from charts to filtered intel views
- Scheduled analytics email digests
