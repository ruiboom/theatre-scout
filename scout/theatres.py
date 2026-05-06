from __future__ import annotations

from pathlib import Path

import yaml

from scout.models import Theatre


def load(path: str | Path) -> list[Theatre]:
    """Load theatres from a YAML file. Pure function — no module state."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [Theatre(**entry) for entry in data]
