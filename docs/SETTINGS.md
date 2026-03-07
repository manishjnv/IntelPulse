# IntelWatch — Settings Module

> Complete technical reference for the Settings system: platform configuration, API key management, user preferences, setup wizard, and settings persistence.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [Database Schema](#3-database-schema)
4. [API Endpoints](#4-api-endpoints)
5. [Settings Categories](#5-settings-categories)
6. [Default Settings](#6-default-settings)
7. [API Key Management](#7-api-key-management)
8. [Platform Setup Checklist](#8-platform-setup-checklist)
9. [Settings Section Components](#9-settings-section-components)
10. [Settings UI Layout](#10-settings-ui-layout)
11. [Security Considerations](#11-security-considerations)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  Settings Management                          │
│  Centralized configuration for platform behavior              │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│  user_settings table     │  │  Environment Variables           │
│  Key-value JSONB store   │  │  Secrets (API keys in .env)      │
│  Per-user preferences    │  │  Docker compose config           │
└─────────────────────────┘  └─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Settings Routes                      │
│  GET/PUT /settings │ GET /api-keys │ GET /platform-info       │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Settings Page                        │
│  6 section tabs │ Form controls │ API key management          │
│  Setup checklist │ Save/Reset actions                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend settings routes | `api/app/routes/settings.py` |
| Core config | `api/app/core/config.py` |
| Database schema | `db/schema.sql` |
| Frontend settings page | `ui/src/app/(app)/settings/page.tsx` |

---

## 3. Database Schema

### `user_settings` table

```sql
CREATE TABLE user_settings (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id),
    settings   JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);
```

Settings are stored as a JSONB blob per user, allowing flexible schema-less configuration.

---

## 4. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/settings` | Get current user settings (merged with defaults) |
| `PUT` | `/api/v1/settings` | Update user settings |
| `GET` | `/api/v1/settings/api-keys` | Get configured API key status (masked) |
| `GET` | `/api/v1/settings/platform-info` | Get platform version, setup status |

### `GET /settings` Response

Returns settings merged with DEFAULTS — any missing keys fall back to defaults:

```json
{
  "general": { ... },
  "security": { ... },
  "notifications": { ... },
  "appearance": { ... },
  "data_storage": { ... },
  "api_keys": { ... }
}
```

### `PUT /settings` Request

Accepts partial updates — only provided keys are updated:

```json
{
  "appearance": {
    "theme": "dark",
    "density": "comfortable"
  }
}
```

### `GET /settings/api-keys` Response

Returns API key **status** (configured yes/no, masked preview) — never full keys:

```json
{
  "abuseipdb": { "configured": true, "preview": "abc...xyz" },
  "virustotal": { "configured": false, "preview": null },
  ...
}
```

### `GET /settings/platform-info` Response

Returns platform metadata:

```json
{
  "version": "1.0.0",
  "environment": "production",
  "domain": "example.com",
  "domain_ui": "https://app.example.com",
  "domain_api": "https://api.example.com",
  "ai_enabled": true,
  "ai_model": "llama-3.3-70b-versatile",
  "total_feeds": 12,
  "active_feeds": 10
}
```

### Admin Endpoints

#### `POST /api/v1/admin/reindex`

Rebuild the OpenSearch index from PostgreSQL (admin only).

1. Calls `rebuild_index()` to recreate index with correct mapping
2. Batches through all `IntelItem` rows (500/batch)
3. Calls `bulk_index_items` per batch
4. Invalidates cache patterns: `iw:search:*`, `iw:dashboard:*`, `iw:status_bar*`
5. Audit-logged with `total_items`, `indexed`, `batch_errors`

**Response:** `{ rebuild: ..., total_items: N, indexed: N, batch_errors: N }`

#### `GET /api/v1/admin/setup/config`

Platform domain and deployment configuration (admin only).

#### `GET /api/v1/admin/setup/status`

Platform readiness checklist (admin only).

**Response:** `{ platform: config, checklist: [...], ready: bool }`

**Checklist items:** `database`, `redis`, `opensearch`, `auth`, `domain`, `feeds_free`, `feeds_api`, `ai`

---

## 5. Settings Categories

Settings organized into 4 categories:

### General Settings

| Key | Default | Type | Description |
|-----|---------|------|-------------|
| `platform_name` | `"IntelWatch"` | string | Platform display name |
| `timezone` | `"UTC"` | string | Default timezone |
| `default_risk_threshold` | `70` | int | Risk score threshold for alerts |
| `auto_refresh` | `true` | bool | Auto-refresh dashboard data |

### Security Settings

| Key | Default | Type | Description |
|-----|---------|------|-------------|
| `api_auth_required` | `true` | bool | Require auth for API endpoints |
| `session_timeout` | `"4 hours"` | string | Session expiration |
| `rate_limit` | `100` | int | API rate limit per window |
| `pii_redaction` | `true` | bool | Redact PII in exports/logs |

### Appearance Settings

| Key | Default | Type | Description |
|-----|---------|------|-------------|
| `theme` | `"dark"` | string | UI theme (dark/light/system) |
| `compact_mode` | `false` | bool | Compact table/card density |
| `show_risk_scores` | `true` | bool | Show risk scores in UI |

### Data & Storage Settings

| Key | Default | Type | Description |
|-----|---------|------|-------------|
| `data_retention` | `"never"` | string | Intel item retention policy |
| `deduplication` | `true` | bool | Dedupe intel items on ingest |
| `opensearch_sync` | `true` | bool | Sync items to OpenSearch |

---

## 6. Default Settings

The backend maintains a `DEFAULTS` dictionary in `routes/settings.py`:

```python
DEFAULTS = {
    "platform_name": "IntelWatch",
    "timezone": "UTC",
    "default_risk_threshold": 70,
    "auto_refresh": True,
    "api_auth_required": True,
    "session_timeout": "4 hours",
    "rate_limit": 100,
    "pii_redaction": True,
    "theme": "dark",
    "compact_mode": False,
    "show_risk_scores": True,
    "data_retention": "never",
    "deduplication": True,
    "opensearch_sync": True,
}
```

15 settings total. When fetching settings:

1. Load user's JSONB settings from `user_settings`
2. Deep-merge with `DEFAULTS`
3. User values override defaults
4. Missing keys automatically use default values

This ensures forward compatibility — new settings added in code are immediately available with sensible defaults without requiring database migrations.

---

## 7. API Key Management

6 external API keys tracked:

| Service | Key Name | Used By |
|---------|----------|---------|
| AbuseIPDB | `abuseipdb_api_key` | IP reputation lookups |
| AlienVault OTX | `otx_api_key` | Threat intelligence feed |
| VirusTotal | `virustotal_api_key` | Multi-type lookups |
| Shodan | `shodan_api_key` | Network intelligence |
| NVD | `nvd_api_key` | Vulnerability data |
| AI/LLM | `ai_api_key` | AI summaries and analysis |

### Key Storage

API keys are stored as **environment variables** (not in the database) for security:
- Set in `.env` file or Docker environment
- Read via `api/app/core/config.py` using Pydantic Settings
- The `/api-keys` endpoint only shows configuration status, never the actual keys

### Key Status Display

For each key, the UI shows:
- **Configured:** Green badge if the environment variable is set
- **Not Configured:** Red badge if missing
- **Preview:** Masked via `_mask()` function:

| Key Length | Masking |
|------------|--------|
| `<= 8` chars | `"••••"` + last 2 chars |
| `> 8` chars | `"••••••••••"` + last 4 chars |
| Empty/null | `"Not configured"` |

---

## 8. Platform Setup Checklist

The `GET /settings/platform-info` endpoint returns an 8-item setup checklist:

| Check | Validates |
|-------|-----------|
| Database Connected | PostgreSQL connection alive |
| OpenSearch Connected | OpenSearch cluster reachable |
| Redis Connected | Redis ping succeeds |
| Worker Running | RQ worker is processing |
| Scheduler Running | APScheduler is active |
| Feeds Configured | At least 1 feed has synced |
| API Keys Set | At least 1 external API key configured |
| AI Service Available | AI/LLM API key configured and valid |

Each check returns `true`/`false`. The UI displays these as a visual checklist with green/red indicators.

---

## 9. Settings Section Components

The frontend settings page uses 6 dedicated section sub-components:

### 1. General Section
- Platform name input
- Timezone selector
- Date format picker
- Items per page slider

### 2. Security Section
- Session timeout input
- 2FA toggle
- Password policy configuration
- Login attempt limit

### 3. Notifications Section
- Email notification toggle
- Webhook URL input + test button
- Notification retention slider
- Links to notification rules management

### 4. Appearance Section
- Theme selector (light/dark/system)
- Density selector (comfortable/compact)
- Sidebar collapsed default toggle

### 5. Data & Storage Section
- Data retention slider
- Auto-enrich toggle
- Max export rows input
- OpenSearch enable/disable

### 6. API Keys Section
- Status cards for each API key
- Configuration instructions
- Key health check buttons
- Links to provider documentation

---

## 10. Settings UI Layout

Layout of `settings/page.tsx`:

```
┌─────────────────────────────────────────────────┐
│  Settings Header                                 │
├─────────────────────────────────────────────────┤
│  Setup Checklist (collapsible)                   │
│  [✓ DB] [✓ OpenSearch] [✓ Redis] [✓ Worker]     │
│  [✓ Scheduler] [✓ Feeds] [✗ API Keys] [✓ AI]    │
├─────────┬───────────────────────────────────────┤
│  Section │  Section Content                      │
│  Nav     │                                       │
│          │  (renders selected section component) │
│  General │  ┌────────────────────────────────┐  │
│  Security│  │  Form fields for the active     │  │
│  Notifs  │  │  section, with labels, inputs,  │  │
│  Appear  │  │  toggles, sliders, etc.         │  │
│  Data    │  │                                  │  │
│  API Keys│  │  [Save Changes] [Reset Defaults] │  │
│          │  └────────────────────────────────┘  │
└─────────┴───────────────────────────────────────┘
```

### Navigation
- Left sidebar with section links
- Active section highlighted
- Clicking a section loads its sub-component
- Unsaved changes trigger a warning on navigation

### Save Behavior
- "Save Changes" sends `PUT /settings` with only modified fields
- "Reset Defaults" restores all settings to DEFAULTS
- Toast notification on save success/failure
- Optimistic UI update with rollback on error

---

## 11. Security Considerations

### API Key Protection
- Keys stored in environment variables, not database
- Never exposed via API responses (only masked preview)
- Keys validated at startup (not at request-time)
- Rotation requires environment variable update + restart

### Settings Access Control
- Settings endpoints require authentication
- Each user has their own settings (user_id scoped)
- Admin users can view platform-level settings
- API key status visible to all authenticated users

### Input Validation
- All settings validated against expected types
- Numeric settings have min/max bounds
- String settings have length limits
- JSONB storage prevents SQL injection

---

## 12. Future Enhancements

- LDAP/SAML SSO configuration
- Custom branding (logo, colors)
- Backup/restore settings
- Settings audit log
- Multi-tenant configuration
- Rate limit configuration per user
- Custom field definitions
- Plugin/extension settings
- Import/export settings profiles
- Settings change notifications
