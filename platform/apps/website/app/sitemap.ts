import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/site';
import { sitemapShows } from '@/lib/queries/shows';
import { sitemapVenues } from '@/lib/queries/venues';

// Purged on demand after each scrape (POST /api/v1/admin/revalidate); the TTL
// is a daily fallback. A DB hiccup degrades to a static-pages-only sitemap
// rather than a 500.
export const revalidate = 86400;

const STATIC_PATHS = [
  '',
  '/shows',
  '/new',
  '/closing',
  '/about',
  '/faq',
  '/privacy',
  '/terms',
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = STATIC_PATHS.map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: path === '' ? 'daily' : 'weekly',
    priority: path === '' ? 1 : 0.6,
  }));

  try {
    const venues = await sitemapVenues();
    for (const v of venues) {
      entries.push({
        url: `${SITE_URL}/venues/${v.slug}`,
        lastModified: v.updated_at,
        changeFrequency: 'weekly',
        priority: 0.7,
      });
    }
  } catch {
    /* DB unavailable — ship the static portion rather than failing the route */
  }

  try {
    const shows = await sitemapShows();
    for (const s of shows) {
      entries.push({
        url: `${SITE_URL}/shows/${s.slug}`,
        // `updated_at` only moves when visible content changes (migration
        // 0007) — it used to be re-stamped by every scrape, which told crawlers
        // the whole site changed daily and they re-crawled the lot.
        lastModified: s.updated_at,
        changeFrequency: 'weekly',
        priority: 0.5,
      });
    }
  } catch {
    /* as above */
  }

  return entries;
}
