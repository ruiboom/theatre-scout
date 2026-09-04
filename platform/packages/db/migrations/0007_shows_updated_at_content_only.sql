-- shows.updated_at should mean "the listing content changed", not "the scraper
-- ran". Until now the daily `scrape all --replace` deleted and re-inserted every
-- venue's rows, so every show carried today's updated_at, the sitemap told
-- crawlers all ~1,400 show pages changed daily, and they obligingly re-crawled
-- the lot — each hit regenerating an ISR page and querying Neon.
--
-- The writer now upserts in place (see apps/scrapers/scrapers/writer.py) and
-- this trigger ignores housekeeping-only updates (last_seen_at, raw_data), so
-- updated_at — and therefore the sitemap's <lastmod> — only moves when a field
-- someone can actually see has changed.

CREATE OR REPLACE FUNCTION set_shows_updated_at() RETURNS TRIGGER AS $$
BEGIN
    IF ROW(NEW.slug, NEW.venue_id, NEW.title, NEW.show_type,
           NEW.description_short, NEW.description_full,
           NEW.price_min_pence, NEW.price_max_pence,
           NEW.start_date, NEW.end_date, NEW.duration_minutes, NEW.age_rating,
           NEW.content_warnings, NEW.image_url, NEW.booking_url,
           NEW.writer, NEW.director, NEW.cast_members, NEW.reviews_summary)
       IS NOT DISTINCT FROM
       ROW(OLD.slug, OLD.venue_id, OLD.title, OLD.show_type,
           OLD.description_short, OLD.description_full,
           OLD.price_min_pence, OLD.price_max_pence,
           OLD.start_date, OLD.end_date, OLD.duration_minutes, OLD.age_rating,
           OLD.content_warnings, OLD.image_url, OLD.booking_url,
           OLD.writer, OLD.director, OLD.cast_members, OLD.reviews_summary)
    THEN
        NEW.updated_at = OLD.updated_at;
        RETURN NEW;
    END IF;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS shows_updated_at ON shows;
CREATE TRIGGER shows_updated_at BEFORE UPDATE ON shows
    FOR EACH ROW EXECUTE FUNCTION set_shows_updated_at();
