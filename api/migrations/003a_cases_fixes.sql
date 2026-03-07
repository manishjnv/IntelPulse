-- =============================================
-- Cases Phase 1 Fixes: FK constraints + counter trigger
-- =============================================

-- 1. Add FK constraints for case_items.added_by and case_activities.user_id
-- (These columns already REFERENCES users(id) in schema but let's ensure the constraint exists)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_case_items_added_by'
    ) THEN
        ALTER TABLE case_items
            ADD CONSTRAINT fk_case_items_added_by
            FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_case_activities_user_id'
    ) THEN
        ALTER TABLE case_activities
            ADD CONSTRAINT fk_case_activities_user_id
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 2. Add updated_at index for sort performance
CREATE INDEX IF NOT EXISTS idx_cases_updated ON cases(updated_at DESC);

-- 3. Trigger to auto-reconcile denormalized counters on case_items INSERT/DELETE
CREATE OR REPLACE FUNCTION update_case_item_counters()
RETURNS TRIGGER AS $$
DECLARE
    target_case_id UUID;
    intel_ct INTEGER;
    ioc_ct INTEGER;
    obs_ct INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        target_case_id := OLD.case_id;
    ELSE
        target_case_id := NEW.case_id;
    END IF;

    SELECT
        COALESCE(SUM(CASE WHEN item_type = 'intel' THEN 1 ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN item_type = 'ioc' THEN 1 ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN item_type NOT IN ('intel', 'ioc') THEN 1 ELSE 0 END), 0)
    INTO intel_ct, ioc_ct, obs_ct
    FROM case_items
    WHERE case_id = target_case_id;

    UPDATE cases
    SET linked_intel_count = intel_ct,
        linked_ioc_count = ioc_ct,
        linked_observable_count = obs_ct
    WHERE id = target_case_id;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_case_item_counters ON case_items;
CREATE TRIGGER trg_case_item_counters
    AFTER INSERT OR DELETE ON case_items
    FOR EACH ROW
    EXECUTE FUNCTION update_case_item_counters();
