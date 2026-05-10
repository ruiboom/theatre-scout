-- Lightweight in-DB analytics for the admin dashboard.
--
-- Three event types cover what we need:
--   - 'visit'    : page view  (path)
--   - 'search'   : search submitted on /shows  (query)
--   - 'outbound' : user clicked a tracked external link  (target = show slug)
--
-- Internal navigation (e.g. clicking a venue row to land on /venues/<slug>)
-- shows up implicitly as a visit to /venues/<slug>; the dashboard derives
-- venue-click counts from those.

BEGIN;

CREATE TABLE IF NOT EXISTS events (
    id           BIGSERIAL PRIMARY KEY,
    type         TEXT NOT NULL CHECK (type IN ('visit', 'search', 'outbound')),
    path         TEXT,
    target       TEXT,
    query        TEXT,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Lightweight UA + IP-prefix capture so we can spot bot floods later
    -- without storing PII.
    ua           TEXT,
    ip_prefix    TEXT
);

CREATE INDEX IF NOT EXISTS events_occurred_at_idx ON events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS events_type_idx ON events (type);
CREATE INDEX IF NOT EXISTS events_target_idx ON events (target) WHERE target IS NOT NULL;

COMMIT;
