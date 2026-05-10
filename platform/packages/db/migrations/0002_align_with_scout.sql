-- Align with scout/'s evolved data model.
--
-- - shows.start_date / end_date: most listings expose a date range rather than
--   per-night performance times. Scout has been writing to these for months.
-- - venues.postcode_prefix: scout writes this from theatres.yaml; useful for
--   neighbourhood-adjacent area filters.
-- - shows uniqueness changes from (venue_id, title) to (venue_id, title,
--   start_date) so a returning production in a later season counts as new.
-- - Drop the old (venue_id, title) UNIQUE on the way through.

BEGIN;

ALTER TABLE shows
    ADD COLUMN IF NOT EXISTS start_date DATE,
    ADD COLUMN IF NOT EXISTS end_date   DATE;

ALTER TABLE venues
    ADD COLUMN IF NOT EXISTS postcode_prefix TEXT;

CREATE INDEX IF NOT EXISTS shows_dates_idx     ON shows (start_date, end_date);
CREATE INDEX IF NOT EXISTS shows_first_seen_idx ON shows (first_seen_at DESC);

-- Constraint name in 0001_init.sql is auto-generated; drop the old one if
-- present and add the wider key. Idempotent so reruns are safe.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint c
         JOIN pg_class t ON t.oid = c.conrelid
         WHERE t.relname = 'shows' AND c.conname = 'shows_venue_id_title_key'
    ) THEN
        ALTER TABLE shows DROP CONSTRAINT shows_venue_id_title_key;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
         JOIN pg_class t ON t.oid = c.conrelid
         WHERE t.relname = 'shows' AND c.conname = 'shows_venue_id_title_start_date_key'
    ) THEN
        ALTER TABLE shows ADD CONSTRAINT shows_venue_id_title_start_date_key
            UNIQUE (venue_id, title, start_date);
    END IF;
END $$;

COMMIT;
