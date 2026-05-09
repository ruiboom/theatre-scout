from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from scout.models import Show


class _ClientLike(Protocol):
    def get(self, url: str, *, stealth: bool = False) -> object | None: ...


class BaseAdapter(ABC):
    """Per-theatre adapter. Subclasses must define `slug`, `url`, and `parse(html, base_url)`."""

    slug: str = ""
    url: str = ""
    requires_js: bool = False

    @abstractmethod
    def parse(self, html: str, base_url: str) -> list[Show]:
        """Pure parser: HTML → list of Show. No IO."""

    def fetch(self, client: _ClientLike) -> list[Show]:
        resp = client.get(self.url, stealth=self.requires_js)
        if resp is None:
            return []
        text = getattr(resp, "text", None) or getattr(resp, "content", b"").decode(
            "utf-8", errors="replace"
        )
        return self.parse(text, self.url)
