-- =============================================
-- Add case_number auto-increment column to cases
-- =============================================

-- Create a sequence for case numbers
CREATE SEQUENCE IF NOT EXISTS case_number_seq START 1;

-- Add case_number column
ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_number INTEGER;

-- Backfill existing cases in creation order
UPDATE cases SET case_number = sub.rn
FROM (
    SELECT id, ROW_NUMBER() OVER (ORDER BY created_at ASC) AS rn FROM cases
) sub
WHERE cases.id = sub.id AND cases.case_number IS NULL;

-- Set default for new rows
ALTER TABLE cases ALTER COLUMN case_number SET DEFAULT nextval('case_number_seq');

-- Advance the sequence past existing rows
SELECT setval('case_number_seq', COALESCE((SELECT MAX(case_number) FROM cases), 0));

-- Make it NOT NULL and UNIQUE
ALTER TABLE cases ALTER COLUMN case_number SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_cases_case_number ON cases(case_number);
