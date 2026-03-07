# IntelWatch — Geo View Module

> Complete technical reference for the Geo View: geographic intelligence visualization, region-based browsing, drill-down panels, and IOC geolocation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [Data Sources](#3-data-sources)
4. [Region Color Mapping](#4-region-color-mapping)
5. [Tab System](#5-tab-system)
6. [Drill-Down Panel](#6-drill-down-panel)
7. [IOC Geo Data](#7-ioc-geo-data)
8. [Constants & Reference Tables](#8-constants--reference-tables)
9. [UI Layout](#9-ui-layout)
10. [Export](#10-export)
11. [Future Enhancements](#11-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│              Geo View — Geographic Intelligence               │
│  5-tab view of geographic, network, and industry data         │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│  GET /intel/stats        │  │  GET /iocs (with enrichment)     │
│  Country, industry,      │  │  IPinfo geolocation data         │
│  network distributions   │  │  ASN, org, coordinates           │
└─────────────────────────┘  └─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Geo View Page                        │
│  5 tabs │ Sortable tables │ Drill-down panel                  │
│  Region colors │ Continent emoji │ Excel export               │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend intel routes | `api/app/routes/intel.py` |
| Enrichment service (IPinfo) | `api/app/services/enrichment.py` |
| Frontend Geo View page | `ui/src/app/(app)/geo/page.tsx` |

---

## 3. Data Sources

| Data | Source | Description |
|------|--------|-------------|
| Country distribution | `GET /intel/stats` | Country codes from intel items |
| Continent mapping | Frontend lookup | Country → continent mapping |
| Network/ASN data | IOC enrichment (IPinfo) | ASN, organization from IP IOCs |
| Industry targets | `GET /intel/stats` | Industries mentioned in intel items |
| Intel item geo | Intel item metadata | `target_countries` field |

---

## 4. Region Color Mapping

15 named region colors for chart visualization:

| Region / Index | Color |
|----------------|-------|
| 1 | Blue (#3b82f6) |
| 2 | Red (#ef4444) |
| 3 | Green (#22c55e) |
| 4 | Purple (#a855f7) |
| 5 | Orange (#f97316) |
| 6 | Cyan (#06b6d4) |
| 7 | Pink (#ec4899) |
| 8 | Yellow (#eab308) |
| 9 | Teal (#14b8a6) |
| 10 | Indigo (#6366f1) |
| 11 | Rose (#f43f5e) |
| 12 | Emerald (#10b981) |
| 13 | Violet (#8b5cf6) |
| 14 | Amber (#f59e0b) |
| 15 | Sky (#0ea5e9) |

---

## 5. Tab System

5 tabs for different geographic dimensions:

### Tab 1: Countries
- **Data:** Country code → count mapping
- **Display:** Sorted table with country name, flag emoji, count, percentage
- **Drill-down:** Click to see intel items targeting that country
- **Chart:** Horizontal bar chart of top countries

### Tab 2: Continents
- **Data:** Aggregated from country → continent mapping
- **Continent emojis:**

| Continent | Emoji |
|-----------|-------|
| North America | 🌎 |
| South America | 🌎 |
| Europe | 🌍 |
| Africa | 🌍 |
| Asia | 🌏 |
| Oceania | 🌏 |
| Antarctica | 🧊 |

- **Display:** Continent cards with count, percentage, and top countries within each

### Tab 3: Networks
- **Data:** ASN and organization data from IP IOC enrichment
- **Display:** Network/ASN table with org name, ASN number, IP count, associated countries

### Tab 4: Industries
- **Data:** Targeted industries from intel item metadata
- **Display:** Industry table with name, item count, severity breakdown
- **Chart:** Horizontal bar chart of top targeted industries

### Tab 5: Intel Geo
- **Data:** Intel items with geographic targeting data
- **Display:** Table of intel items grouped by target geography
- **Columns:** Title, severity, target countries, risk score, published date

---

## 6. Drill-Down Panel

Clicking any row in the geo tables opens a drill-down panel:

### Contents
- **Header:** Selected entity name (country, continent, network, industry)
- **Stats:** Total items, severity breakdown, avg risk score
- **Intel Items List:** Paginated list of related intel items
  - Title, severity badge, risk score, published date
  - Click navigates to intel item detail
- **Export Button:** Download filtered items as Excel

### Behavior
- Panel slides in from the right
- Overlay backdrop with click-to-close
- Persistent within tab navigation
- Closes on tab change

---

## 7. IOC Geo Data

Geographic data for IOCs comes from the IPinfo enrichment pipeline:

| Field | Description |
|-------|-------------|
| `country` | Two-letter country code |
| `region` | State/province |
| `city` | City name |
| `latitude` | Decimal latitude |
| `longitude` | Decimal longitude |
| `asn` | Autonomous System Number |
| `org` | Organization name |

This data is used in the Networks tab and overlaid on the Countries tab for IOC-specific geographic distribution.

---

## 8. Constants & Reference Tables

### Country to Continent Mapping
Frontend maintains a lookup table mapping ~250 ISO country codes to their continent.

### Region Colors Array
`REGION_COLORS` — 15 predefined colors for chart segments (see §4).

### Continent Emojis
`CONTINENT_EMOJI` — 7 emoji mappings (see §5 Tab 2).

### Default Sort
- Countries: count descending
- Continents: count descending
- Networks: IP count descending
- Industries: item count descending
- Intel Geo: risk score descending

---

## 9. UI Layout

Full layout of `geo/page.tsx` (~1050 lines):

```
┌─────────────────────────────────────────────────┐
│  Geo View Header — "Geographic Intelligence"     │
├─────────────────────────────────────────────────┤
│  Tab Bar: Countries│Continents│Networks│         │
│           Industries│Intel Geo                    │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────┬─────────────────────┐   │
│  │  Chart / Map        │  Summary Stats      │   │
│  │  (varies by tab)    │                     │   │
│  └────────────────────┴─────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Data Table (sortable columns)            │   │
│  │  Row 1: Entity │ Count │ % │ Severity     │   │
│  │  Row 2: ...                               │   │
│  │  Row N: ...                               │   │
│  │  [Pagination]                             │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Drill-Down Panel (slide-over)            │   │
│  │  (opens on row click)                     │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## 10. Export

### Drill-Down Export
- **Format:** Excel (.xlsx)
- **Content:** Filtered intel items for the selected geographic entity
- **Columns:** Title, severity, risk score, source, published date, target countries
- **Trigger:** Export button within the drill-down panel

---

## 11. Future Enhancements

- Interactive world map with choropleth visualization
- Real-time threat heat map
- IP geolocation map with clustering
- Country risk score aggregation
- Threat corridor visualization (source → target paths)
- Time-based geographic trend analysis
- STIX geographic indicator export
- Network topology visualization
