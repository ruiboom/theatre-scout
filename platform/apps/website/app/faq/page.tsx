export const metadata = { title: 'FAQ' };

/**
 * Three placeholders to fill before publishing — search for "TODO:" below.
 *   1. CUSTOM_GPT_URL  — published Custom GPT link
 *   2. MCP_SERVER_URL  — deployed MCP worker (replace <account>)
 *   3. GITHUB_REPO_URL — repo URL (currently private)
 */

export default function FaqPage() {
  return (
    <article style={{ maxWidth: '40rem' }}>
      <h1>Frequently asked questions</h1>

      <h2>What is Theatre Scout?</h2>
      <p>
        Theatre Scout is a directory of what&rsquo;s currently on at the 70 London
        theatres that aren&rsquo;t in the West End &mdash; pub theatres, fringe
        spaces, arches under railway lines, converted warehouses. Tickets
        usually £10&ndash;£25 instead of £80+, and programming that&rsquo;s
        bolder and weirder than the big commercial houses.
      </p>

      <h2>Why isn&rsquo;t the Lyceum / Phantom / [a big West End show] here?</h2>
      <p>
        By design. Theatre Scout only covers non-West End venues. The West End
        is already well-served by mainstream ticket sites; we&rsquo;re
        surfacing the scene that isn&rsquo;t.
      </p>

      <h2>What do &ldquo;Major&rdquo;, &ldquo;Mid-size&rdquo;, &ldquo;Fringe&rdquo; and &ldquo;Outer&rdquo; mean?</h2>
      <p>We group venues by size and character:</p>
      <ul>
        <li>
          <strong>Major</strong> &mdash; the bigger Off-West End producing
          houses (Almeida, Bridge, Donmar, National, Old Vic, Young Vic and the
          like).
        </li>
        <li>
          <strong>Mid-size</strong> &mdash; specialist venues with a strong
          identity (Barbican, Park, Soho, Wilton&rsquo;s and the like).
        </li>
        <li>
          <strong>Fringe</strong> &mdash; pub theatres and small fringe rooms
          (Finborough, King&rsquo;s Head, Southwark Playhouse and the like).
        </li>
        <li>
          <strong>Outer</strong> &mdash; larger receiving houses outside zones
          1&ndash;2 (Alexandra Palace, Richmond, Wimbledon and the like).
        </li>
      </ul>

      <h2>Which venues are covered?</h2>
      <p>
        All 70 are listed on the <a href="/">home page</a>, grouped by tier. If
        you can think of a London venue we should track, see{' '}
        <em>How can I add a venue?</em> below.
      </p>

      <h2>Where does the data come from?</h2>
      <p>
        We pull listings directly from each venue&rsquo;s own website. Every
        show, date, price, image and description comes from the theatre itself
        &mdash; no middlemen.
      </p>

      <h2>How often is it updated?</h2>
      <p>
        The full catalogue refreshes once a day, overnight. If a venue updates
        their site today, you&rsquo;ll see it on Theatre Scout the next
        morning.
      </p>

      <h2>A show looks wrong / has the wrong dates / is missing &mdash; what do I do?</h2>
      <p>
        In almost every case, either the venue&rsquo;s own site has the bad
        data or our parser for that venue needs a tweak. File an issue on the
        GitHub repo (see <em>Who runs this?</em>) with the venue name and the
        show title, and we&rsquo;ll fix it.
      </p>

      <h2>Why are some prices / images / cast missing?</h2>
      <p>
        Not every theatre publishes the same level of detail. If a venue
        doesn&rsquo;t list a cast or a price range on their site, we can&rsquo;t
        conjure it. If you spot information on the venue&rsquo;s site that
        we&rsquo;re missing, that&rsquo;s worth flagging too.
      </p>

      <h2>Do you sell tickets?</h2>
      <p>
        No. The <strong>Book tickets</strong> button on every show page sends
        you straight to the venue&rsquo;s own box office. We don&rsquo;t handle
        payments, never see your card, and don&rsquo;t take a cut.
      </p>

      <h2>Can I save a show, get reminders, or subscribe to a calendar feed?</h2>
      <p>
        Not at the moment. A calendar view is something we&rsquo;d like to add
        later; saved-show and reminder features aren&rsquo;t on the roadmap
        today. If any of these would be useful, say so in a GitHub issue
        &mdash; that&rsquo;s how we decide what to build next.
      </p>

      <h2>Is there an app?</h2>
      <p>No app &mdash; but the site is built to work on a phone.</p>

      <h2>Do you use cookies or track me?</h2>
      <p>
        No. No cookies, no third-party trackers, no Google Analytics, no
        fingerprinting. We do count anonymous totals server-side (page views,
        search terms, which <em>Book tickets</em> links got clicked) so we know
        whether the site is working, but none of it is tied to you.
      </p>

      <h2>How can I add a venue?</h2>
      <p>
        Propose it on the GitHub repo (link below) with the venue name and its
        website URL. We add it to the master list and write a small parser for
        its site; from the next overnight scrape onward, its shows appear on
        Theatre Scout.
      </p>
      <p>
        The repo is currently private, so to file an issue you&rsquo;ll need to
        be added as a collaborator first &mdash; mention that when you get in
        touch.
      </p>

      <h2>Can I use Theatre Scout inside ChatGPT?</h2>
      <p>
        Yes &mdash; Theatre Scout has a Custom GPT that can search shows,
        recommend things to see, and answer questions about specific venues,
        all backed by the same data as the website.
      </p>
      <p>
        {/* TODO: replace with published Custom GPT link, e.g. https://chatgpt.com/g/<id>-theatre-scout */}
        <code>[TODO: published Custom GPT link]</code>
      </p>
      <p>To add it:</p>
      <ol>
        <li>Open the link above in ChatGPT.</li>
        <li>
          Click <strong>Start chat</strong>.
        </li>
        <li>
          Ask it things like <em>&ldquo;what&rsquo;s on at the Almeida this month?&rdquo;</em>{' '}
          or <em>&ldquo;recommend a fringe play for Friday night under £20.&rdquo;</em>
        </li>
      </ol>
      <p>A free ChatGPT account is enough; the GPT itself is free to use.</p>

      <h2>Can I use Theatre Scout inside Claude?</h2>
      <p>
        Yes &mdash; Theatre Scout runs as a remote MCP server, which means
        Claude can search shows and make recommendations directly inside a
        conversation.
      </p>
      <p>The server URL is:</p>
      <p>
        <code>https://platform-mcp-server.boomclick.workers.dev/mcp</code>
      </p>
      <p>
        To add it in <strong>Claude Desktop</strong>:
      </p>
      <ol>
        <li>
          Open <strong>Settings &rarr; Connectors</strong>.
        </li>
        <li>
          Choose <strong>Add a custom connector</strong>.
        </li>
        <li>Paste the server URL above.</li>
        <li>
          When prompted, complete the <strong>Authorize</strong> consent
          screen &mdash; Theatre Scout uses OAuth, so you approve access
          once and the tools become available.
        </li>
      </ol>
      <p>
        Once connected, you can ask Claude things like{' '}
        <em>&ldquo;what&rsquo;s on tonight in zone 2?&rdquo;</em> or{' '}
        <em>&ldquo;find me a play about climate change running this week.&rdquo;</em>
      </p>
      <p>
        Other MCP-compatible clients (Claude Code, Cursor, and similar) can use
        the same URL &mdash; check their docs for where to paste it.
      </p>

      <h2>Who runs this?</h2>
      <p>
        Theatre Scout is an independent project, not affiliated with any
        theatre or ticketing company. The code lives on GitHub:
      </p>
      <p>
        {/* TODO: paste GitHub repo URL — note the repo is currently private */}
        <code>[TODO: GitHub repo URL &mdash; currently private]</code>
      </p>
      <p>
        For bug reports, missing data or new venue proposals, file an issue
        there.
      </p>
    </article>
  );
}
