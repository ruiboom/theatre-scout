# @platform/db

Postgres schema, migrations, and helpers.

## Stack

- **Postgres 16+** (Supabase or Neon both work)
- **PostGIS** for geo queries — *"shows within walking distance of London Bridge"* becomes a one-liner
- **Built-in tsvector full-text search** for keyword search on titles/descriptions — no separate search service

## Tables

- `venues` — 70 theatres, with a PostGIS `location` point
- `shows` — productions, joined to a single venue, with a generated `search_tsv` column
- `performances` — individual datetime instances of a show (one row per night)
- `tags` — typed (`genre` | `tag`), e.g. `comedy`, `queer`, `political`
- `show_tags` — join
- `scrape_runs` — observability for the ingestion pipeline

The strict normalisation (one show ⇒ many performances) is what makes *"what's on tonight near me"* a clean SQL query.

## Apply schema

```bash
# create db
createdb listings
# install postgis extension
psql listings -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
# apply schema
psql listings -f schema.sql
# (optional) seed sample data
psql listings -f ../../scripts/seed.sql
```

## Migration policy

`schema.sql` is the canonical full schema. Every change goes in `migrations/NNNN_name.sql` (sequentially numbered) AND is applied to `schema.sql` so a fresh DB matches a migrated DB. Test this in CI.
