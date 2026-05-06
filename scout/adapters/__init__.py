"""Adapter package. Each `<slug>.py` defines a `BaseAdapter` subclass and registers itself."""

from scout.adapters.registry import all_adapters, get_adapter, register

__all__ = ["all_adapters", "get_adapter", "register"]
