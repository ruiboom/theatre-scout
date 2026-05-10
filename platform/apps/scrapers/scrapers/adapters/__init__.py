"""
Adapter registry.

Adding a venue means: write a class in this package, then register the slug
below. Keeping the registry explicit (vs. import-discovery) makes it obvious
which adapters are wired up.
"""

from __future__ import annotations

from ..base import BaseAdapter
from .example import ExampleAdapter

REGISTRY: dict[str, type[BaseAdapter]] = {
    "example": ExampleAdapter,
    # "almeida": AlmeidaAdapter,
    # "bridge":  BridgeAdapter,
    # ...add the other 68 here as they're written
}


def get_adapter(slug: str) -> BaseAdapter:
    if slug not in REGISTRY:
        raise KeyError(f"no adapter registered for venue {slug!r}")
    return REGISTRY[slug]()
