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
