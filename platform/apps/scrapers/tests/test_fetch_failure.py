"""A dead listing fetch must be a `failed` run, not a silent empty success.

`BaseAdapter.fetch()` used to turn a missing response (None) or an HTTP error
status — e.g. Bush's 503 "maintenance" page, or a 403 anti-bot block — into an
empty list. The orchestrator then recorded status='success', shows_found=0,
indistinguishable from a genuinely empty listing, so the venue surfaced as
'silent-zero' instead of 'failed'. fetch() now raises FetchError on both, which
run_one / run_all record as 'failed' (and never reach the DB write, so a blocked
scrape can't trigger a --replace wipe either).
"""

from __future__ import annotations

import pytest

import scrapers.runner as runner
from scrapers.adapters.base import BaseAdapter, FetchError
from scrapers.models import Show


class _Resp:
    """Minimal stand-in for scrapers.http.Response."""

    def __init__(self, status_code: int, text: str = "<html><body>ok</body></html>") -> None:
        self.status_code = status_code
        self.text = text


class _Client:
    """Returns one fixed response (or None) for every get()."""

    def __init__(self, resp: object | None) -> None:
        self._resp = resp
        self.calls: list[str] = []

    def get(self, url: str, *, stealth: bool = False) -> object | None:
        self.calls.append(url)
        return self._resp


class _Adapter(BaseAdapter):
    slug = "x-venue"
    url = "https://example.test/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return [
            Show(
                theatre_slug=self.slug,
                title="A Show",
                show_type="play",
                url="https://example.test/shows/a-show",
            )
        ]


def test_fetch_raises_on_none() -> None:
    with pytest.raises(FetchError):
        _Adapter().fetch(_Client(None))


@pytest.mark.parametrize("status", [403, 429, 503])
def test_fetch_raises_on_http_error(status: int) -> None:
    with pytest.raises(FetchError):
        _Adapter().fetch(_Client(_Resp(status)))


def test_fetch_parses_on_ok() -> None:
    shows = _Adapter().fetch(_Client(_Resp(200)))
    assert len(shows) == 1


def test_run_one_records_failed_and_skips_write(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[object] = []
    wrote: list[object] = []
    monkeypatch.setattr(runner, "load_all", lambda: None)
    monkeypatch.setattr(runner, "get_adapter", lambda slug: _Adapter)
    monkeypatch.setattr(runner, "record_run", lambda run: recorded.append(run))
    monkeypatch.setattr(runner, "write_shows", lambda *a, **k: wrote.append(a))

    run = runner.run_one("x-venue", _Client(_Resp(503)), replace=True)

    assert run.status == "failed"
    assert "503" in (run.error or "")
    assert wrote == [], "a failed fetch must not reach the DB write (no --replace wipe)"
    assert recorded == [run]
