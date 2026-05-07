from __future__ import annotations

from scout.enrich import extract_description, extract_image


def test_jsonld_event_description() -> None:
    desc = "A revenge tragedy by Shakespeare set in modern Denmark with electrifying staging."
    html = f"""
    <html><head>
    <script type="application/ld+json">
    {{"@type": "TheaterEvent", "name": "Hamlet", "description": "{desc}"}}
    </script>
    </head></html>
    """
    assert "revenge tragedy" in extract_description(html)


def test_meta_description_fallback() -> None:
    desc = "A bold new staging of A Doll's House by Henrik Ibsen, running through July."
    html = f'<html><head><meta name="description" content="{desc}"></head></html>'
    assert "Doll" in extract_description(html)


def test_og_description_fallback() -> None:
    desc = "A musical journey through 1970s Soho, full of riffs and cocktails."
    html = f'<html><head><meta property="og:description" content="{desc}"></head></html>'
    assert "1970s Soho" in extract_description(html)


def test_first_main_paragraph_fallback() -> None:
    body = (
        "This searing new play by an emerging writer asks what happens when "
        "our memories go private. A bold, witty, kinetic 90 minutes."
    )
    html = f"""
    <html><body>
    <main>
        <article>
            <h1>Show</h1>
            <p>Buy tickets</p>
            <p>{body}</p>
        </article>
    </main>
    </body></html>
    """
    desc = extract_description(html)
    assert "searing new play" in desc


def test_returns_empty_when_nothing_usable() -> None:
    html = "<html><body><p>Hi.</p></body></html>"
    assert extract_description(html) == ""


def test_jsonld_takes_priority_over_meta() -> None:
    meta = "A meta tag description that should be ignored if JSON-LD has one."
    jsonld = "JSON-LD wins because it's the strongest signal of canonical event content."
    html = f"""
    <html><head>
    <meta name="description" content="{meta}">
    <script type="application/ld+json">
    {{"@type": "TheaterEvent", "name": "X", "description": "{jsonld}"}}
    </script>
    </head></html>
    """
    assert "JSON-LD wins" in extract_description(html)


def test_extract_image_from_jsonld_string() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type":"TheaterEvent","name":"X","image":"https://cdn.example.com/poster.jpg"}'
        "</script>"
    )
    assert extract_image(html, "https://x.com") == "https://cdn.example.com/poster.jpg"


def test_extract_image_from_jsonld_object_with_url() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type":"TheaterEvent","name":"X",'
        '"image":{"@type":"ImageObject","url":"https://cdn.example.com/poster.jpg"}}'
        "</script>"
    )
    assert extract_image(html, "https://x.com") == "https://cdn.example.com/poster.jpg"


def test_extract_image_from_og_image() -> None:
    html = '<meta property="og:image" content="https://cdn.example.com/og-poster.jpg">'
    assert extract_image(html, "https://x.com") == "https://cdn.example.com/og-poster.jpg"


def test_extract_image_from_twitter_image() -> None:
    html = '<meta name="twitter:image" content="https://cdn.example.com/tw-poster.jpg">'
    assert extract_image(html, "https://x.com") == "https://cdn.example.com/tw-poster.jpg"


def test_extract_image_from_main_first_img() -> None:
    html = """
    <main>
        <article>
            <img src="/static/spacer.gif" width="1" height="1">
            <img src="/img/hero.jpg" alt="Hero">
        </article>
    </main>
    """
    out = extract_image(html, "https://x.com")
    assert out == "https://x.com/img/hero.jpg"


def test_extract_image_resolves_relative_urls() -> None:
    html = '<meta property="og:image" content="/img/p.jpg">'
    assert extract_image(html, "https://x.com/page/") == "https://x.com/img/p.jpg"


def test_extract_image_returns_none_when_nothing_found() -> None:
    assert extract_image("<html><body><p>no images</p></body></html>", "https://x.com") is None


def test_extract_image_jsonld_takes_priority_over_meta() -> None:
    html = (
        '<meta property="og:image" content="https://x.com/og.jpg">'
        '<script type="application/ld+json">'
        '{"@type":"TheaterEvent","name":"X","image":"https://x.com/jsonld.jpg"}'
        "</script>"
    )
    assert extract_image(html, "https://x.com") == "https://x.com/jsonld.jpg"


def test_truncates_long_descriptions() -> None:
    long = "Words " * 200
    html = f'<meta name="description" content="{long.strip()}">'
    out = extract_description(html)
    assert len(out) <= 601
    assert out.endswith("…")
