from scrapers.normalize import parse_price_range, slugify, clean_text


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_unicode():
    assert slugify("Café déjà vu") == "cafe-deja-vu"


def test_price_range():
    assert parse_price_range("£10-£25") == (1000, 2500)


def test_price_free():
    assert parse_price_range("Free") == (0, 0)


def test_price_from():
    assert parse_price_range("From £15") == (1500, None)


def test_price_none():
    assert parse_price_range("Pay what you can") == (None, None)


def test_clean_text():
    assert clean_text("  hello\n  world  ") == "hello world"
