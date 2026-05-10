"""
Pydantic models matching `packages/shared/src/types.ts`.

These are the contract between scrapers (Python) and the database. Every
adapter returns instances of `ScrapedShow`; the writer upserts them. If the
TS types in @platform/shared change, update these too.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ShowType = Literal[
    "play", "musical", "comedy", "dance", "opera", "family", "cabaret", "other"
]
TagType = Literal["genre", "tag"]


class ScrapedTag(BaseModel):
    slug: str
    name: str
    type: TagType


class ScrapedPerformance(BaseModel):
    starts_at: datetime
    available_tickets_estimate: int | None = None
    sold_out: bool = False
    raw_data: dict = Field(default_factory=dict)


class ScrapedShow(BaseModel):
    """One canonical show as produced by an adapter."""

    model_config = ConfigDict(extra="forbid")

    venue_slug: str
    slug: str
    title: str
    show_type: ShowType = "other"
    description_short: str = ""
    description_full: str = ""
    price_min_pence: int | None = None
    price_max_pence: int | None = None
    duration_minutes: int | None = None
    age_rating: str | None = None
    content_warnings: list[str] = Field(default_factory=list)
    image_url: str | None = None
    booking_url: str = ""
    writer: str | None = None
    director: str | None = None
    cast_members: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)  # tag slugs of type 'genre'
    tags: list[str] = Field(default_factory=list)  # tag slugs of type 'tag'
    performances: list[ScrapedPerformance] = Field(default_factory=list)
    raw_data: dict = Field(default_factory=dict)
