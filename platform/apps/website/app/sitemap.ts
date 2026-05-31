import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/site';
import { sitemapShows } from '@/lib/queries/shows';
import { sitemapVenues } from '@/lib/queries/venues';

// Regenerated hourly alongside the cached pages it points at. A DB hiccup
// degrades to a static-pages-only sitemap rather than a 500.
export const revalidate = 3600;

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
        changeFrequency: 'daily',
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
        lastModified: s.updated_at,
        changeFrequency: 'daily',
        priority: 0.5,
      });
    }
  } catch {
    /* as above */
  }

  return entries;
}
