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
