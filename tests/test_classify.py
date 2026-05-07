from __future__ import annotations

import pytest

from scout.classify import classify


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tim Key: Live Comedy Special", "comedy"),
        ("Stand up with Lucy Beaumont", "comedy"),
        ("Hamilton: The Musical", "musical"),
        ("Songbook in Concert", "musical"),
        ("La Traviata (Opera)", "opera"),
        ("English National Ballet: Swan Lake", "dance"),
        ("Drag Show: The Glittering Hour", "cabaret"),
        ("Tots' Time: Music for babies", "family"),
        ("A Doll's House", "play"),
        ("", "play"),
    ],
)
def test_classify(text: str, expected: str) -> None:
    assert classify(text) == expected
