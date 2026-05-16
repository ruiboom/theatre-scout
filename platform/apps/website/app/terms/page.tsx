export const metadata = { title: 'Terms' };

/**
 * Terms of use. Plain-language, consistent with the FAQ and privacy page.
 * Update the "Last updated" date on any material change.
 */
export default function TermsPage() {
  return (
    <article style={{ maxWidth: '40rem' }}>
      <h1>Terms of use</h1>
      <p>
        <em>Last updated: 16 May 2026</em>
      </p>
      <p>
        By using the Theatre Scout website or its AI assistant connectors, you
        agree to these terms. If you don&rsquo;t agree, please don&rsquo;t use
        the service.
      </p>

      <h2>What Theatre Scout is</h2>
      <p>
        A free, independent directory of what&rsquo;s on at London theatres
        outside the West End. Listings are gathered automatically from each
        venue&rsquo;s own public website. Theatre Scout is not affiliated with
        any theatre, promoter, or ticketing company.
      </p>

      <h2>No tickets, no bookings</h2>
      <p>
        We don&rsquo;t sell tickets or process payments. The{' '}
        <strong>Book tickets</strong> button takes you to the venue&rsquo;s own
        box office, where that venue&rsquo;s terms and prices apply. Any
        transaction is strictly between you and the venue.
      </p>

      <h2>Accuracy &mdash; please verify before you travel</h2>
      <p>
        Listings are re-scraped once a day and can be wrong, incomplete, or out
        of date &mdash; a venue may change a date, price, or cast after our
        last refresh, or our parser for a site may need a fix. Theatre Scout is
        provided <strong>&ldquo;as is&rdquo;</strong>, without warranties of
        any kind. <strong>Always confirm details on the venue&rsquo;s own site
        before booking or travelling.</strong>
      </p>

      <h2>Acceptable use</h2>
      <p>
        The website is for personal, non-commercial browsing. The MCP server
        and underlying API are offered for reasonable, good-faith use by AI
        assistants and similar clients. Please don&rsquo;t:
      </p>
      <ul>
        <li>
          place excessive or automated load on the service, or try to disrupt
          it;
        </li>
        <li>
          bulk-harvest the data to republish it as a competing directory;
        </li>
        <li>
          attempt to bypass rate limits or access controls.
        </li>
      </ul>
      <p>
        We may rate-limit, suspend, or revoke access that is abusive or that
        threatens the stability of the service, at our discretion.
      </p>

      <h2>Intellectual property</h2>
      <p>
        Show titles, descriptions, images, and other listing content belong to
        the respective venues and rights holders; Theatre Scout claims no
        ownership of it and presents it for informational discovery only. The
        Theatre Scout software is published on GitHub under its repository
        licence.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        To the fullest extent permitted by law, Theatre Scout and its
        maintainers are not liable for any loss arising from use of, or
        reliance on, the service or its listings &mdash; including missed
        performances, incorrect prices or times, or unavailable shows. The
        service is a free informational tool, not a booking guarantee.
      </p>

      <h2>Changes</h2>
      <p>
        These terms may change; the date above changes with them. Continued use
        after a change means you accept the updated terms.
      </p>

      <h2>Governing law</h2>
      <p>
        These terms are governed by the laws of England and Wales.
      </p>

      <h2>Contact</h2>
      <p>
        Questions? Raise them on the project&rsquo;s GitHub repository &mdash;
        see <em>Who runs this?</em> in the <a href="/faq">FAQ</a>.
      </p>
    </article>
  );
}
