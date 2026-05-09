from __future__ import annotations

from scout.text import clean_text


def test_plain_text_passes_through() -> None:
    assert clean_text("A simple description.") == "A simple description."


def test_decodes_html_entities() -> None:
    assert clean_text("Tom &amp; Jerry &lt; oh") == "Tom & Jerry < oh"


def test_strips_tags_after_entity_decode() -> None:
    src = "&lt;p&gt;Members and Friends - you must be logged in&lt;/p&gt;"
    assert clean_text(src) == "Members and Friends - you must be logged in"


def test_strips_real_tags() -> None:
    src = "<p>A play by <em>someone</em> about whatever.</p>"
    assert clean_text(src) == "A play by someone about whatever."


def test_collapses_whitespace_and_newlines() -> None:
    assert clean_text("hello\n\n\tworld   again") == "hello world again"


def test_normalises_literal_backslash_n() -> None:
    # Some JSON-LD descriptions arrive with literal "\n" sequences inside the string.
    assert clean_text("first line\\nsecond line") == "first line second line"


def test_handles_double_encoded_entities() -> None:
    # &amp;lt;p&amp;gt;X&amp;lt;/p&amp;gt; → &lt;p&gt;X&lt;/p&gt; → <p>X</p> → X
    src = "&amp;lt;p&amp;gt;X&amp;lt;/p&amp;gt;"
    assert clean_text(src) == "X"


def test_empty_input() -> None:
    assert clean_text("") == ""


def test_clean_description_drops_boilerplate() -> None:
    from scout.text import clean_description

    boilerplate = (
        "Members and Friends - you must be logged into the web site to buy discounted tickets"
    )
    assert clean_description(boilerplate) == ""


def test_clean_description_keeps_real_descriptions() -> None:
    from scout.text import clean_description

    real = "A bold revival of Henrik Ibsen's classic, staged with electric urgency."
    assert clean_description(real) == real


def test_clean_description_strips_tags_then_drops_boilerplate() -> None:
    from scout.text import clean_description

    src = "&lt;p&gt;Members and Friends - you must be logged in&lt;/p&gt;"
    assert clean_description(src) == ""
