"""Adapter package. Each `<slug>.py` defines a `BaseAdapter` subclass and registers itself."""

import importlib
import pkgutil

from scout.adapters.registry import all_adapters, get_adapter, register

_INTERNAL = {"base", "registry", "_html", "_jsonld"}


def load_all() -> None:
    """Import every concrete adapter module so they register themselves."""
    for mod in pkgutil.iter_modules(__path__):
        if mod.name not in _INTERNAL and not mod.name.startswith("_"):
            importlib.import_module(f"{__name__}.{mod.name}")


__all__ = ["all_adapters", "get_adapter", "load_all", "register"]
