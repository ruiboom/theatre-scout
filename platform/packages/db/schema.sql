-- ============================================================================
-- platform schema — full canonical definition
--
-- A fresh DB created with this file should be byte-identical to a DB built up
-- through every migration in `migrations/`. If they ever diverge, this file
-- wins, and a new migration brings the migrated path back in line.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- powering ILIKE/fuzzy venue lookup

-- ----------------------------------------------------------------------------
-- venues
-- ----------------------------------------------------------------------------

CREATE TABLE venues (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug                TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    -- Carries the same meaning as scout's `area` (e.g. "Islington").
    neighbourhood       TEXT NOT NULL,
    -- First half of UK postcode, e.g. 'N1' / 'SE1'. Useful for area filters.
    postcode_prefix     TEXT,
    nearest_tube        TEXT,
    description         TEXT NOT NULL DEFAULT '',
    capacity            INTEGER,
    address             TEXT NOT NULL DEFAULT '',
    location            GEOGRAPHY(POINT, 4326),
    website             TEXT NOT NULL DEFAULT '',
    category            TEXT NOT NULL CHECK (category IN ('major','mid','fringe','outer')),
    raw_data            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX venues_neighbourhood_idx ON venues (neighbourhood);
CREATE INDEX venues_location_idx     ON venues USING GIST (location);
CREATE INDEX venues_name_trgm_idx    ON venues USING GIN (name gin_trgm_ops);

-- ----------------------------------------------------------------------------
-- shows
-- ----------------------------------------------------------------------------

CREATE TABLE shows (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug                TEXT UNIQUE NOT NULL,
    venue_id            UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    show_type           TEXT NOT NULL DEFAULT 'other'
                        CHECK (show_type IN ('play','musical','comedy','dance','opera','family','cabaret','other')),
    description_short   TEXT NOT NULL DEFAULT '',
    description_full    TEXT NOT NULL DEFAULT '',
    -- price stored in pence for fidelity; API exposes as GBP integers
    price_min_pence     INTEGER,
    price_max_pence     INTEGER,
    -- Run dates from the listings page. Most venues only expose a date range
    -- rather than per-night times, so these are the canonical "what's playing"
    -- columns when no individual `performances` rows exist for the show.
    start_date          DATE,
    end_date            DATE,
    duration_minutes    INTEGER,
    age_rating          TEXT,
    content_warnings    TEXT[] NOT NULL DEFAULT '{}',
    image_url           TEXT,
    booking_url         TEXT NOT NULL DEFAULT '',
    writer              TEXT,
    director            TEXT,
    cast_members        TEXT[] NOT NULL DEFAULT '{}',
    reviews_summary     TEXT,
    -- generated full-text search vector — no triggers needed
    search_tsv          TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description_short, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(description_full, '')), 'C')
    ) STORED,
    raw_data            JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Adapter re-runs upsert on this natural key. Mirrors scout's
    -- `(theatre_slug, title, COALESCE(start_date, ''))` so a show with the same
    -- title that returns to the same venue in a later season still counts as
    -- a new row.
    UNIQUE (venue_id, title, start_date)
);

CREATE INDEX shows_venue_idx     ON shows (venue_id);
CREATE INDEX shows_search_idx    ON shows USING GIN (search_tsv);
CREATE INDEX shows_title_trgm    ON shows USING GIN (title gin_trgm_ops);
CREATE INDEX shows_dates_idx     ON shows (start_date, end_date);
CREATE INDEX shows_first_seen_idx ON shows (first_seen_at DESC);

-- ----------------------------------------------------------------------------
-- performances
-- ----------------------------------------------------------------------------

CREATE TABLE performances (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    show_id             UUID NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    starts_at           TIMESTAMPTZ NOT NULL,
    available_tickets_estimate INTEGER,
    sold_out            BOOLEAN NOT NULL DEFAULT FALSE,
    raw_data            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (show_id, starts_at)
);

CREATE INDEX performances_show_idx       ON performances (show_id);
CREATE INDEX performances_starts_at_idx  ON performances (starts_at);

-- ----------------------------------------------------------------------------
-- tags
-- ----------------------------------------------------------------------------

CREATE TABLE tags (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN ('genre','tag')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX tags_type_idx ON tags (type);

CREATE TABLE show_tags (
    show_id     UUID NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    tag_id      UUID NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (show_id, tag_id)
);

CREATE INDEX show_tags_tag_idx  ON show_tags (tag_id);

-- ----------------------------------------------------------------------------
-- scrape_runs (observability)
-- ----------------------------------------------------------------------------

CREATE TABLE scrape_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_slug      TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN ('success','partial','failed','running')),
    shows_found     INTEGER NOT NULL DEFAULT 0,
    error           TEXT
);

CREATE INDEX scrape_runs_venue_idx       ON scrape_runs (venue_slug);
CREATE INDEX scrape_runs_started_at_idx  ON scrape_runs (started_at DESC);

-- ----------------------------------------------------------------------------
-- events (analytics — visits, searches, outbound clicks)
-- ----------------------------------------------------------------------------

CREATE TABLE events (
    id           BIGSERIAL PRIMARY KEY,
    type         TEXT NOT NULL CHECK (type IN ('visit', 'search', 'outbound')),
    path         TEXT,
    target       TEXT,
    query        TEXT,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ua           TEXT,
    ip_prefix    TEXT
);

CREATE INDEX events_occurred_at_idx ON events (occurred_at DESC);
CREATE INDEX events_type_idx        ON events (type);
CREATE INDEX events_target_idx      ON events (target) WHERE target IS NOT NULL;

-- ----------------------------------------------------------------------------
-- updated_at trigger
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER shows_updated_at BEFORE UPDATE ON shows
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
