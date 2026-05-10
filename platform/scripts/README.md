# scripts

Operational SQL + helper scripts.

## Files

- **`seed.sql`** — sample data (3 venues, 6 shows, performances spanning today/week/month). Enough to make every API endpoint return non-empty results without scraping anything. Apply *after* `packages/db/schema.sql`.

## Usage

```bash
# fresh local DB
createdb listings
psql listings -f packages/db/schema.sql
psql listings -f scripts/seed.sql

# now hit the API
pnpm --filter website dev &
curl 'http://localhost:3000/api/v1/whats-on?when=this_weekend' | jq
```
