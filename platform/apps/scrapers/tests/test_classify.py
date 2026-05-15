from scrapers.classify import classify


def test_default():
    assert classify("") == "play"
    assert classify("Some random show") == "play"


def test_comedy():
    assert classify("An Evening of Stand-Up Comedy") == "comedy"


def test_musical():
    assert classify("West Side Story — The Musical") == "musical"


def test_dance():
    assert classify("Royal Ballet: Swan Lake") == "dance"


def test_family():
    assert classify("Tots Tales — Age 3+ Storytelling") == "family"


def test_cabaret():
    assert classify("Underbelly Boulevard: Saturday Night Cabaret") == "cabaret"


def test_genre_overrides_misleading_title():
    # A bare comedian-name title has no keyword, but the site says Comedy.
    assert classify("Daniel Sloss", genre="Comedy") == "comedy"
    assert classify("The Trial", genre="Stand-Up") == "comedy"


def test_genre_theatre_label_is_play():
    assert classify("Some Name", genre="Theatre") == "play"


def test_genre_first_alias_wins():
    assert classify("Some Name", genre="Comedy & Cabaret") == "comedy"


def test_unknown_genre_falls_back_to_keywords():
    assert classify("Royal Ballet: Swan Lake", genre="Misc") == "dance"
    assert classify("Plain Title", genre="Whatever") == "play"


def test_empty_genre_falls_back_to_keywords():
    assert classify("An Evening of Stand-Up Comedy", genre="") == "comedy"
    assert classify("An Evening of Stand-Up Comedy", genre=None) == "comedy"
