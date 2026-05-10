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
    from . import almeida  # noqa: F401
    from . import arcola  # noqa: F401
    from . import bloomsbury  # noqa: F401
    from . import charing_cross  # noqa: F401
    from . import churchill  # noqa: F401
    from . import donmar_warehouse  # noqa: F401
    from . import drayton_arms  # noqa: F401
    from . import etcetera  # noqa: F401
    from . import eventim_apollo  # noqa: F401
    from . import hackney_empire  # noqa: F401
    from . import lyric_hammersmith  # noqa: F401
    from . import marylebone  # noqa: F401
    from . import new_wimbledon  # noqa: F401
    from . import old_red_lion  # noqa: F401
    from . import old_vic  # noqa: F401
    from . import omnibus  # noqa: F401
    from . import open_air_theatre  # noqa: F401
    from . import park_theatre  # noqa: F401
    from . import pleasance  # noqa: F401
    from . import richmond  # noqa: F401
    from . import riverside_studios  # noqa: F401
    from . import royal_court  # noqa: F401
    from . import sadlers_wells  # noqa: F401
    from . import soho_theatre  # noqa: F401
    from . import tower  # noqa: F401
    from . import troubadour_canary_wharf  # noqa: F401
    from . import troubadour_wembley_park  # noqa: F401
    from . import union  # noqa: F401
    from . import upstairs_at_the_gatehouse  # noqa: F401
    from . import vaults  # noqa: F401
    from . import waterloo_east  # noqa: F401
    from . import white_bear  # noqa: F401
    from . import yard  # noqa: F401

    # Bulk-registered GenericAdapter subclasses.
    from . import bulk

    bulk.load()
