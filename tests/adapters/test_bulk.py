"""Smoke tests for the bulk-registered adapters.

For each adapter, parses its saved fixture (if present) and asserts:
  - it does not raise
  - if it returns shows, every Show has a non-empty title and an http(s) URL

Per-adapter quality bars (e.g. "must return >= N shows") belong in dedicated
test modules, not here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scout import adapters

adapters.load_all()  # register everything

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _all_slugs() -> list[str]:
    return [a.slug for a in adapters.all_adapters()]


@pytest.mark.parametrize("slug", _all_slugs())
def test_adapter_parses_fixture_without_error(slug: str) -> None:
    adapter = adapters.get_adapter(slug)()
    fixture = FIXTURES / f"{slug}.html"
    if not fixture.is_file():
        pytest.skip(f"no fixture for {slug}")
    shows = adapter.parse(fixture.read_text(encoding="utf-8"), adapter.url)
    for s in shows:
        assert s.title, f"{slug}: empty title in show"
        assert str(s.url).startswith(("http://", "https://")), f"{slug}: bad url in show {s.title}"
