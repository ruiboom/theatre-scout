from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, HttpUrl

Category = Literal["major", "mid", "fringe", "outer"]
ShowType = Literal["play", "musical", "comedy", "dance", "opera", "family", "cabaret", "other"]
ScrapeStatus = Literal["success", "partial", "failed"]


def _check_http_url(value: str) -> str:
    if not (value.startswith("http://") or value.startswith("https://")):
        raise ValueError(f"URL must start with http(s)://, got: {value!r}")
    return value


UrlStr = Annotated[str, AfterValidator(_check_http_url)]


class Theatre(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    name: str
    area: str
    postcode_prefix: str
    category: Category
    url: HttpUrl


class Show(BaseModel):
    model_config = ConfigDict(frozen=True)

    theatre_slug: str
    title: str
    show_type: ShowType = "other"
    description: str = ""
    url: UrlStr
    start_date: date | None = None
    end_date: date | None = None
    price_min: int | None = None
    price_max: int | None = None
    image_url: UrlStr | None = None
    raw: dict[str, Any] = {}


class ScrapeRun(BaseModel):
    theatre_slug: str
    started_at: datetime
    finished_at: datetime | None = None
    status: ScrapeStatus = "success"
    shows_found: int = 0
    error: str | None = None
