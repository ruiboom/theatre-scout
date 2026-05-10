export const metadata = { title: 'About' };

/**
 * About copy from `docs/POSITIONING.md` and `listings-system-arch/about-page.md`.
 * Keep the "two theatre scenes" line in sync with the homepage hero.
 */
export default function AboutPage() {
  return (
    <article style={{ maxWidth: '40rem' }}>
      <h1>About</h1>
      <p>
        There are two theatre scenes in London. One has billboards. The other
        is where the interesting work happens.
      </p>
      <p>This site is about the second one.</p>
      <p>
        70 venues — pub theatres, fringe spaces, arches under railway lines,
        converted warehouses — putting on hundreds of shows a week. Tickets
        usually £10–£25 instead of £80+. Programming that&rsquo;s bolder, weirder,
        more current, more willing to take risks.
      </p>
      <p>
        Yes, the quality is variable. At these prices, that&rsquo;s a feature. You
        get to take a punt. A flop is a story. A hit is a discovery you found
        before anyone else did.
      </p>
    </article>
  );
}
