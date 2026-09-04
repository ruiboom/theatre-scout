import { ShowsListing } from '@/app/shows/listing';

// The bare `/shows` — no filters — rendered as an ISR page so the CDN serves
// it. `next.config.ts` rewrites `/shows` here when none of the filter params
// are present; this path is never linked directly (its canonical is /shows and
// robots.txt disallows it). It's the page in the nav and the only /shows URL
// crawlers may fetch, so it's most of the listing traffic — previously a
// function invocation plus Data Cache reads per hit.
//
// The rails rotate on an hourly seed, so an hourly TTL keeps that behaviour;
// the scrape workflow's revalidate call refreshes the data underneath.
export const revalidate = 3600;

export const metadata = {
  alternates: { canonical: '/shows' },
};

export default function ShowsIndexPage() {
  return <ShowsListing sp={{}} />;
}
