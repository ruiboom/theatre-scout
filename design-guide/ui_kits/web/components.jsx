// Theatre Scout — Swiss Index UI Kit
// Components shared across the click-thru. Exposes all to window so they
// can be used from a separate babel script tag.

const Bar = ({ saved = 7 }) => (
  <header className="bar">
    <div className="bar-l">
      <div className="bar-tile">TS</div>
      <strong>TS</strong>
      <span className="bar-sep">/</span>
      <span>Theatre Scout</span>
      <span className="bar-sep">/</span>
      <span>London</span>
    </div>
    <nav className="bar-r">
      <span>2026.05.14 · 14:32</span>
      <span>·</span>
      <strong>1,160 SHOWS</strong>
      <span>·</span>
      <span>87 VENUES</span>
      <span>·</span>
      <a href="#"><strong>♡ {String(saved).padStart(2, "0")}</strong></a>
    </nav>
  </header>
);

const Tabs = ({ items, active, onChange }) => (
  <div className="tabs">
    {items.map((t) => (
      <button
        key={t}
        className={`ts-chip ${t === active ? "ts-chip--active" : ""}`}
        onClick={() => onChange?.(t)}
      >
        {t}
      </button>
    ))}
  </div>
);

const BigNumber = ({ kicker, n, sub }) => (
  <div className="bignum">
    <div className="bignum-k">{kicker}</div>
    <div className="bignum-n">{n}</div>
    <div className="bignum-s">{sub}</div>
  </div>
);

const Thumb = ({ ratio = "70/50" }) => (
  <div className="thumb" style={{ aspectRatio: ratio }} />
);

const IndexedRail = ({ idx, title, count, items, onOpen }) => (
  <section className="rail">
    <div className="rail-head">
      <div className="rail-idx">{String(idx).padStart(2, "0")}</div>
      <h2 className="rail-title">{title}</h2>
      <div className="rail-count">{count} SHOWS ›</div>
    </div>
    <div className="rail-grid">
      {items.map((s, i) => (
        <article className="card" key={s.title} onClick={() => onOpen?.(s)}>
          <Thumb ratio="1/1" />
          <div className="card-meta">{s.tag}</div>
          <div className="card-title">{s.title}</div>
          <div className="card-sub">{s.venue}</div>
          <div className="card-dates">{s.dates}</div>
        </article>
      ))}
    </div>
  </section>
);

const IndexRow = ({ idx, show, onOpen }) => (
  <div className="row" onClick={() => onOpen?.(show)}>
    <div className="row-idx">{String(idx).padStart(3, "0")}</div>
    <Thumb ratio="70/50" />
    <div>
      <div className="row-title">{show.title}</div>
      <div className="row-tag">{show.tag}</div>
    </div>
    <div className="row-venue">{show.venue}</div>
    <div className="row-dates">{show.dates}</div>
    <button className="row-save" onClick={(e) => { e.stopPropagation(); }}>♡</button>
  </div>
);

const SpecSheet = ({ rows }) => (
  <dl className="spec">
    {rows.map(([k, v]) => (
      <div className="spec-row" key={k}>
        <dt>{k}</dt>
        <dd>{v}</dd>
      </div>
    ))}
  </dl>
);

const Button = ({ primary, children, ...rest }) => (
  <button className={`ts-btn ${primary ? "ts-btn--primary" : ""}`} {...rest}>
    {children}
  </button>
);

const FilterPanel = ({ open, onClose }) => {
  if (!open) return null;
  return (
    <div className="filter-veil" onClick={onClose}>
      <aside className="filter-panel" onClick={(e) => e.stopPropagation()}>
        <div className="filter-head">
          <div className="ts-meta">FILTERS · 0 ACTIVE</div>
          <button className="filter-x" onClick={onClose}>×</button>
        </div>
        <div className="filter-group">
          <div className="ts-meta">TYPE</div>
          <div className="filter-row">
            {["Play", "Musical", "Opera", "Dance", "Comedy"].map((x) => (
              <span className="ts-chip" key={x}>{x}</span>
            ))}
          </div>
        </div>
        <div className="filter-group">
          <div className="ts-meta">VENUE TIER</div>
          <div className="filter-row">
            {["West End", "Off-West End", "Fringe", "Studio"].map((x) => (
              <span className="ts-chip" key={x}>{x}</span>
            ))}
          </div>
        </div>
        <div className="filter-group">
          <div className="ts-meta">PRICE</div>
          <div className="filter-row">
            {["Under £20", "£20–40", "£40–80", "£80+"].map((x) => (
              <span className="ts-chip" key={x}>{x}</span>
            ))}
          </div>
        </div>
        <div className="filter-foot">
          <Button onClick={onClose}>Reset</Button>
          <Button primary onClick={onClose}>Apply 1,160 results</Button>
        </div>
      </aside>
    </div>
  );
};

Object.assign(window, {
  Bar, Tabs, BigNumber, Thumb, IndexedRail, IndexRow, SpecSheet, Button, FilterPanel,
});
