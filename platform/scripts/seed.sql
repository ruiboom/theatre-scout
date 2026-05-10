-- ============================================================================
-- Sample data — enough to exercise every API endpoint locally.
--
--   3 venues across different neighbourhoods
--   6 shows across genres / prices
--   Performances spanning today, this week, this weekend, next month
--   A handful of genre + tag rows
--
-- Apply with:
--   psql $DATABASE_URL -f scripts/seed.sql
-- ============================================================================

BEGIN;

-- ---- venues ---------------------------------------------------------------

INSERT INTO venues (slug, name, neighbourhood, nearest_tube, description, capacity, address, location, website, category)
VALUES
  ('bush-theatre', 'Bush Theatre', 'Shepherd''s Bush', 'Shepherd''s Bush Market', 'A leading new-writing theatre in west London.', 144, '7 Uxbridge Rd, London W12 8LJ',
   ST_SetSRID(ST_MakePoint(-0.2261, 51.5050), 4326)::geography,
   'https://www.bushtheatre.co.uk', 'major'),
  ('park-theatre', 'Park Theatre', 'Finsbury Park', 'Finsbury Park', 'Two-stage theatre with bold programming in north London.', 200, 'Clifton Terrace, London N4 3JP',
   ST_SetSRID(ST_MakePoint(-0.1063, 51.5642), 4326)::geography,
   'https://www.parktheatre.co.uk', 'major'),
  ('finborough-theatre', 'Finborough Theatre', 'Earl''s Court', 'Earl''s Court', 'Tiny pub theatre with an outsized literary reputation.', 50, '118 Finborough Rd, London SW10 9ED',
   ST_SetSRID(ST_MakePoint(-0.1922, 51.4877), 4326)::geography,
   'https://finboroughtheatre.co.uk', 'fringe');

-- ---- tags -----------------------------------------------------------------

INSERT INTO tags (slug, name, type) VALUES
  ('comedy',        'Comedy',        'genre'),
  ('drama',         'Drama',         'genre'),
  ('musical',       'Musical',       'genre'),
  ('experimental',  'Experimental',  'genre'),
  ('political',     'Political',     'tag'),
  ('queer',         'Queer',         'tag'),
  ('one-person',    'One-person',    'tag'),
  ('weird',         'Weird',         'tag'),
  ('first-date',    'First-date',    'tag');

-- ---- shows ----------------------------------------------------------------

