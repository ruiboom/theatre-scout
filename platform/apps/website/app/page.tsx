import { listVenuesWithCounts } from '@/lib/queries/venues';
import { pad3 } from '@/lib/format';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let venues: Awaited<ReturnType<typeof listVenuesWithCounts>> = [];
  let error: string | null = null;
  try {
    venues = await listVenuesWithCounts();
  } catch (err) {
    error = err instanceof Error ? err.message : 'Database not available';
  }

  const byCat = {
    major: venues.filter((v) => v.category === 'major'),
    mid: venues.filter((v) => v.category === 'mid'),
    fringe: venues.filter((v) => v.category === 'fringe'),
    outer: venues.filter((v) => v.category === 'outer'),
  };
  const totalShows = venues.reduce((acc, v) => acc + v.show_count, 0);
  const totalVenues = venues.length;

  return (
    <>
      <section className="hero">
        <div className="hero-l">
          <div className="ts-meta">London · An index of every show currently in town</div>
          <h1 className="hero-h1">
            An index of
            <br />
            every show
            <br />
            in London.
          </h1>
          <p className="hero-p">
            Anywhere But The West End doesn&rsquo;t sell tickets. We list
            everything playing across {totalVenues || 70} venues outside the West End — from the
            National to a back room in Bethnal Green — and link you to the box
            office.
          </p>
          <div className="hero-cta">
            <a className="ts-btn ts-btn--primary" href="/shows">
              Browse the index ›
            </a>
          </div>
        </div>
        <div className="hero-r">
          <BigNum k="Upcoming" n={totalShows.toLocaleString()} s="listings" />
          <BigNum k="Indexed" n={String(totalVenues)} s="venues" />
          <BigNum
            k="Major + mid"
            n={String(byCat.major.length + byCat.mid.length)}
            s="producing houses"
          />
          <BigNum
            k="Fringe + outer"
            n={String(byCat.fringe.length + byCat.outer.length)}
            s="receiving / pub"
          />
        </div>
      </section>

      {error ? (
        <section className="rail">
          <p className="empty">
            Couldn&rsquo;t reach the database — {error}.
          </p>
        </section>
      ) : (
        <section className="rail">
          <div className="rail-head">
            <div className="rail-idx">01</div>
            <h2 className="rail-title">
              All venues <small>{venues.length} listed, A–Z</small>
            </h2>
            <a className="rail-count" href="/shows">
              Browse the index ›
            </a>
          </div>
          <ul className="row-list" style={{ padding: 0, margin: 0, listStyle: 'none' }}>
            {venues.map((v, i) => (
              <a
                key={v.id}
                className="row row-theatre"
                href={`/venues/${v.slug}`}
              >
                <div className="row-idx">{pad3(i + 1)}</div>
                <div className="row-body">
                  <div className="row-title">{v.name}</div>
                  <div className="row-tag">{v.category}</div>
                </div>
                <div className="row-meta">{v.neighbourhood}</div>
                <div className="row-aside">{v.show_count} shows</div>
              </a>
            ))}
          </ul>
        </section>
      )}
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
