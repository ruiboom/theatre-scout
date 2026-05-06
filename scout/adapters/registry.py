from __future__ import annotations

from scout.adapters.base import BaseAdapter

_REGISTRY: dict[str, type[BaseAdapter]] = {}


def register(cls: type[BaseAdapter]) -> type[BaseAdapter]:
    """Class decorator. Stores the adapter class in the registry under its `slug`."""
    if not cls.slug:
        raise ValueError(f"Adapter {cls.__name__} has no slug")
    _REGISTRY[cls.slug] = cls
    return cls


def get_adapter(slug: str) -> type[BaseAdapter]:
    if slug not in _REGISTRY:
        raise KeyError(f"No adapter registered for slug={slug!r}")
    return _REGISTRY[slug]


def all_adapters() -> list[type[BaseAdapter]]:
    return sorted(_REGISTRY.values(), key=lambda c: c.slug)
