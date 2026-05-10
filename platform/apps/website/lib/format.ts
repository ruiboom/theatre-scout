/**
 * Tiny formatting helpers used by the templates. Mirrors the jinja filters in
 * scout's web/app.py — `fmt_relative`, `fmt_date`, `fmt_price`.
 */

export function fmtRelative(when: string | null): string {
  if (!when) return 'never';
  const t = new Date(when).getTime();
  if (Number.isNaN(t)) return 'never';
  const secs = Math.floor((Date.now() - t) / 1000);
  if (secs < 0) return 'just now';
  if (secs < 60) return 'just now';
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  if (secs < 86400 * 7) return `${Math.floor(secs / 86400)}d ago`;
  return new Date(when).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export function fmtDateRange(
  start: string | null,
  end: string | null,
): string {
  if (!start) return '';
  const s = new Date(start);
  const left = s.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
  if (!end || end === start) return left;
  const e = new Date(end);
  const right = e.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
  return `${left} – ${right}`;
}

/** Price min/max in *integer pounds*. Show types use null for unknown. */
export function fmtPrice(min: number | null, max: number | null): string {
  if (min == null && max == null) return '';
  if (min === 0 && (max === 0 || max == null)) return 'Free';
  if (min == null) return `up to £${max}`;
  if (max == null || max === min) return `£${min}`;
  return `£${min}–£${max}`;
}

export function pad3(n: number): string {
  return String(n).padStart(3, '0');
}

export function pad2(n: number): string {
  return String(n).padStart(2, '0');
}
