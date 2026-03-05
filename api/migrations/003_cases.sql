-- =============================================
-- Case / Incident Management Tables
-- =============================================

-- Enum types
DO $$ BEGIN
    CREATE TYPE case_type AS ENUM ('incident_response', 'investigation', 'hunt', 'rfi');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE case_status AS ENUM ('new', 'in_progress', 'pending', 'resolved', 'closed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE case_priority AS ENUM ('critical', 'high', 'medium', 'low');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ─── Cases ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    case_type       case_type NOT NULL DEFAULT 'investigation',
    status          case_status NOT NULL DEFAULT 'new',
    priority        case_priority NOT NULL DEFAULT 'medium',
    severity        severity_level NOT NULL DEFAULT 'medium',
    tlp             tlp_level NOT NULL DEFAULT 'TLP:GREEN',
    owner_id        UUID NOT NULL REFERENCES users(id),
    assignee_id     UUID REFERENCES users(id),
    tags            TEXT[] NOT NULL DEFAULT '{}',

    -- Counters (denormalized for list performance)
    linked_intel_count      INTEGER NOT NULL DEFAULT 0,
    linked_ioc_count        INTEGER NOT NULL DEFAULT 0,
    linked_observable_count INTEGER NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cases_status    ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_priority  ON cases(priority);
CREATE INDEX IF NOT EXISTS idx_cases_owner     ON cases(owner_id);
CREATE INDEX IF NOT EXISTS idx_cases_assignee  ON cases(assignee_id);
CREATE INDEX IF NOT EXISTS idx_cases_created   ON cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_tags      ON cases USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_cases_title_trgm ON cases USING GIN(title gin_trgm_ops);

-- ─── Case Items (linked intel, IOCs, observables) ───────
CREATE TABLE IF NOT EXISTS case_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    item_type       VARCHAR(30) NOT NULL,    -- intel, ioc, technique, observable
    item_id         TEXT NOT NULL,
    item_title      TEXT,
    item_metadata   JSONB NOT NULL DEFAULT '{}',
    added_by        UUID REFERENCES users(id),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(case_id, item_type, item_id)
);

CREATE INDEX IF NOT EXISTS idx_case_items_case  ON case_items(case_id);
CREATE INDEX IF NOT EXISTS idx_case_items_type  ON case_items(item_type, item_id);

-- ─── Case Activity / Timeline ──────────────────────────
CREATE TABLE IF NOT EXISTS case_activities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,   -- created, status_changed, comment, item_added, item_removed, assigned, priority_changed
    detail          TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_activity_case ON case_activities(case_id, created_at DESC);
