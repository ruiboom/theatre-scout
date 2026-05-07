from __future__ import annotations

from scout.adapters._generic import GenericAdapter


class _Stub(GenericAdapter):
    slug = "_stub"
    url = "https://example.com/whats-on"
    card_selector = "article"


def test_jsonld_takes_priority_over_cards() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type":"TheaterEvent","name":"From JSONLD","url":"https://x.com/j"}'
        "</script>"
        '<article><h2>From HTML</h2><a href="/h">link</a></article>'
    )
    out = _Stub().parse(html, "https://x.com")
    assert [s.title for s in out] == ["From JSONLD"]


def test_falls_back_to_cards_when_no_jsonld() -> None:
    html = """
    <article><h2>Show A</h2><a href="/a">a</a></article>
    <article><h2>Show B</h2><a href="/b">b</a></article>
    <article>NO TITLE</article>
    """
    out = _Stub().parse(html, "https://x.com")
    assert sorted(s.title for s in out) == ["Show A", "Show B"]


def test_dedupes_by_url() -> None:
    html = """
    <article><h2>Same</h2><a href="/x">a</a></article>
    <article><h2>Same again</h2><a href="/x">b</a></article>
    """
    out = _Stub().parse(html, "https://x.com")
    assert len(out) == 1


def test_skips_javascript_hashes() -> None:
    html = """
    <article><h2>JS</h2><a href="javascript:void(0)">x</a></article>
    <article><h2>Hash</h2><a href="#section">x</a></article>
    <article><h2>Real</h2><a href="/real">x</a></article>
    """
    out = _Stub().parse(html, "https://x.com")
    assert [s.title for s in out] == ["Real"]


def test_no_selector_no_jsonld_returns_empty() -> None:
    class NoSel(GenericAdapter):
        slug = "_nosel"
        url = "https://x.com"

    assert NoSel().parse("<html>no shows here</html>", "https://x.com") == []


def test_link_selector_uses_link_as_card() -> None:
    class LinkMode(GenericAdapter):
        slug = "_lm"
        url = "https://x.com"
        card_selector = 'a[href*="/whats-on/"]'

    html = """
    <a href="/whats-on/show-a">Show A</a>
    <a href="/whats-on/show-b">Show B</a>
    <a href="/about">About</a>
    """
    out = LinkMode().parse(html, "https://x.com")
    assert sorted(s.title for s in out) == ["Show A", "Show B"]


def test_require_date_filters_out_cards_without_dates() -> None:
    class DateReq(GenericAdapter):
        slug = "_datereq"
        url = "https://x.com"
        card_selector = "article"
        require_date = True

    html = """
    <article><h2>With date</h2><a href="/w">x</a> 5 May 2026</article>
    <article><h2>No date</h2><a href="/n">x</a></article>
    """
    out = DateReq().parse(html, "https://x.com")
    assert [s.title for s in out] == ["With date"]
