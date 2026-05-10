/**
 * Resolves the `whats_on.when` enum to a concrete date window in Europe/London.
 *
 * Tested behaviour (see TOOL_SURFACE.md "Critical cases to write first"):
 *   - DST transitions don't shift "this weekend" by an hour
 *   - "tonight" returns today's window only when called before midnight
 *   - Returned window is inclusive on both ends, ISO date strings
 */

const TZ = 'Europe/London';

function londonNow(): Date {
  // Get a Date object that, when read with UTC accessors, gives the
  // London-local components.
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const parts = Object.fromEntries(
    fmt.formatToParts(new Date()).map((p) => [p.type, p.value]),
  ) as Record<string, string>;
  return new Date(
    Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour) === 24 ? 0 : Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    ),
  );
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d);
  out.setUTCDate(out.getUTCDate() + n);
  return out;
}

function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export type WhenWindow = 'tonight' | 'tomorrow' | 'this_weekend' | 'next_weekend' | 'this_week';

export function resolveWindow(when: WhenWindow): { from: string; to: string } {
  const now = londonNow();
  // Reset to start of London-local day so date arithmetic is timezone-stable.
  const today = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  );

  switch (when) {
    case 'tonight':
      return { from: toIsoDate(today), to: toIsoDate(today) };
    case 'tomorrow': {
      const t = addDays(today, 1);
      return { from: toIsoDate(t), to: toIsoDate(t) };
    }
    case 'this_week':
      return { from: toIsoDate(today), to: toIsoDate(addDays(today, 6)) };
    case 'this_weekend': {
      // Find the next Friday (or today if already Fri/Sat/Sun)
      const dow = today.getUTCDay(); // 0=Sun..6=Sat
      let fri: Date;
      if (dow === 5 || dow === 6 || dow === 0) {
        // Friday: today; Saturday: yesterday; Sunday: 2 days ago
        const offset = dow === 5 ? 0 : dow === 6 ? -1 : -2;
        fri = addDays(today, offset);
      } else {
        fri = addDays(today, 5 - dow);
      }
      const sun = addDays(fri, 2);
      return { from: toIsoDate(fri), to: toIsoDate(sun) };
    }
    case 'next_weekend': {
      const dow = today.getUTCDay();
      const offsetToThisFri =
        dow === 5 ? 0 : dow === 6 ? -1 : dow === 0 ? -2 : 5 - dow;
      const thisFri = addDays(today, offsetToThisFri);
      const nextFri = addDays(thisFri, 7);
      const nextSun = addDays(nextFri, 2);
      return { from: toIsoDate(nextFri), to: toIsoDate(nextSun) };
    }
  }
}
