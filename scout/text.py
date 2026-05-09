"""Tiny pure helpers for cleaning extracted text. No IO."""

from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

_WS_RE = re.compile(r"\s+")
_LITERAL_BACKSLASH_NEWLINE_RE = re.compile(r"\\[nrt]")

_BOILERPLATE_RE = re.compile(
    r"\b(members? and friends|return to details|logged in|please log in|sign in|"
    r"book your tickets|buy tickets|find out more|cookie|cookies on|accept all|"
    r"privacy policy|tickets are free|discounted tickets|buy discounted)\b",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Make extracted body text safe to render directly.

    Decodes HTML entities, strips any embedded tags, normalises literal `\\n`/`\\t`
    artefacts, and collapses runs of whitespace. Plain text passes through unchanged.
    """
    if not text:
        return ""
    # Some sources double-encode (`&amp;lt;` → `&lt;` → `<`); a second pass is harmless.
    decoded = html.unescape(html.unescape(text))
    decoded = _LITERAL_BACKSLASH_NEWLINE_RE.sub(" ", decoded)
    if "<" in decoded and ">" in decoded:
        decoded = BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True)
    return _WS_RE.sub(" ", decoded).strip()


def is_boilerplate(text: str) -> bool:
    """True if the text looks like venue boilerplate (login prompts, cookie banners, etc.)."""
    return bool(text) and bool(_BOILERPLATE_RE.search(text))


def clean_description(text: str) -> str:
    """Like `clean_text` but returns "" if the cleaned result is just boilerplate."""
    cleaned = clean_text(text)
    return "" if is_boilerplate(cleaned) else cleaned
