import { redirect } from 'next/navigation';
import { clearAdminCookie, isAdmin } from '@/lib/auth';
import {
  scrapeStatus,
  topSearches,
  topShowClicks,
  topVenueClicks,
  venueHealth,
  visitTotals,
  type VenueHealthRow,
} from '@/lib/queries/events';
import { fmtRelative } from '@/lib/format';
import { revalidateSite } from '@/lib/revalidate';

export const metadata = { title: 'Admin · Dashboard' };
export const dynamic = 'force-dynamic';

async function logout() {
  'use server';
  await clearAdminCookie();
  redirect('/admin/login');
}

async function purgeCache() {
  'use server';
  if (!(await isAdmin())) redirect('/admin/login');
  revalidateSite();
  redirect('/admin?purged=1');
}

async function triggerRefresh() {
  'use server';
  // Page-level isAdmin() already gated us; we can talk to GitHub directly
  // without round-tripping through our own /api/v1/admin/refresh.
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    redirect(
      '/admin?error=' +
        encodeURIComponent(
          'GITHUB_TOKEN env var not set. Add a fine-grained PAT with Actions: read & write to Vercel.',
        ),
    );
  }
  const repo = process.env.GITHUB_REPO ?? 'ruiboom/theatre-scout';
  const workflow = process.env.GITHUB_WORKFLOW ?? 'scrape.yml';
  const res = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: 'POST',
      headers: {
        accept: 'application/vnd.github+json',
        authorization: `Bearer ${token}`,
        'x-github-api-version': '2022-11-28',
        'user-agent': 'theatre-scout-admin',
      },
      body: JSON.stringify({ ref: 'main' }),
    },
  );
  if (res.status === 204) {
    redirect('/admin?triggered=1');
  }
  const body = await res.text().catch(() => '');
  redirect(
    '/admin?error=' +
      encodeURIComponent(
        `GitHub returned ${res.status} ${res.statusText} — ${body.slice(0, 200)}`,
      ),
  );
}

export default async function AdminDashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ triggered?: string; purged?: string; error?: string }>;
}) {
  if (!(await isAdmin())) redirect('/admin/login');
  const sp = await searchParams;

  const [visits, searches, venueClicks, showClicks, scrape] = await Promise.all([
    visitTotals(),
    topSearches(7, 10),
    topVenueClicks(7, 10),
    topShowClicks(7, 10),
    scrapeStatus(),
  ]);

  // Kept off the Promise.all above so a not-yet-migrated DB (no venue_health
  // view) degrades to an "unavailable" note instead of 500-ing the dashboard.
  let health: VenueHealthRow[] = [];
  let healthUnavailable = false;
  try {
    health = await venueHealth();
  } catch {
    healthUnavailable = true;
  }

  return (
    <>
      <section className="hero" style={{ padding: '48px 0 32px' }}>
        <div className="hero-l">
          <div className="ts-meta">Admin · dashboard</div>
          <h1 className="hero-h1" style={{ fontSize: 'clamp(40px, 5vw, 64px)' }}>
            What people did,
            <br />
            on Theatre Scout.
          </h1>
        </div>
        <div className="hero-r">
          <BigNum k="Last 24h" n={visits.last_24h.toLocaleString()} s="visits" />
          <BigNum k="Last 7 days" n={visits.last_7d.toLocaleString()} s="visits" />
          <BigNum k="Last 30 days" n={visits.last_30d.toLocaleString()} s="visits" />
          <BigNum
            k="Last scrape"
            n={fmtRelative(scrape.last_run_at)}
            s={`${scrape.successful_today}✓ / ${scrape.failed_today}✗`}
          />
        </div>
      </section>

      <section className="controls" style={{ marginBottom: 24 }}>
        <div className="controls-l" style={{ display: 'flex', gap: 12 }}>
          <form action={purgeCache}>
            <button type="submit" className="ts-btn" title="Mark every cached page and data read stale; the next visit re-renders it from Neon">
              Purge page cache
            </button>
          </form>
          <form action={triggerRefresh}>
            <button type="submit" className="ts-btn ts-btn--primary">
              Refresh data ▶
            </button>
          </form>
          <span className="ts-meta" style={{ alignSelf: 'center' }}>
            Triggers the daily-scrape workflow on GitHub Actions. Takes ~17 min.
          </span>
        </div>
        <div className="controls-r">
          <form action={logout}>
            <button type="submit" className="ts-btn">
              Sign out
            </button>
          </form>
        </div>
      </section>

      {sp.triggered === '1' && (
        <p
          style={{
            padding: '12px 16px',
            border: '1px solid var(--ts-rule)',
            marginBottom: 24,
          }}
        >
          ✓ Scrape kicked off on GitHub Actions. Watch progress at{' '}
          <a
            href="https://github.com/ruiboom/theatre-scout/actions/workflows/scrape.yml"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/ruiboom/theatre-scout/actions
          </a>
          . Live counts here will reflect new data after ~20 min.
        </p>
      )}
      {sp.error && (
        <p
          style={{
            padding: '12px 16px',
            border: '1px solid var(--ts-rule)',
            marginBottom: 24,
            color: '#c8392b',
          }}
        >
          ✗ Refresh failed: <code>{decodeURIComponent(sp.error)}</code>
        </p>
      )}

      <section style={{ marginBottom: 32 }}>
        <HealthPanel rows={health} unavailable={healthUnavailable} />
      </section>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 32,
        }}
      >
        <RankedList
          title="Top searches (7d)"
          rows={searches}
          renderRow={(r) => (
            <>
              <span>{r.key}</span>
              <strong>{r.count}</strong>
            </>
          )}
        />
        <RankedList
          title="Top venues — clicks (7d)"
          rows={venueClicks}
          renderRow={(r) => (
            <>
              <a href={`/venues/${r.slug}`}>{r.name}</a>
              <strong>{r.count}</strong>
            </>
          )}
        />
        <RankedList
          title="Top shows — outbound (7d)"
          rows={showClicks}
          renderRow={(r) => (
            <>
              <span>
                {r.title}
                {r.venue ? (
                  <span className="ts-meta" style={{ marginLeft: 8 }}>
                    · {r.venue}
                  </span>
                ) : null}
              </span>
              <strong>{r.count}</strong>
            </>
          )}
        />
      </div>
    </>
  );
}

