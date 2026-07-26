"""Tiny pure helpers for cleaning extracted text. No IO.

Ported from scout/text.py — same shape so adapters port cleanly.
"""

from __future__ import annotations

import html
import re
import unicodedata

from scrapling.parser import Selector

_WS_RE = re.compile(r"\s+")
_LITERAL_BACKSLASH_NEWLINE_RE = re.compile(r"\\[nrt]")
# Zero-width characters often leak in from rich-text-editor copy/paste; Python's
# `\s` doesn't match them so they survive `_WS_RE` and `.strip()` and end up
# rendered as invisible cruft at the front of descriptions.
_ZERO_WIDTH_RE = re.compile(r"[​‌‍﻿]")

_BOILERPLATE_RE = re.compile(
    r"\b(members? and friends|return to details|logged in|please log in|sign in|"
    r"book your tickets|buy tickets|find out more|cookie|cookies on|accept all|"
    r"privacy policy|tickets are free|discounted tickets|buy discounted)\b",
    re.IGNORECASE,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def clean_text(text: str) -> str:
    """Make extracted body text safe to render directly.

    Decodes HTML entities, strips any embedded tags, normalises literal `\\n`/`\\t`
    artefacts, and collapses runs of whitespace. Plain text passes through unchanged.
    """
    if not text:
        return ""
    decoded = html.unescape(html.unescape(text))
    decoded = _LITERAL_BACKSLASH_NEWLINE_RE.sub(" ", decoded)
    decoded = _ZERO_WIDTH_RE.sub("", decoded)
    if "<" in decoded and ">" in decoded:
        decoded = Selector(decoded).get_all_text(separator=" ", strip=True)
    return _WS_RE.sub(" ", decoded).strip()


def is_boilerplate(text: str) -> bool:
    """True if the text looks like venue boilerplate (login prompts, cookie banners, etc.)."""
    return bool(text) and bool(_BOILERPLATE_RE.search(text))


def clean_description(text: str) -> str:
    """Like `clean_text` but returns "" if the cleaned result is just boilerplate."""
    cleaned = clean_text(text)
    return "" if is_boilerplate(cleaned) else cleaned


def slugify(value: str) -> str:
    """Lower, ascii-fold, hyphen-collapse. Stable for re-runs of the same show."""
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return _SLUG_RE.sub("-", folded).strip("-")
