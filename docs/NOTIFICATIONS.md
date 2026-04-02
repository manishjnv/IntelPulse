# IntelPulse — Notifications Module

> Complete technical reference for the Notifications system: rule engine, system rules, threshold/correlation/feed-error evaluation, severity intelligence, batch notifications, webhook delivery, and notification management UI.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [Database Schema](#3-database-schema)
4. [API Endpoints](#4-api-endpoints)
5. [System Rules](#5-system-rules)
6. [Rule Types & Evaluation](#6-rule-types--evaluation)
7. [Severity Intelligence](#7-severity-intelligence)
8. [Batch Notification Logic](#8-batch-notification-logic)
9. [Webhook Delivery](#9-webhook-delivery)
10. [Notification Categories](#10-notification-categories)
11. [Rule Evaluation Engine](#11-rule-evaluation-engine)
12. [Constants & Reference Tables](#12-constants--reference-tables)
13. [Notifications UI Layout](#13-notifications-ui-layout)
14. [Caching & Performance](#14-caching--performance)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  Intel Item Ingestion                         │
│  New items trigger notification rule evaluation               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Rule Evaluation Engine                            │
│  For each new item, evaluate ALL enabled rules                │
│  3 rule types: threshold │ feed_error │ correlation            │
│  Match → create notification + optional webhook               │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌──────────────────────┐  ┌───────────────────────────────────┐
│  notifications table  │  │  Webhook Delivery                  │
│  Stored in PostgreSQL │  │  POST to configured URL             │
│  With severity +      │  │  JSON payload with notification     │
│  metadata JSONB       │  │  data + retry logic                 │
└──────────────────────┘  └───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Notifications Page                    │
│  Notification list │ Stats panel │ Category filters            │
│  Mark read/unread │ Rule management │ Bulk actions             │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend notification routes | `api/app/routes/notifications.py` |
| Notification service | `api/app/services/notifications.py` |
| Webhook service | `api/app/services/webhook.py` |
| Database schema | `db/schema.sql` |
| Migration scripts | `scripts/migrate_notifications.sql` |
| Frontend notifications page | `ui/src/app/(app)/notifications/page.tsx` |

---

## 3. Database Schema

### `notification_rules` table

```sql
CREATE TABLE notification_rules (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    rule_type   VARCHAR(50) NOT NULL,
    conditions  JSONB NOT NULL DEFAULT '{}',
    is_enabled  BOOLEAN DEFAULT TRUE,
    is_system   BOOLEAN DEFAULT FALSE,
    created_by  INTEGER REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### `notifications` table

```sql
CREATE TABLE notifications (
    id          SERIAL PRIMARY KEY,
    rule_id     INTEGER REFERENCES notification_rules(id),
    title       VARCHAR(500) NOT NULL,
    message     TEXT,
    severity    VARCHAR(20) DEFAULT 'info',
    category    VARCHAR(50) DEFAULT 'alert',
    metadata    JSONB DEFAULT '{}',
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. API Endpoints

### Notification Management (12 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notifications` | List notifications (paginated, filtered) |
| `GET` | `/notifications/stats` | Notification statistics |
| `GET` | `/notifications/{id}` | Single notification detail |
| `PUT` | `/notifications/{id}/read` | Mark as read |
| `PUT` | `/notifications/read-all` | Mark all as read |
| `DELETE` | `/notifications/{id}` | Delete notification |
| `DELETE` | `/notifications/clear-all` | Clear all notifications |
| `GET` | `/notifications/rules` | List notification rules |
| `POST` | `/notifications/rules` | Create custom rule |
| `PUT` | `/notifications/rules/{id}` | Update rule |
| `DELETE` | `/notifications/rules/{id}` | Delete rule |
| `POST` | `/notifications/test-webhook` | Test webhook delivery |
| `POST` | `/notifications/rules/{id}/toggle` | Toggle rule enabled/disabled |
| `GET` | `/notifications/unread-count` | Quick count for notification bell badge |

### System Rule Delete Protection

`DELETE /notifications/rules/{id}` returns **403** with message `"System rules cannot be deleted"` if the rule has `is_system = true`. Service returns sentinel string `"system"`, route converts to 403.

### Query Parameters for `GET /notifications`

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `page_size` | int | Items per page |
| `category` | string | Filter by category |
| `severity` | string | Filter by severity |
| `is_read` | boolean | Filter read/unread |
| `sort_by` | string | Sort field |
| `sort_order` | string | asc / desc |

---

## 5. System Rules

4 pre-seeded system rules (cannot be deleted, can be toggled):

### 1. Critical / High Alert
- **Type:** `threshold`
- **Conditions:**
  ```json
  {
    "severity": ["critical", "high"],
    "risk_score_min": 70
  }
  ```
- **Effect:** Notification when critical/high severity items with risk ≥ 70 are ingested

### 2. CISA KEV Alert
- **Type:** `threshold`
- **Conditions:**
  ```json
  {
    "is_kev": true
  }
  ```
- **Effect:** Notification when any CISA KEV item is ingested

### 3. Feed Health Watchdog
- **Type:** `feed_error`
- **Conditions:**
  ```json
  {
    "stale_minutes": 120,
    "on_error": true
  }
  ```
- **Effect:** Notification when any feed reports an error or becomes stale (> 2 hours)

### 4. Risk Score Spike
- **Type:** `correlation`
- **Conditions:**
  ```json
  {
    "min_feeds": 2
  }
  ```
- **Effect:** Notification when a CVE appears in multiple feeds (cross-feed correlation)

### System Rule Seeding

On startup, the notification service calls `seed_system_rules()` which:
1. Checks for existing system rules
2. Creates missing system rules with default conditions
3. Does NOT overwrite user-modified conditions on existing system rules

---

## 6. Rule Types & Evaluation

### Threshold Rules

Evaluate individual intel items against multiple conditions:

| Condition Field | Type | Description |
|----------------|------|-------------|
| `severity` | string[] | Match if item severity in list |
| `risk_score_min` | float | Match if risk_score ≥ value |
| `risk_score_max` | float | Match if risk_score ≤ value |
| `is_kev` | boolean | Match if KEV status matches |
| `source_name` | string[] | Match if source in list |
| `has_cve` | boolean | Match if item has CVE references |
| `keywords` | string[] | Match if any keyword in title/description |

**Logic:** ALL conditions must match (AND logic).

### Feed Error Rules

Monitor feed health:

| Condition Field | Type | Description |
|----------------|------|-------------|
| `stale_minutes` | int | Minutes before a feed is considered stale |
| `on_error` | boolean | Trigger on any feed error |

**Evaluation:** Checks `feed_sync_state` table for error/stale feeds.

### Correlation Rules

Detect cross-feed intelligence:

| Condition Field | Type | Description |
|----------------|------|-------------|
| `min_feeds` | int | Minimum distinct feeds mentioning the same CVE |

**Evaluation:** Queries intel items grouped by CVE, filters where distinct `source_name` count ≥ `min_feeds`.

---

## 7. Severity Intelligence

Notification severity is **computed**, not static. The `_compute_notification_severity` function evaluates:

### Input Signals

| Signal | Weight |
|--------|--------|
| `risk_score` | Primary factor |
| `is_kev` | Automatic upgrade to at least "high" |
| `severity` | From intel item severity field |

### Severity Matrix

| Condition | Computed Severity |
|-----------|-------------------|
| `risk_score ≥ 90` OR `is_kev` + `severity = critical` | `critical` |
| `risk_score ≥ 70` OR `is_kev` | `high` |
| `risk_score ≥ 40` | `medium` |
| `risk_score ≥ 20` | `low` |
| `risk_score < 20` | `info` |

---

## 8. Batch Notification Logic

To prevent **alert fatigue**, the system batches related notifications:

### Trigger Condition
When a threshold rule matches multiple items in a single ingestion cycle, instead of creating N individual notifications, the system creates **one batch notification**.

### Batch Notification Fields
- `title` — "{Rule Name}: {count} items matched"
- `metadata` — Contains `_build_batch_metadata` output:
  - `item_count` — Number of matched items
  - `items` — Array of `{id, title, risk_score, severity}`
  - `highest_risk` — Maximum risk_score in batch
  - `severity_counts` — Breakdown by severity

### Batch Threshold
- If 1 item matches → Individual notification
- If 2+ items match → Batch notification with full metadata

---

## 9. Webhook Delivery

### Configuration
Webhook URL and secret are stored in rule conditions (`webhook_url`, `webhook_secret`).

### Payload Structure

```json
{
  "event": "notification",
  "timestamp": "2024-01-15T12:00:00Z",
  "data": {
    "title": "Critical Alert: CVE-2024-3094",
    "message": "...",
    "severity": "critical",
    "category": "alert",
    "entity_type": "intel_item",
    "entity_id": "uuid-here",
    "metadata": { ... }
  }
}
```

### HMAC Signing

If `webhook_secret` is configured, the payload is signed:

| Header | Value |
|--------|-------|
| `X-IntelPulse-Signature` | `hmac.new(secret, body, sha256).hexdigest()` |
| `Content-Type` | `application/json` |
| `User-Agent` | `IntelPulse/1.0` |

Body is serialized with `json.dumps(payload, sort_keys=True)` before signing.

### Delivery Constants

| Setting | Value |
|---------|-------|
| HTTP timeout | 10 seconds |
| Retry | None (fire-and-forget) |

### Channel Dispatcher

`deliver_to_channels_sync()` supports multiple channels:

| Channel | Behavior |
|---------|----------|
| `in_app` | Skipped (already stored in DB) |
| `webhook` | POST to `webhook_url` with HMAC signing |
| `slack` | Same POST as webhook (Slack-compatible payload) |

Used in both sync (`httpx.Client`) and async (`httpx.AsyncClient`) modes.

### Test Webhook
`POST /notifications/test-webhook` sends a test payload to verify URL configuration.

---

## 10. Notification Categories

| Category | Description | Rule Types |
|----------|-------------|------------|
| `alert` | Threat intelligence alerts | threshold |
| `feed_error` | Feed health issues | feed_error |
| `correlation` | Cross-feed intelligence | correlation |
| `system` | Platform system events | auto-generated |

---

## 11. Rule Evaluation Engine

### `evaluate_notification_rules(items)`

The main evaluation entry point, called after each ingestion batch:

1. Load all enabled rules from `notification_rules`
2. For each rule, dispatch to type-specific evaluator:
   - `threshold` → `_eval_threshold_rule(rule, items)`
   - `feed_error` → `_eval_feed_error_rule(rule)`
   - `correlation` → `_eval_correlation_rule(rule, items)`
3. Collect matched items per rule
4. Create notifications (individual or batch based on count)
5. Trigger webhook delivery if configured
6. Return count of notifications created

### `_eval_threshold_rule(rule, items)`

For each item in the batch:
1. Check severity against `conditions.severity` list
2. Check risk_score against min/max bounds
3. Check KEV status
4. Check source_name against allowed list
5. Check CVE presence
6. Check keywords in title/description (case-insensitive)
7. If ALL conditions pass → item matches

### `_eval_feed_error_rule(rule)`

1. Query `feed_sync_state` for feeds with status = 'error'
2. Query feeds where `last_success` is older than `stale_minutes`
3. Create notification for each problematic feed

### `_eval_correlation_rule(rule, items)`

1. Extract CVE IDs from the ingested items
2. For each CVE, count distinct `source_name` across all intel items
3. If distinct count ≥ `min_feeds` → create correlation notification
4. Include all contributing sources in notification metadata

---

## 12. Constants & Reference Tables

### Notification Severity Colors

| Severity | Color |
|----------|-------|
| `critical` | Red (#ef4444) |
| `high` | Orange (#f97316) |
| `medium` | Yellow (#eab308) |
| `low` | Green (#22c55e) |
| `info` | Blue (#3b82f6) |

### Category Icons

| Category | Icon |
|----------|------|
| `alert` | Bell |
| `feed_error` | AlertTriangle |
| `correlation` | GitMerge |
| `system` | Settings |

### Default Page Size

`page_size = 20`

---

## 13. Notifications UI Layout

Layout of `notifications/page.tsx`:

```
┌─────────────────────────────────────────────────┐
│  Notifications Header + Actions                  │
│  [Mark All Read] [Clear All] [Rules ⚙]           │
├─────────────────────────────────────────────────┤
│  Stats Bar                                       │
│  Total │ Unread │ Critical │ High │ Medium        │
├─────────────────────────────────────────────────┤
│  Category Filters                                │
│  [All] [Alert] [Feed Error] [Correlation] [System]│
├─────────────────────────────────────────────────┤
│  Severity Filter                                 │
│  [All] [Critical] [High] [Medium] [Low] [Info]   │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Notification Item                        │   │
│  │  [Severity badge] Title                   │   │
│  │  Category │ Rule name │ Timestamp          │   │
│  │  Message preview                          │   │
│  │  [Mark Read] [Delete]                     │   │
│  ├──────────────────────────────────────────┤   │
│  │  Notification Item                        │   │
│  │  ...                                      │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  [Pagination]                                    │
├─────────────────────────────────────────────────┤
│  Rules Management Panel (expandable)             │
│  System rules (toggle only) + Custom rules (CRUD)│
└─────────────────────────────────────────────────┘
```

### Notification Item Display

Each notification shows:
- **Severity badge** — Color-coded (see §12)
- **Title** — Notification title (truncated)
- **Category icon** — Category-specific icon
- **Rule name** — Which rule triggered it
- **Timestamp** — Relative time
- **Message** — Preview (expandable)
- **Batch metadata** — If batch notification, shows item count and breakdown
- **Actions** — Mark read/unread, delete

---

## 14. Caching & Performance

| Aspect | Strategy |
|--------|----------|
| Rule evaluation | Synchronous after ingestion batch |
| Notification query | Direct SQL, no cache |
| Stats | Computed on-demand |
| Webhook | Fire-and-forget async |

### Performance Considerations

- Rules are loaded once per evaluation cycle (not per item)
- Batch notifications reduce total notification count
- Correlation queries use database aggregation (not application-level loops)
- System rules are seeded once on startup, not re-evaluated for seeding

---

## 15. Future Enhancements

- Email notification delivery
- Slack / Teams integration
- SMS alerts for critical notifications
- Notification digest (daily/weekly summary)
- Custom webhook templates
- Rule testing sandbox (dry-run)
- Notification analytics dashboard
- Escalation policies (auto-escalate unread critical)
- Noise reduction with ML-based deduplication
- User-specific notification preferences
