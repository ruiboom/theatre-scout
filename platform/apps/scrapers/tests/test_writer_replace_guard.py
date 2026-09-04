"""A transient empty scrape must not wipe a venue under --replace.

Regression guard for the data-loss path: an adapter that momentarily returns 0
shows (site blip / anti-bot during the daily run) used to DELETE the venue's
rows and insert nothing, blanking it on the live site. `write_shows` now skips
the destructive replace when there's nothing to write.

Uses a fake cursor/connection so the test needs no Postgres.
"""

from __future__ import annotations

import scrapers.writer as writer


class _FakeCursor:
    def __init__(self, venue_id: str | None, existing: int) -> None:
        self.venue_id = venue_id
        self.existing = existing
        self.sql: list[str] = []
        self._last = ""

    def execute(self, sql: str, params: object = None) -> None:
        self.sql.append(sql)
        self._last = sql

    def fetchone(self) -> tuple[object, ...] | None:
        if "FROM venues" in self._last:
            return (self.venue_id,) if self.venue_id is not None else None
        if "COUNT(*)" in self._last:
            return (self.existing,)
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *a: object) -> bool:
        return False


class _FakeConn:
    def __init__(self, cur: _FakeCursor) -> None:
        self._cur = cur

    def cursor(self) -> _FakeCursor:
        return self._cur

    def transaction(self) -> _FakeConn:
        # Nested `with conn.transaction()` is a savepoint in psycopg; a no-op here.
        return self

    def commit(self) -> None:
        pass

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *a: object) -> bool:
        return False


def _patch(monkeypatch: object, cur: _FakeCursor) -> None:
    monkeypatch.setattr(writer, "_conn", lambda: _FakeConn(cur))  # type: ignore[attr-defined]


def test_replace_with_empty_shows_does_not_delete(monkeypatch: object) -> None:
    cur = _FakeCursor(venue_id="v1", existing=3)
    _patch(monkeypatch, cur)

    written = writer.write_shows("backyard-comedy-club", [], replace=True)

    assert written == 0
    assert not any("DELETE" in s.upper() for s in cur.sql), (
        "the empty-result guard must prevent the --replace wipe"
    )


def test_replace_with_empty_shows_on_fresh_venue_is_noop(monkeypatch: object) -> None:
    # No existing rows: still must not DELETE, and must not error.
    cur = _FakeCursor(venue_id="v2", existing=0)
    _patch(monkeypatch, cur)

    written = writer.write_shows("some-venue", [], replace=True)

    assert written == 0
    assert not any("DELETE" in s.upper() for s in cur.sql)


# ---- in-place upsert (no wipe-and-rewrite) ---------------------------------
#
# `--replace` used to DELETE every row for the venue and re-insert, which gave
# every show a fresh id/updated_at daily and made the sitemap claim the whole
# site changed every day. It must now only delete rows that fell off the
# listing, and upsert the rest.

from datetime import date  # noqa: E402

from scrapers.models import Show  # noqa: E402


class _RecordingCursor(_FakeCursor):
    def __init__(self, venue_id: str) -> None:
        super().__init__(venue_id, existing=0)
        self.params: list[object] = []

    def execute(self, sql: str, params: object = None) -> None:
        super().execute(sql, params)
        self.params.append(params)


def _show(title: str, url: str) -> Show:
    return Show(
        theatre_slug="almeida",
        title=title,
        url=url,
        show_type="play",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 20),
    )


def test_replace_deletes_only_rows_missing_from_this_run(monkeypatch: object) -> None:
    cur = _RecordingCursor(venue_id="v1")
    _patch(monkeypatch, cur)

    shows = [
        _show("Hamlet", "https://almeida.co.uk/hamlet"),
        _show("Lear", "https://almeida.co.uk/lear"),
    ]
    written = writer.write_shows("almeida", shows, replace=True)

    assert written == 2
    deletes = [(q, p) for q, p in zip(cur.sql, cur.params, strict=True) if "DELETE" in q.upper()]
    assert len(deletes) == 1, "exactly one scoped delete, never a venue-wide wipe"
    q, p = deletes[0]
    assert "NOT (slug = ANY(%s))" in q
    assert isinstance(p, tuple) and p[0] == "v1"
    kept = set(p[1])
    assert kept == {writer._slug_for(s) for s in shows}
    upserts = [q for q in cur.sql if "ON CONFLICT (venue_id, title, start_date)" in q]
    assert len(upserts) == 2


def test_upsert_without_replace_never_deletes(monkeypatch: object) -> None:
    cur = _RecordingCursor(venue_id="v1")
    _patch(monkeypatch, cur)

    written = writer.write_shows("almeida", [_show("Hamlet", "https://x/h")], replace=False)

    assert written == 1
    assert not any("DELETE" in s.upper() for s in cur.sql)