function BigNum({ k, n, s }: { k: string; n: string; s: string }) {
  return (
    <div>
      <div className="bignum-k">{k}</div>
      <div className="bignum-n">{n}</div>
      <div className="bignum-s">{s}</div>
    </div>
  );
}

function RankedList<T>({
  title,
  rows,
  renderRow,
}: {
  title: string;
  rows: T[];
  renderRow: (r: T) => React.ReactNode;
}) {
  return (
    <section>
      <div
        className="rail-head"
        style={{ marginBottom: 12, alignItems: 'baseline' }}
      >
        <h2 className="rail-title" style={{ fontSize: 18 }}>
          {title}
        </h2>
      </div>
      {rows.length === 0 ? (
        <p className="ts-meta">No data yet.</p>
      ) : (
        <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {rows.map((r, i) => (
            <li
              key={i}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                gap: 12,
                padding: '8px 0',
                borderBottom: '1px solid var(--ts-rule)',
              }}
            >
              {renderRow(r)}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function HealthPanel({
  rows,
  unavailable,
}: {
  rows: VenueHealthRow[];
  unavailable: boolean;
}) {
  return (
    <section>
      <div
        className="rail-head"
        style={{ marginBottom: 12, alignItems: 'baseline' }}
      >
        <h2 className="rail-title" style={{ fontSize: 18 }}>
          Venue health
          {rows.length > 0 ? ` · ${rows.length} need attention` : ''}
        </h2>
      </div>
      {unavailable ? (
        <p className="ts-meta">
          Unavailable — apply migration <code>0004_venue_health_view</code> to
          this database.
        </p>
      ) : rows.length === 0 ? (
        <p className="ts-meta">All venues healthy ✓</p>
      ) : (
        <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {rows.map((r) => {
            const severe =
              r.reason === 'failed' || r.reason === 'silent-zero';
            return (
              <li
                key={r.venue_slug}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  gap: 12,
                  padding: '8px 0',
                  borderBottom: '1px solid var(--ts-rule)',
                }}
              >
                <span>
                  <a href={`/venues/${r.venue_slug}`}>
                    {r.venue_name ?? r.venue_slug}
                  </a>
                  <span className="ts-meta" style={{ marginLeft: 8 }}>
                    latest {r.latest_found ?? '—'} · ~
                    {Math.round(r.median_found)} median
                  </span>
                </span>
                <strong style={{ color: severe ? '#c8392b' : '#b8860b' }}>
                  {r.reason}
                </strong>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
