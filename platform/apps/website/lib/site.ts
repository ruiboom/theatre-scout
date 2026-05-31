/**
 * Canonical public origin, used for the absolute URLs in robots.txt and the
 * sitemap. Defaults to the primary custom domain; override per environment with
 * NEXT_PUBLIC_SITE_URL (e.g. on a preview deployment) so crawlers are pointed
 * at the right host.
 */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? 'https://theatre-scout.fun';
