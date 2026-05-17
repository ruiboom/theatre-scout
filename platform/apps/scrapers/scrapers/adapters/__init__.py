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
    # Each module self-registers via @register on import (hence noqa: F401);
    # `bulk` also exposes load() below. Add new bespoke modules here when
    # porting from scout.
    from . import (
        almeida,  # noqa: F401
        arcola,  # noqa: F401
        barons_court,  # noqa: F401
        battersea_arts_centre,  # noqa: F401
        bloomsbury,  # noqa: F401
        bread_and_roses,  # noqa: F401
        bulk,
        canal_cafe,  # noqa: F401
        charing_cross,  # noqa: F401
        churchill,  # noqa: F401
        courtyard,  # noqa: F401
        donmar_warehouse,  # noqa: F401
        drayton_arms,  # noqa: F401
        etcetera,  # noqa: F401
        eventim_apollo,  # noqa: F401
        hackney_empire,  # noqa: F401
        hope_theatre,  # noqa: F401
        lyric_hammersmith,  # noqa: F401
        marylebone,  # noqa: F401
        new_wimbledon,  # noqa: F401
        old_red_lion,  # noqa: F401
        old_vic,  # noqa: F401
        omnibus,  # noqa: F401
        open_air_theatre,  # noqa: F401
        park_theatre,  # noqa: F401
        pleasance,  # noqa: F401
        richmond,  # noqa: F401
        riverside_studios,  # noqa: F401
        royal_court,  # noqa: F401
        sadlers_wells,  # noqa: F401
        soho_theatre,  # noqa: F401
        space_theatre,  # noqa: F401
        tower,  # noqa: F401
        tramshed,  # noqa: F401
        troubadour_canary_wharf,  # noqa: F401
        troubadour_wembley_park,  # noqa: F401
        union,  # noqa: F401
        upstairs_at_the_gatehouse,  # noqa: F401
        vaults,  # noqa: F401
        waterloo_east,  # noqa: F401
        white_bear,  # noqa: F401
        yard,  # noqa: F401
    )

    bulk.load()
