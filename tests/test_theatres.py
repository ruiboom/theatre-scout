from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from scout.models import Theatre
from scout.theatres import load

YAML_PATH = Path(__file__).resolve().parent.parent / "theatres.yaml"

EXPECTED_TOTAL = 68
EXPECTED_COUNTS = {"major": 18, "mid": 19, "fringe": 19, "outer": 12}

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d{1,2}[A-Z]?$")


@pytest.fixture(scope="module")
def theatres() -> list[Theatre]:
    return load(YAML_PATH)


def test_yaml_file_exists() -> None:
    assert YAML_PATH.is_file()


def test_loads_expected_total(theatres: list[Theatre]) -> None:
    assert len(theatres) == EXPECTED_TOTAL


def test_slugs_unique(theatres: list[Theatre]) -> None:
    slugs = [t.slug for t in theatres]
    assert len(slugs) == len(set(slugs))


def test_slugs_kebab_case(theatres: list[Theatre]) -> None:
    bad = [t.slug for t in theatres if not SLUG_RE.match(t.slug)]
    assert bad == []


def test_category_counts(theatres: list[Theatre]) -> None:
    counts = Counter(t.category for t in theatres)
    assert dict(counts) == EXPECTED_COUNTS


def test_urls_https(theatres: list[Theatre]) -> None:
    bad = [t.url for t in theatres if not str(t.url).startswith("https://")]
    assert bad == []


def test_postcode_prefix_shape(theatres: list[Theatre]) -> None:
    bad = [t.postcode_prefix for t in theatres if not POSTCODE_RE.match(t.postcode_prefix)]
    assert bad == []


def test_load_returns_typed_theatres(theatres: list[Theatre]) -> None:
    assert all(isinstance(t, Theatre) for t in theatres)
