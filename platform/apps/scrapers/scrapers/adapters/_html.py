"""Pure HTML/text helpers reused across adapters. No IO.

Ported verbatim from scout/adapters/_html.py.
"""

from __future__ import annotations

import re
from datetime import date

_MONTHS = {
    name: i + 1
    for i, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    )
}
_MONTH_LOOKUP: dict[str, int] = {**_MONTHS, **{k[:3]: v for k, v in _MONTHS.items()}}

# Match flexible British date ranges:
#   "Tue 31 March – Sat 23 May 2026"
#   "Sat 16 May - Sat 15 Aug 2026"
#   "Thu 9 - Sat 11 Jul 2026"
#   "31 March 2026 - 23 May 2026"
_WEEKDAY = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
_DATE_RANGE_RE = re.compile(
    rf"(?:{_WEEKDAY}\s+)?"
    r"(\d{1,2})"
    r"(?:\s+([A-Z][a-z]+))?"
    r"(?:\s+(\d{4}))?"
    r"\s*[-–]\s*"
    rf"(?:{_WEEKDAY}\s+)?"
    r"(\d{1,2})\s+"
    r"([A-Z][a-z]+)\s+"
    r"(\d{4})"
)


def parse_date_range(text: str) -> tuple[date | None, date | None]:
    """Best-effort parse of a single date or open-ended date range from human text.

    Returns (start, end). Either may be None if unparseable.
    """
    m = _DATE_RANGE_RE.search(text)
    if m:
        sd, sm_name, sy, ed, em_name, ey = m.groups()
        end_month = _MONTH_LOOKUP.get(em_name)
        if end_month is None:
            return None, None
        end_date = _safe_date(int(ey), end_month, int(ed))
        start_month = _MONTH_LOOKUP.get(sm_name) if sm_name else end_month
        start_year = int(sy) if sy else int(ey)
        start_date = (
            _safe_date(start_year, start_month, int(sd)) if start_month is not None else None
        )
        return start_date, end_date
    single = re.search(r"(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})", text)
    if single:
        sd, sm_name, sy = single.groups()
        m_num = _MONTH_LOOKUP.get(sm_name)
        if m_num is not None:
            d = _safe_date(int(sy), m_num, int(sd))
            return d, d
    return None, None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
