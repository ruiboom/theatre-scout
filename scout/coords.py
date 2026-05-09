from __future__ import annotations

from pathlib import Path

import yaml


def load(path: str | Path) -> dict[str, tuple[float, float]]:
    """Load slug → (lat, lon) from a sidecar YAML. Missing file → empty dict.

    Sidecar format::

        almeida:
          lat: 51.5391
          lon: -0.1031
    """
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: dict[str, tuple[float, float]] = {}
    for slug, entry in data.items():
        if isinstance(entry, dict) and "lat" in entry and "lon" in entry:
            out[slug] = (float(entry["lat"]), float(entry["lon"]))
    return out


def save(path: str | Path, coords: dict[str, tuple[float, float]]) -> None:
    """Write slug → (lat, lon) mapping to a sidecar YAML."""
    serialised = {slug: {"lat": lat, "lon": lon} for slug, (lat, lon) in sorted(coords.items())}
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(serialised, f, sort_keys=False, allow_unicode=True)
