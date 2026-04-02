# IntelPulse — Feed Status Module

> Complete technical reference for the Feed Status panel: feed health monitoring, sync state tracking, manual triggers, pipeline status, and status indicators.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [Database Schema](#3-database-schema)
4. [API Endpoints](#4-api-endpoints)
5. [Feed Sync State](#5-feed-sync-state)
6. [Status Definitions](#6-status-definitions)
7. [Stale Detection](#7-stale-detection)
8. [Manual Feed Triggers](#8-manual-feed-triggers)
9. [Pipeline Status Banner](#9-pipeline-status-banner)
10. [Constants & Reference Tables](#10-constants--reference-tables)
11. [Feed Status UI Layout](#11-feed-status-ui-layout)
12. [Scheduler Integration](#12-scheduler-integration)
13. [Future Enhancements](#13-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│           Feed Sync State Tracking                            │
│  Each feed has a row in feed_sync_state                       │
│  Updated after every ingestion cycle                          │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│  Worker/Scheduler        │  │  FastAPI Routes                  │
│  ingest_feed → updates   │  │  GET /feeds/status               │
│  sync state on each run  │  │  POST /feeds/{name}/trigger      │
│  Self-healing watchdog   │  │  POST /feeds/trigger-all          │
└─────────────────────────┘  └─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Feed Status Page                     │
│  2 tabs (Intel / News) │ Status cards │ Pipeline banner       │
│  Manual trigger buttons │ timeAgo display                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend feed routes | `api/app/routes/intel.py` (feeds section) |
| Backend health routes | `api/app/routes/health.py` |
| Worker ingestion | `worker/tasks.py` |
| Scheduler configuration | `worker/scheduler.py` |
| Database schema | `db/schema.sql` |
| Frontend Feed Status page | `ui/src/app/(app)/feeds/page.tsx` |
| Frontend FeedStatusPanel | `ui/src/components/FeedStatusPanel.tsx` |

---

## 3. Database Schema

### `feed_sync_state` table

```sql
CREATE TABLE feed_sync_state (
    id             SERIAL PRIMARY KEY,
    feed_name      VARCHAR(100) NOT NULL UNIQUE,
    last_sync      TIMESTAMPTZ,
    last_success   TIMESTAMPTZ,
    last_error     TEXT,
    items_synced   INTEGER DEFAULT 0,
    status         VARCHAR(20) DEFAULT 'idle',
    error_count    INTEGER DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);
```

### Fields

| Field | Description |
|-------|-------------|
| `feed_name` | Unique feed identifier (e.g., "nvd", "cisa_kev") |
| `last_sync` | Timestamp of most recent sync attempt |
| `last_success` | Timestamp of last successful sync |
| `last_error` | Error message from last failed sync |
| `items_synced` | Total items synced in last run |
| `status` | Current feed status (see §6) |
| `error_count` | Consecutive error count |

---

## 4. API Endpoints

### `GET /api/v1/feeds/status`

Returns array of all feed sync states.

**Response:** Array of feed status objects with all `feed_sync_state` fields plus computed fields:
- `is_stale` — Boolean indicating if feed is past its expected interval
- `next_expected` — Estimated next sync time

### `POST /api/v1/feeds/{name}/trigger`

Manually trigger ingestion for a specific feed.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string (path) | Feed name identifier |

**Effect:** Enqueues the feed's ingestion task immediately.

### `POST /api/v1/feeds/trigger-all`

Trigger ingestion for all feeds simultaneously.

**Effect:** Enqueues all 12 intel feed + news feed ingestion tasks.

---

## 5. Feed Sync State

The ingestion pipeline updates `feed_sync_state` at key points:

### During Ingestion

1. **Start:** Status → `syncing`, update `last_sync`
2. **Success:** Status → `idle`, update `last_success`, set `items_synced`, reset `error_count` to 0
3. **Error:** Status → `error`, set `last_error` message, increment `error_count`

### Feed List

12 Intel Feeds tracked:

| Feed Name | Schedule |
|-----------|----------|
| `nvd` | Every 15 min |
| `cisa_kev` | Every 60 min |
| `abuse_ipdb` | Every 60 min |
| `otx` | Every 30 min |
| `virustotal` | Every 60 min |
| `github_advisories` | Every 30 min |
| `epss` | Every 24 hours |
| `feodo_tracker` | Every 60 min |
| `urlhaus` | Every 30 min |
| `shodan` | Every 60 min |
| `mitre_cve` | Every 60 min |
| `circl_cve` | Every 60 min |

Plus news feeds tracked separately.

---

## 6. Status Definitions

7 possible feed statuses with visual indicators:

| Status | Color | Icon | Description |
|--------|-------|------|-------------|
| `idle` | Green | ✓ | Feed healthy, waiting for next cycle |
| `syncing` | Blue | ⟳ | Currently ingesting data |
| `error` | Red | ✗ | Last sync failed |
| `stale` | Orange | ⚠ | No sync beyond expected interval |
| `disabled` | Gray | ○ | Feed manually disabled |
| `initializing` | Purple | … | First-time setup in progress |
| `rate_limited` | Yellow | ⏱ | API rate limit hit, backing off |

### STATUS_META (Frontend)

Frontend maps each status to a color, icon, and label for consistent rendering across the UI:

```typescript
const STATUS_META = {
  idle:         { color: 'green',  icon: CheckCircle,  label: 'Healthy' },
  syncing:      { color: 'blue',   icon: RefreshCw,    label: 'Syncing' },
  error:        { color: 'red',    icon: XCircle,      label: 'Error' },
  stale:        { color: 'orange', icon: AlertTriangle, label: 'Stale' },
  disabled:     { color: 'gray',   icon: MinusCircle,  label: 'Disabled' },
  initializing: { color: 'purple', icon: Loader,       label: 'Init' },
  rate_limited: { color: 'yellow', icon: Clock,        label: 'Rate Limited' }
};
```

---

## 7. Stale Detection

A feed is considered **stale** when:

```
current_time - last_success > expected_interval × stale_multiplier
```

The default `stale_multiplier` is **2x** the expected interval. For example:
- NVD (15 min interval) → stale after 30 min without success
- CISA KEV (60 min interval) → stale after 120 min without success

Stale detection is computed server-side in the `/feeds/status` response and additionally evaluated by the **Feed Health Watchdog** notification rule.

---

## 8. Manual Feed Triggers

Both trigger endpoints are in `admin.py` and require admin role.

### Single Feed Trigger

`POST /api/v1/admin/feeds/{feed_name}/trigger`

- **Auth:** Admin only
- **Queue:** `high` priority
- **Timeout:** 300 seconds
- **Task:** `worker.tasks.ingest_feed`
- **Audit:** Logged with `action=trigger_feed`

**Valid feed names:** `nvd`, `cisa_kev`, `urlhaus`, `abuseipdb`, `otx`, `virustotal`, `shodan`

Invalid names return 400 with the valid list.

### Trigger All

`POST /api/v1/admin/feeds/trigger-all`

- **Auth:** Admin only
- **Queue:** `default` priority
- **Timeout:** 600 seconds
- **Task:** `worker.tasks.ingest_all_feeds`
- **Audit:** Logged with `action=trigger_all_feeds`

### Queue Summary

| Endpoint | Queue | `job_timeout` |
|----------|-------|---------------|
| Single feed trigger | `high` | 300s |
| Trigger all | `default` | 600s |

**Note:** No deduplication guard exists — rapid repeated calls will queue duplicate jobs.

---

## 9. Pipeline Status Banner

A banner at the top of the Feed Status page showing overall pipeline health:

| Metric | Description |
|--------|-------------|
| Total Feeds | Count of all tracked feeds |
| Healthy | Feeds with status `idle` |
| Syncing | Feeds currently ingesting |
| Errors | Feeds with `error` status |
| Stale | Feeds past expected interval |

Colors:
- All healthy → Green banner
- Any stale → Yellow banner
- Any errors → Red banner

---

## 10. Constants & Reference Tables

### `timeAgo` Helper

Frontend utility that converts timestamps to human-readable relative time:

| Range | Display |
|-------|---------|
| < 60s | "just now" |
| < 60m | "Nm ago" |
| < 24h | "Nh ago" |
| < 7d | "Nd ago" |
| ≥ 7d | Date string |

### Stale Threshold

Frontend stale indicator: **120 seconds** since last update triggers stale badge in the status bar.

### Feed Categories (Tab System)

| Tab | Feeds |
|-----|-------|
| Intel Feeds | NVD, CISA KEV, AbuseIPDB, OTX, VirusTotal, GitHub Advisories, EPSS, Feodo Tracker, URLhaus, Shodan, MITRE CVE, CIRCL CVE |
| News Feeds | Cyber news aggregation feeds |

---

## 11. Feed Status UI Layout

Layout of `feeds/page.tsx`:

```
┌─────────────────────────────────────────────────┐
│  Feed Status Header + "Trigger All" Button       │
├─────────────────────────────────────────────────┤
│  Pipeline Status Banner                          │
│  [Healthy: N] [Syncing: N] [Errors: N] [Stale: N]│
├─────────────────────────────────────────────────┤
│  Tab Bar: Intel Feeds │ News Feeds               │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │  Feed Card: NVD                          │    │
│  │  Status badge │ Last sync │ Items synced  │    │
│  │  Error message (if any) │ [Trigger]       │    │
│  ├─────────────────────────────────────────┤    │
│  │  Feed Card: CISA KEV                     │    │
│  │  ...                                     │    │
│  ├─────────────────────────────────────────┤    │
│  │  Feed Card: ...                          │    │
│  │  (repeated for each feed)                │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
└─────────────────────────────────────────────────┘
```

Each feed card displays:
- Feed name and icon
- Status badge (color-coded per §6)
- Last sync time (relative via `timeAgo`)
- Last success time
- Items synced in last run
- Error message (if status is `error`)
- Consecutive error count
- Manual trigger button

---

## 12. Scheduler Integration

The scheduler (`worker/scheduler.py`) manages all feed intervals:

### Self-Healing Watchdog

A watchdog job runs every 5 minutes:
- Checks all feed states
- If a feed has `error_count ≥ 3`, attempts re-trigger with exponential backoff
- If a feed is stale beyond 3× expected interval, logs a warning
- Watchdog itself has a max retry limit to prevent infinite loops

### APScheduler Configuration

All 26 scheduled jobs are registered in `scheduler.py`:
- Feed ingestion jobs use `IntervalTrigger`
- Each job has a `max_instances=1` to prevent overlap
- Jobs have `misfire_grace_time` to handle delayed execution
- Coalesce is enabled to combine missed runs

---

## 13. Future Enhancements

- Feed health history graph (uptime visualization)
- Feed performance metrics (ingestion duration, throughput)
- Feed configuration UI (enable/disable, change intervals)
- Custom feed connector builder
- Feed dependency tracking
- Alert routing for persistent feed failures
- Feed output quality scoring
- Historical sync state timeline
