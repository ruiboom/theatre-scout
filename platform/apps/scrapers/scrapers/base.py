"""BaseAdapter — every venue is one subclass of this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .models import ScrapedShow


class BaseAdapter(ABC):
    """
    Subclass per venue. Override `slug`, `homepage`, and `fetch()`.

    The orchestrator calls `fetch()` and writes whatever it returns.
    Adapters should be PURE FUNCTIONS of (HTTP client) -> Iterable[ScrapedShow]
    so they're trivially testable from a saved fixture.
    """

    #: Kebab-case identifier matching the row in `theatres.yaml`.
    slug: str = ""

    #: Used for logging / display.
    name: str = ""

    #: For robots.txt + rate-limiting host buckets.
    homepage: str = ""

    @abstractmethod
    def fetch(self) -> Iterable[ScrapedShow]:
        """Yield normalised `ScrapedShow` records. Raise on hard errors —
        the orchestrator records the failure and moves on."""
        raise NotImplementedError
