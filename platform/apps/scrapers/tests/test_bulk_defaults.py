from scrapers.adapters import get_adapter, load_all

load_all()


def test_comedy_venue_default_show_type():
    # Stand-up-dominant venues fall back to comedy when JSON-LD, site genre
    # and title keywords are all silent.
    assert get_adapter("hen-and-chickens").default_show_type == "comedy"
    assert get_adapter("underbelly-boulevard").default_show_type == "comedy"


def test_non_comedy_venue_default_unchanged():
    assert get_adapter("barbican").default_show_type == "play"
