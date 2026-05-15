from scrapers.adapters._jsonld import parse_jsonld


def _wrap(json_body: str) -> str:
    return f'<html><head><script type="application/ld+json">{json_body}</script></head></html>'


def _one(json_body: str):
    shows = parse_jsonld(_wrap(json_body), theatre_slug="x", base_url="https://x.com")
    assert len(shows) == 1
    return shows[0]


def test_specific_comedy_event_is_authoritative():
    s = _one('{"@type": "ComedyEvent", "name": "Whatever", "url": "https://x.com/a"}')
    assert s.show_type == "comedy"


def test_specific_dance_event_is_authoritative():
    s = _one('{"@type": "DanceEvent", "name": "Untitled", "url": "https://x.com/a"}')
    assert s.show_type == "dance"


def test_generic_theater_event_with_comedy_signal_reclassifies():
    # The whole point of step D: a stand-up gig wrapped in the generic
    # TheaterEvent must not be locked to "play".
    s = _one(
        '{"@type": "TheaterEvent", "name": "Daniel Sloss: Stand-Up", "url": "https://x.com/a"}'
    )
    assert s.show_type == "comedy"


def test_generic_event_uses_description_signal():
    s = _one(
        '{"@type": "Event", "name": "Mark Watson", "url": "https://x.com/a",'
        ' "description": "An evening of live comedy and improv."}'
    )
    assert s.show_type == "comedy"


def test_generic_theater_event_without_signal_defaults_to_play():
    s = _one('{"@type": "TheaterEvent", "name": "A Doll\'s House", "url": "https://x.com/a"}')
    assert s.show_type == "play"


def test_specific_type_wins_over_ambiguous_cotype():
    s = _one('{"@type": ["TheaterEvent", "ComedyEvent"], "name": "X", "url": "https://x.com/a"}')
    assert s.show_type == "comedy"


def test_non_event_node_is_dropped():
    html = _wrap('{"@type": "Organization", "name": "Not an event"}')
    assert parse_jsonld(html, theatre_slug="x", base_url="https://x.com") == []


def test_graph_wrapper_mixed_nodes():
    html = _wrap(
        """
        {"@graph": [
            {"@type": "TheaterEvent", "name": "Hamlet", "url": "https://x.com/1"},
            {"@type": "Organization", "name": "Ignore me"},
            {"@type": "ComedyEvent", "name": "Jokes", "url": "https://x.com/2"}
        ]}
        """
    )
    shows = parse_jsonld(html, theatre_slug="x", base_url="https://x.com")
    by_title = {s.title: s.show_type for s in shows}
    assert by_title == {"Hamlet": "play", "Jokes": "comedy"}
