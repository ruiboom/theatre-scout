import { ShowsListing, type Search } from './listing';

// The filtered listing (`/shows?type=…&when=…`). Driven by the query string,
// so it can't be cached by path — but the bare `/shows` never reaches this
// route: `next.config.ts` rewrites it to `/shows-index`, an ISR page served
// from the CDN. Data reads are cached either way; see listing.tsx.
export const dynamic = 'force-dynamic';

export default async function ShowsPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  return <ShowsListing sp={await searchParams} />;
}
