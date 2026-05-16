export const metadata = { title: 'Privacy' };

/**
 * Privacy policy. Must stay factually consistent with the FAQ
 * ("Do you use cookies or track me?") and with what's actually wired up:
 * Vercel Web Analytics (cookieless) in layout.tsx + server-side anonymous
 * counts. Update the "Last updated" date on any material change.
 */
export default function PrivacyPage() {
  return (
    <article style={{ maxWidth: '40rem' }}>
      <h1>Privacy policy</h1>
      <p>
        <em>Last updated: 16 May 2026</em>
      </p>
      <p>
        Theatre Scout is an independent, free listings directory for London
        theatres outside the West End. It is not affiliated with any theatre
        or ticketing company. This policy explains the little data the service
        handles &mdash; on the website and through the AI assistant
        connectors.
      </p>

      <h2>The short version</h2>
      <p>
        No accounts. No login. No advertising. No cookies for tracking. We
        don&rsquo;t sell or share personal data, because we don&rsquo;t collect
        any that identifies you.
      </p>

      <h2>What we collect on the website</h2>
      <p>
        We use <strong>Vercel Web Analytics</strong>, a cookieless analytics
        service that records aggregate page views without cross-site tracking,
        fingerprinting, or storing data that identifies an individual visitor.
      </p>
      <p>
        We also keep <strong>anonymous server-side counts</strong> &mdash;
        totals such as page views, popular search terms, and which{' '}
        <em>Book tickets</em> links are clicked. These are aggregate numbers
        only, used to tell whether the site is working and useful. They are not
        tied to you, your device, or a profile.
      </p>

      <h2>What we collect through Claude / ChatGPT</h2>
      <p>
        Theatre Scout is also available as a remote MCP server that AI
        assistants such as Claude and ChatGPT can connect to. The connection
        uses an OAuth authorisation step purely because those platforms require
        one. That authorisation is <strong>anonymous</strong>: there is no user
        account, and we do not receive your name, email, or your identity with
        the AI provider.
      </p>
      <p>
        The tools only return the same public listings data shown on the
        website. We do not receive the content of your conversations with the
        assistant &mdash; only the specific search request the assistant sends
        (for example, a date range or neighbourhood).
      </p>

      <h2>Payments and ticket booking</h2>
      <p>
        We never sell tickets and never see your payment details. The{' '}
        <strong>Book tickets</strong> button sends you to the venue&rsquo;s own
        box office. Those sites are operated by others and have their own
        privacy policies.
      </p>

      <h2>Where the listings come from</h2>
      <p>
        Show and venue information is gathered from each theatre&rsquo;s own
        public website. It describes productions and venues &mdash; not people
        &mdash; and contains no personal data about you.
      </p>

      <h2>Infrastructure providers</h2>
      <p>
        The service runs on Cloudflare (the MCP server), Vercel (the website
        and analytics), and Neon (the database of public listings). To deliver
        and secure the service, these providers may briefly process technical
        request metadata such as IP address. We do not combine that metadata
        with anything else or use it to identify you.
      </p>

      <h2>Children</h2>
      <p>
        Theatre Scout is a general-audience listings site. It is not directed
        at children and does not knowingly collect data from them.
      </p>

      <h2>Changes</h2>
      <p>
        If this policy changes, the date above changes with it. Material
        changes will be noted on this page.
      </p>

      <h2>Contact</h2>
      <p>
        Questions or concerns? Raise them on the project&rsquo;s GitHub
        repository &mdash; see <em>Who runs this?</em> in the{' '}
        <a href="/faq">FAQ</a>.
      </p>
    </article>
  );
}