WITH v AS (
  SELECT slug, id FROM venues
)
INSERT INTO shows (
  slug, venue_id, title, show_type,
  description_short, description_full,
  price_min_pence, price_max_pence,
  duration_minutes, age_rating, content_warnings,
  booking_url, writer, director, cast_members
)
SELECT * FROM (VALUES
  ('the-borrowed-time', (SELECT id FROM v WHERE slug='bush-theatre'),
   'The Borrowed Time', 'play',
   'A two-hander about grief, time and the music we keep coming back to.',
   'A lyrical, funny, devastating play set in a flat above a Shepherd''s Bush record shop. Two estranged siblings sort through their late father''s LP collection and find more than they bargained for.',
   1500, 2500, 95, '14+', ARRAY['grief','death of a parent']::text[],
   'https://www.bushtheatre.co.uk/event/borrowed-time/', 'Aoife Ó Murchú',
   'Lynette Linton', ARRAY['Sope Dirisu','Niamh Cusack']),

  ('night-bus', (SELECT id FROM v WHERE slug='bush-theatre'),
   'Night Bus', 'comedy',
   'Six strangers, one N207 bus, fifty-five minutes from Acton to Holborn.',
   'A late-night comedy of errors that won''t let you off until the last stop.',
   1000, 1800, 70, '16+', ARRAY['strong language']::text[],
   'https://www.bushtheatre.co.uk/event/night-bus/', 'Tess Walker',
   'Daniel Bailey', ARRAY[]::text[]),

  ('queer-cartography', (SELECT id FROM v WHERE slug='park-theatre'),
   'Queer Cartography', 'play',
   'A queer love story mapped across thirty years of north London.',
   'Spans Stoke Newington 1994 to Finsbury Park 2024, told in vignettes.',
   1200, 2200, 110, NULL, ARRAY[]::text[],
   'https://www.parktheatre.co.uk/event/queer-cartography/', 'Jake Boon',
   'Jamie Armitage', ARRAY['Sara Powell','Ali Wright']),

  ('the-machine-room', (SELECT id FROM v WHERE slug='park-theatre'),
   'The Machine Room', 'play',
   'A factory closes. The workers stay. A political ghost story.',
   'Set in a Sheffield steel mill in 1986, a chorus of nine workers refuse to leave and find that the building has its own ideas.',
   1500, 2800, 130, '15+', ARRAY['themes of class violence']::text[],
   'https://www.parktheatre.co.uk/event/machine-room/', 'Ifeyinwa Frederick',
   'Roy Alexander Weise', ARRAY[]::text[]),

  ('what-the-cat-knew', (SELECT id FROM v WHERE slug='finborough-theatre'),
   'What The Cat Knew', 'comedy',
   'A one-woman show about cats, surveillance and the council.',
   'Weirder than it sounds. Funnier than it has any right to be.',
   1200, 1500, 60, '12+', ARRAY[]::text[],
   'https://finboroughtheatre.co.uk/whatthecatknew/', 'Rosie Beckett',
   'Rosie Beckett', ARRAY['Rosie Beckett']),

  ('a-modest-revolt', (SELECT id FROM v WHERE slug='finborough-theatre'),
   'A Modest Revolt', 'play',
   'A neglected 1968 play, reclaimed.',
   'The Finborough revives a forgotten piece by a Black British playwright who never saw a second London production. Eight performances only.',
   1400, 1800, 100, NULL, ARRAY[]::text[],
   'https://finboroughtheatre.co.uk/modestrevolt/', 'Mustapha Matura',
   'Tinuke Craig', ARRAY[]::text[])
) AS new_shows(slug, venue_id, title, show_type, description_short, description_full,
               price_min_pence, price_max_pence, duration_minutes, age_rating,
               content_warnings, booking_url, writer, director, cast_members);

-- ---- show_tags ------------------------------------------------------------

INSERT INTO show_tags (show_id, tag_id)
SELECT s.id, t.id
FROM (VALUES
  ('the-borrowed-time',  'drama'),
  ('the-borrowed-time',  'first-date'),
  ('night-bus',          'comedy'),
  ('night-bus',          'weird'),
  ('queer-cartography',  'drama'),
  ('queer-cartography',  'queer'),
  ('the-machine-room',   'drama'),
  ('the-machine-room',   'political'),
  ('what-the-cat-knew',  'comedy'),
  ('what-the-cat-knew',  'one-person'),
  ('what-the-cat-knew',  'weird'),
  ('a-modest-revolt',    'drama'),
  ('a-modest-revolt',    'political')
) AS pair(show_slug, tag_slug)
JOIN shows s ON s.slug = pair.show_slug
JOIN tags  t ON t.slug = pair.tag_slug;

-- ---- performances ---------------------------------------------------------
-- Spanning today, this week, this weekend, next month so the search/whats-on
-- defaults all return non-empty results.

INSERT INTO performances (show_id, starts_at)
SELECT s.id, perf.starts_at
FROM shows s
CROSS JOIN LATERAL (VALUES
  (NOW() + INTERVAL '6 hours'),
  (NOW() + INTERVAL '1 day 19 hours'),
  (NOW() + INTERVAL '3 days 19 hours'),
  (NOW() + INTERVAL '5 days 19 hours'),
  (NOW() + INTERVAL '12 days 19 hours'),
  (NOW() + INTERVAL '30 days 19 hours')
) AS perf(starts_at)
WHERE s.slug IN (
  'the-borrowed-time', 'night-bus', 'queer-cartography',
  'the-machine-room',  'what-the-cat-knew', 'a-modest-revolt'
);

COMMIT;
