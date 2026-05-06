from __future__ import annotations

import pytest

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import all_adapters, get_adapter, register
from scout.models import Show


def test_registry_lookup_by_slug() -> None:
    @register
    class Stub(BaseAdapter):
        slug = "_test_stub"
        url = "https://example.com"

        def parse(self, html: str, base_url: str) -> list[Show]:
            return []

    assert get_adapter("_test_stub") is Stub
    assert "_test_stub" in {a.slug for a in all_adapters()}


def test_registry_unknown_slug_raises() -> None:
    with pytest.raises(KeyError):
        get_adapter("does-not-exist-anywhere")


def test_fetch_calls_client_then_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed: list[Show] = [
        Show(theatre_slug="x", title="A", url="https://x.com/a"),
        Show(theatre_slug="x", title="B", url="https://x.com/b"),
    ]

    class FakeAdapter(BaseAdapter):
        slug = "_fakeadapter"
        url = "https://x.com/whats-on"

        def parse(self, html: str, base_url: str) -> list[Show]:
            assert html == "<html>fixture</html>"
            assert base_url == "https://x.com/whats-on"
            return parsed

    class FakeResp:
        content = b"<html>fixture</html>"
        text = "<html>fixture</html>"
        status_code = 200

    class FakeClient:
        def get(self, url: str) -> FakeResp:
            assert url == "https://x.com/whats-on"
            return FakeResp()

    a = FakeAdapter()
    out = a.fetch(FakeClient())  # type: ignore[arg-type]
    assert out == parsed


def test_fetch_returns_empty_when_client_returns_none() -> None:
    class FakeAdapter(BaseAdapter):
        slug = "_blocked"
        url = "https://x.com"

        def parse(self, html: str, base_url: str) -> list[Show]:
            raise AssertionError("parse should not be called")

    class BlockedClient:
        def get(self, url: str) -> None:
            return None

    assert FakeAdapter().fetch(BlockedClient()) == []  # type: ignore[arg-type]
