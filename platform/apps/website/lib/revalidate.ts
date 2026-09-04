import { revalidatePath, revalidateTag } from 'next/cache';

/**
 * Purge every cached render and data read on the site.
 *
 * The data changes exactly once a day (the 05:00 UTC scrape), so pages carry
 * a long ISR fallback TTL and rely on this being called right after the
 * scrape finishes. `revalidateTag('shows')` clears the Data Cache entries
 * (`unstable_cache` reads on /shows, /punt, the layout's scrape stamp);
 * `revalidatePath('/', 'layout')` marks every page under the root layout —
 * index, feeds, every show and venue page — stale so the next hit regenerates
 * it; the sitemap is a metadata route and is purged by path.
 *
 * Cheap and idempotent: it only marks entries stale; nothing regenerates until
 * a request arrives for it.
 */
export function revalidateSite(): void {
  revalidateTag('shows');
  revalidatePath('/', 'layout');
  revalidatePath('/sitemap.xml');
}
