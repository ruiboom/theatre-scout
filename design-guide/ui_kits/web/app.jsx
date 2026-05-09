// Theatre Scout — click-thru screens
// Browse landing → show detail. Filter panel as overlay.

const { useState } = React;

const ScreenBrowse = ({ onOpenShow, onOpenFilter }) => {
  const [tab, setTab] = useState("All");
  const [view, setView] = useState("Rails");
  return (
    <main className="page" data-screen-label="01 Browse">
      <section className="hero">
        <div className="hero-l">
          <div className="ts-meta">LONDON · WEEK 20 · MAY 2026</div>
          <h1 className="hero-h1">An index of every<br/>show currently in<br/>London.</h1>
          <p className="hero-p">
            Theatre Scout doesn't sell tickets. We list everything playing across
            87 venues — from the National to a back room in Bethnal Green — and
            link you to the box office. Updated daily.
          </p>
          <div className="hero-cta">
            <Button primary>Browse the index ↓</Button>
            <Button onClick={onOpenFilter}>Filter · 0</Button>
          </div>
        </div>
        <div className="hero-r">
          <BigNumber kicker="This week" n="14" sub="openings" />
          <BigNumber kicker="Closing soon" n="09" sub="last call" />
          <BigNumber kicker="Upcoming" n="1,160" sub="listings" />
          <BigNumber kicker="Venues" n="87" sub="live" />
        </div>
      </section>

      <section className="controls">
        <Tabs items={["All","Today","This week","New","Closing","Cheap"]} active={tab} onChange={setTab} />
        <div className="controls-r">
          <Tabs items={["Rails","List","Calendar"]} active={view} onChange={setView} />
          <Button onClick={onOpenFilter}>Filter · 0</Button>
        </div>
      </section>

      {view === "Rails" && RAILS.map((r) => (
        <IndexedRail
          key={r.idx}
          idx={r.idx}
          title={r.title}
          count={r.count}
          items={r.picks.map((i) => SHOWS[i])}
          onOpen={onOpenShow}
        />
      ))}

      {view === "List" && (
        <section className="list">
          <div className="ts-meta list-head">ALL SHOWS · 1,160 · SORTED BY OPENING DATE</div>
          {SHOWS.map((s, i) => (
            <IndexRow key={s.title} idx={i + 1} show={s} onOpen={onOpenShow} />
          ))}
        </section>
      )}

      {view === "Calendar" && (
        <section className="cal">
          <div className="ts-meta">MAY 2026</div>
          <div className="cal-grid">
            {Array.from({ length: 21 }).map((_, i) => {
              const day = i + 12;
              const has = i % 3 === 0;
              return (
                <div className="cal-day" key={i}>
                  <div className="cal-d">{String(day).padStart(2,"0")}</div>
                  {has && <div className="cal-show" onClick={() => onOpenShow(SHOWS[i % SHOWS.length])}>
                    <div className="cal-show-t">{SHOWS[i % SHOWS.length].title}</div>
                    <div className="cal-show-v">{SHOWS[i % SHOWS.length].venue}</div>
                  </div>}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <footer className="foot">
        <div className="ts-meta">© 2026 Theatre Scout · London only · Daily index</div>
        <div className="ts-meta">Email · Instagram · About · API</div>
      </footer>
    </main>
  );
};

const ScreenShow = ({ show, onBack }) => (
  <main className="page show" data-screen-label="02 Show detail">
    <div className="crumb">
      <button className="crumb-back" onClick={onBack}>← All shows</button>
      <span className="ts-meta">/ {show.tag} / {show.venue.toUpperCase()}</span>
    </div>

    <section className="show-hero">
      <div className="show-l">
        <div className="ts-meta">0237 · {show.tag}</div>
        <h1 className="show-title">{show.title}</h1>
        <div className="show-venue">{show.venue} · {show.area}</div>
        <p className="show-syn">{show.synopsis}</p>
        <div className="show-cta">
          <Button primary>Book at {show.venue.split(" ")[0]} ↗</Button>
          <Button>♡ Save to watchlist</Button>
        </div>
        <div className="ts-meta show-status">{show.booking}</div>
      </div>
      <div className="show-r">
        <div className="show-still" />
      </div>
    </section>

    <section className="show-body">
      <div>
        <div className="ts-meta">SPECIFICATIONS</div>
        <SpecSheet rows={[
          ["Run", show.dates],
          ["Running time", show.running],
          ["Director", show.director],
          ["Cast", show.cast],
          ["Price", show.price],
          ["Age", "12+"],
          ["Captioned", "Tue 09 Jun, Sat 27 Jun"],
          ["Audio described", "Sat 20 Jun"],
        ]} />
      </div>

      <div>
        <div className="ts-meta">VENUE</div>
        <SpecSheet rows={[
          ["Address", "Almeida Street, N1 1TA"],
          ["Tube", "Angel · Highbury & Islington"],
          ["Capacity", "325"],
          ["Bar", "Yes, opens 1h before"],
        ]} />
      </div>
    </section>

    <section className="rail">
      <div className="rail-head">
        <div className="rail-idx">05</div>
        <h2 className="rail-title">If you like this</h2>
        <div className="rail-count">12 SHOWS ›</div>
      </div>
      <div className="rail-grid">
        {SHOWS.slice(0, 4).map((s) => (
          <article className="card" key={s.title}>
            <Thumb ratio="1/1" />
            <div className="card-meta">{s.tag}</div>
            <div className="card-title">{s.title}</div>
            <div className="card-sub">{s.venue}</div>
            <div className="card-dates">{s.dates}</div>
          </article>
        ))}
      </div>
    </section>
  </main>
);

const App = () => {
  const [active, setActive] = useState(null);
  const [filterOpen, setFilterOpen] = useState(false);
  return (
    <div className="app">
      <Bar />
      {active
        ? <ScreenShow show={active} onBack={() => setActive(null)} />
        : <ScreenBrowse onOpenShow={setActive} onOpenFilter={() => setFilterOpen(true)} />}
      <FilterPanel open={filterOpen} onClose={() => setFilterOpen(false)} />
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
