from __future__ import annotations

from datetime import date

from scout.adapters._jsonld import parse_jsonld


def _wrap(json_body: str) -> str:
    return f'<html><head><script type="application/ld+json">{json_body}</script></head></html>'


def test_single_event() -> None:
    html = _wrap(
        """
        {
            "@context": "https://schema.org",
            "@type": "TheaterEvent",
            "name": "Hamlet",
            "url": "/shows/hamlet",
            "description": "A play",
            "startDate": "2026-05-01",
            "endDate": "2026-07-01",
            "image": "https://cdn.example.com/hamlet.jpg"
        }
        """
    )
    shows = parse_jsonld(html, theatre_slug="almeida", base_url="https://almeida.co.uk")
    assert len(shows) == 1
    s = shows[0]
    assert s.title == "Hamlet"
    assert str(s.url) == "https://almeida.co.uk/shows/hamlet"
    assert s.start_date == date(2026, 5, 1)
    assert s.end_date == date(2026, 7, 1)
    assert str(s.image_url) == "https://cdn.example.com/hamlet.jpg"


def test_array_of_events() -> None:
    html = _wrap(
        """
        [
            {"@type": "TheaterEvent", "name": "A", "url": "https://x.com/a"},
            {"@type": "TheaterEvent", "name": "B", "url": "https://x.com/b"}
        ]
        """
    )
    shows = parse_jsonld(html, theatre_slug="x", base_url="https://x.com")
    assert sorted(s.title for s in shows) == ["A", "B"]


def test_graph_wrapper() -> None:
    html = _wrap(
        """
        {
            "@graph": [
                {"@type": "TheaterEvent", "name": "G1", "url": "https://x.com/1"},
                {"@type": "Organization", "name": "Not an event"},
                {"@type": "ComedyEvent", "name": "G2", "url": "https://x.com/2"}
            ]
        }
        """
    )
    shows = parse_jsonld(html, theatre_slug="x", base_url="https://x.com")
    assert sorted(s.title for s in shows) == ["G1", "G2"]


def test_show_type_from_jsonld_type() -> None:
    html = _wrap(
        """
        [
            {"@type": "ComedyEvent", "name": "C", "url": "https://x.com/c"},
            {"@type": "DanceEvent", "name": "D", "url": "https://x.com/d"},
            {"@type": "TheaterEvent", "name": "T", "url": "https://x.com/t"}
        ]
        """
    )
    by_title = {s.title: s.show_type for s in parse_jsonld(html, "x", "https://x.com")}
    assert by_title == {"C": "comedy", "D": "dance", "T": "play"}


def test_offers_extract_price_range_in_pence() -> None:
    html = _wrap(
        """
        {
            "@type": "TheaterEvent", "name": "Priced", "url": "https://x.com/p",
            "offers": {"@type": "AggregateOffer", "lowPrice": "12.50", "highPrice": "55", "priceCurrency": "GBP"}
        }
        """
    )
    s = parse_jsonld(html, "x", "https://x.com")[0]
    assert s.price_min == 1250
    assert s.price_max == 5500


def test_skips_non_event_types() -> None:
    html = _wrap(
        """
        [
            {"@type": "Organization", "name": "Skip"},
            {"@type": "TheaterEvent", "name": "Keep", "url": "https://x.com/k"}
        ]
        """
    )
    shows = parse_jsonld(html, "x", "https://x.com")
    assert [s.title for s in shows] == ["Keep"]


def test_malformed_json_doesnt_crash() -> None:
    html = (
        '<script type="application/ld+json">not json {</script>'
        '<script type="application/ld+json">{"@type": "TheaterEvent", "name": "OK", "url": "https://x.com/ok"}</script>'
    )
    shows = parse_jsonld(html, "x", "https://x.com")
    assert [s.title for s in shows] == ["OK"]


def test_image_as_object_or_array() -> None:
    html = _wrap(
        """
        [
            {"@type": "TheaterEvent", "name": "Obj", "url": "https://x.com/o",
             "image": {"@type": "ImageObject", "url": "https://cdn/obj.jpg"}},
            {"@type": "TheaterEvent", "name": "Arr", "url": "https://x.com/a",
             "image": ["https://cdn/arr.jpg", "https://cdn/arr2.jpg"]}
        ]
        """
    )
    by_title = {s.title: str(s.image_url) for s in parse_jsonld(html, "x", "https://x.com")}
    assert by_title == {"Obj": "https://cdn/obj.jpg", "Arr": "https://cdn/arr.jpg"}


def test_no_jsonld_returns_empty() -> None:
    assert parse_jsonld("<html>nothing</html>", "x", "https://x.com") == []
