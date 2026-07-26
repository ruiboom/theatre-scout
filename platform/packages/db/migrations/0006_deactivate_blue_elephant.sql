-- blue-elephant: the theatre announced (on blueelephanttheatre.co.uk/whatson,
-- seen 2026-07) that it has surrendered its building — participation work
-- continues but there is no venue and no shows, and "much of our website is
-- now out of date". Its adapter is removed from scrapers/adapters/bulk.py;
-- deactivating the venue row stops venue_health flagging it forever, same as
-- 0005 did for hen-and-chickens and tabard. The row and its historic shows
-- stay for if the company finds a new home:
--   UPDATE venues SET active = TRUE WHERE slug = 'blue-elephant';
--
-- Migrations are applied automatically by the "Apply DB migrations" step of
-- .github/workflows/scrape.yml (ledger table: schema_migrations). To apply by
-- hand instead:
--   psql "$DATABASE_URL" -f packages/db/migrations/0006_deactivate_blue_elephant.sql

BEGIN;

UPDATE venues SET active = FALSE WHERE slug = 'blue-elephant';

COMMIT;
