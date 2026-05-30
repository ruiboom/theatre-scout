"""Venue scrape-health checks.

Reads the `venue_health` DB view — the single source of truth for the
thresholds, see ``packages/db/migrations/0004_venue_health_view.sql`` — and
surfaces venues whose latest scrape looks broken: failed, silent-zero,
collapse, or stale.

Consumed by the ``scrape health`` CLI command (and, in CI, to open a rolling
GitHub issue). The website's admin dashboard reads the same view directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .writer import _conn


@dataclass(frozen=True)
class VenueHealth:
    venue_slug: str
    venue_name: str | None
    latest_status: str | None
    latest_found: int | None
    median_found: float
    max_found: int
    last_finished_at: str | None
    reason: str


def unhealthy_venues() -> list[VenueHealth]:
    """Every venue the ``venue_health`` view flags (``reason IS NOT NULL``).

    Ordered most-urgent first: failed, then silent-zero, collapse, stale.
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT venue_slug, venue_name, latest_status, latest_found,
                   median_found, max_found, last_finished_at, reason
              FROM venue_health
             WHERE reason IS NOT NULL
             ORDER BY CASE reason
                          WHEN 'failed'      THEN 0
                          WHEN 'silent-zero' THEN 1
                          WHEN 'collapse'    THEN 2
                          ELSE 3
                      END,
                      venue_slug
            """
        )
        rows = cur.fetchall()

    return [
        VenueHealth(
            venue_slug=row[0],
            venue_name=row[1],
            latest_status=row[2],
            latest_found=row[3],
            median_found=float(row[4]) if row[4] is not None else 0.0,
            max_found=int(row[5]) if row[5] is not None else 0,
            last_finished_at=row[6].isoformat() if row[6] is not None else None,
            reason=row[7],
        )
        for row in rows
    ]
