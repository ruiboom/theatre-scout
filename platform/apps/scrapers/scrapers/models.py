"""
Pydantic models for the ingest pipeline.

Mirrors `scout/models.py` so adapters port cleanly. The writer
(`scrapers.writer`) is the single place that translates these into platform DB
columns (e.g. `theatre_slug` -> venue_id lookup, `url` -> `booking_url`,
`price_min` integer pence -> `price_min_pence`).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl

Category = Literal["major", "mid", "fringe", "outer"]
ShowType = Literal["play", "musical", "comedy", "dance", "opera", "family", "cabaret", "other"]
ScrapeStatus = Literal["success", "partial", "failed"]
TagType = Literal["genre", "tag"]


def _check_http_url(value: str) -> str:
    if not (value.startswith("http://") or value.startswith("https://")):
        raise ValueError(f"URL must start with http(s)://, got: {value!r}")
    return value


UrlStr = Annotated[str, AfterValidator(_check_http_url)]


class Theatre(BaseModel):
    """Mirrors scout's Theatre. The platform DB calls this `venues`; the writer
    maps slug -> venues.id at insert time."""

    model_config = ConfigDict(frozen=True)

    slug: str
    name: str
    area: str  # platform DB column name is `neighbourhood` — same concept
    postcode_prefix: str | None = None
    category: Category
    url: HttpUrl


class ScrapedPerformance(BaseModel):
    """Optional: only present when the venue exposes per-night times. Most
    listings only give a date range; in that case the show row's
    start_date/end_date are the canonical "what's playing" signal."""

    starts_at: datetime
    available_tickets_estimate: int | None = None
    sold_out: bool = False
    raw_data: dict[str, Any] = Field(default_factory=dict)


class Show(BaseModel):
    """Adapter-facing record. Pure-pythoned shape that mirrors scout's Show.

    Optional richer fields (description_full, performances, content_warnings,
    creators) can be filled by venue-specific bespoke adapters when the venue
    exposes them; the generic adapter only needs the core six.
    """

    model_config = ConfigDict(frozen=True)

    theatre_slug: str
    title: str
    show_type: ShowType = "other"
    description: str = ""
    url: UrlStr  # → booking_url in DB
    start_date: date | None = None
    end_date: date | None = None
    price_min: int | None = None  # pence → price_min_pence in DB
    price_max: int | None = None  # pence → price_max_pence in DB
    image_url: UrlStr | None = None

    # ---- optional richer fields (only set when adapter has them) ----
    description_full: str = ""
    duration_minutes: int | None = None
    age_rating: str | None = None
    content_warnings: tuple[str, ...] = ()
    writer: str | None = None
    director: str | None = None
    cast_members: tuple[str, ...] = ()
    genres: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    performances: tuple[ScrapedPerformance, ...] = ()

    raw: dict[str, Any] = Field(default_factory=dict)


class ScrapeRun(BaseModel):
    theatre_slug: str
    started_at: datetime
    finished_at: datetime | None = None
    status: ScrapeStatus = "success"
    shows_found: int = 0
    error: str | None = None
