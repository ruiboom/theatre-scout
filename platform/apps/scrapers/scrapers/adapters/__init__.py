"""Adapter package.

Each bespoke adapter module uses `@register` to put itself in the registry on
import. `bulk` registers GenericAdapter subclasses for venues whose listings
fit the (slug, url, css-selector) pattern. Call `load_all()` once at startup
(typically in CLI / runner) to make sure every adapter is imported and on the
registry.

Mirrors scout/adapters/__init__.py + scout/adapters/registry.py shape.
"""

from __future__ import annotations

from .base import BaseAdapter
from .registry import all_adapters, get_adapter, register

__all__ = ["BaseAdapter", "all_adapters", "get_adapter", "load_all", "register"]


def load_all() -> None:
    """Import every adapter module so each gets a chance to call `@register`.

    Bespoke adapters are imported by name; the bulk pattern is loaded via its
    `load()` helper. Idempotent — safe to call many times.
    """
    # Bespoke modules — add an import here when porting one from scout.
    from . import example  # noqa: F401

    # Bulk-registered GenericAdapter subclasses.
    from . import bulk

    bulk.load()
