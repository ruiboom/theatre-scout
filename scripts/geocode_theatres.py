"""One-off: geocode every theatre via Nominatim and write to theatre-coords.yaml.

Idempotent — already-coded slugs are skipped unless --force is passed. Writes after
each successful lookup so the run is resumable.

Nominatim usage policy: max 1 req/sec, identifying User-Agent. We pause 1.1s.
https://operations.osmfoundation.org/policies/nominatim/

Usage:
    uv run python scripts/geocode_theatres.py
    uv run python scripts/geocode_theatres.py --force --slug almeida
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scout import coords
from scout.theatres import load as load_theatres

THEATRES_PATH = ROOT / "theatres.yaml"
COORDS_PATH = ROOT / "theatre-coords.yaml"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TheatreScout/0.1 (+local research bot; geocoding pass)"
SLEEP_SECS = 1.1


def _query(q: str) -> tuple[float, float] | None:
    params = {"q": q, "format": "json", "limit": "1", "countrycodes": "gb"}
    url = f"{NOMINATIM_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=15) as resp:
        results = json.loads(resp.read().decode("utf-8"))
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def geocode(name: str, area: str) -> tuple[float, float] | None:
    """Query Nominatim with progressively broader fallbacks.

    Each attempt is its own request — caller should respect the per-request rate limit
    (we sleep between calls below). Stops at first hit.
    """
    queries = [
        f"{name}, {area}, London, UK",
        f"{name}, London, UK",
        f"{name}, London",
    ]
    for q in queries:
        hit = _query(q)
        if hit is not None:
            return hit
        time.sleep(SLEEP_SECS)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-geocode even if coords exist.")
    parser.add_argument("--slug", help="Only geocode this slug.")
    args = parser.parse_args()

    theatres = load_theatres(THEATRES_PATH)
    existing = coords.load(COORDS_PATH)
    print(f"Loaded {len(theatres)} theatres, {len(existing)} already geocoded.", flush=True)

    todo = []
    for t in theatres:
        if args.slug and t.slug != args.slug:
            continue
        if not args.force and t.slug in existing:
            continue
        todo.append(t)
    print(f"To geocode: {len(todo)}", flush=True)

    failed: list[str] = []
    for i, t in enumerate(todo, start=1):
        print(f"[{i:02d}/{len(todo):02d}] {t.slug} · {t.name}, {t.area} ...", end=" ", flush=True)
        try:
            hit = geocode(t.name, t.area)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: {e}", flush=True)
            failed.append(t.slug)
            time.sleep(SLEEP_SECS)
            continue
        if hit is None:
            print("no match", flush=True)
            failed.append(t.slug)
        else:
            existing[t.slug] = hit
            coords.save(COORDS_PATH, existing)
            print(f"{hit[0]:.5f}, {hit[1]:.5f}", flush=True)
        time.sleep(SLEEP_SECS)

    print(f"\nDone. {len(existing)} total geocoded. Failed: {failed or 'none'}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
