from scrapers.text import clean_description, clean_text, is_boilerplate, slugify


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_unicode():
    assert slugify("Café déjà vu") == "cafe-deja-vu"


def test_clean_text_collapses_whitespace():
    assert clean_text("  hello\n  world  ") == "hello world"


def test_clean_text_strips_html():
    assert clean_text("<p>Hello <b>world</b></p>") == "Hello world"


def test_clean_text_decodes_entities():
    assert clean_text("Caf&eacute; &amp; bar") == "Café & bar"


def test_is_boilerplate_login():
    assert is_boilerplate("Please log in to book your tickets")


def test_is_boilerplate_negative():
    assert not is_boilerplate("A two-hander about grief and time.")


def test_clean_description_drops_boilerplate():
    assert clean_description("Cookies on this site help you book tickets") == ""


def test_clean_description_keeps_real_content():
    text = "A devastating new play about three sisters reunited."
    assert clean_description(text) == text
