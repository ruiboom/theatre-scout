/**
 * OpenAPI 3.1 spec for the Internal API.
 *
 * Hand-rolled rather than generated because (a) we only have six endpoints,
 * (b) the spec is consumed by ChatGPT's Custom GPT Action which is fussy
 * about schema shape, and (c) it doubles as human-readable contract docs.
 *
 * Hosted at /api/openapi so the canonical URL is the same domain that
 * actually serves the API. Custom GPT setup: paste this URL as the action
 * import. CORS is wide-open since the spec is public anyway.
 *
 * Keep this in sync with `packages/shared/src/types.ts` and
 * `packages/shared/src/schemas.ts`. The MCP server's tool schemas (in
 * `apps/mcp-server/src/tools.ts`) are the third mirror.
 */

import { NextResponse } from 'next/server';

export const dynamic = 'force-static';
export const revalidate = 3600;

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? 'https://theatre-scout-zunz.vercel.app';

const ShowTypeEnum = [
  'play',
  'musical',
  'comedy',
  'dance',
  'opera',
  'family',
  'cabaret',
  'other',
] as const;
const VenueCategoryEnum = ['major', 'mid', 'fringe', 'outer'] as const;

const VenueSummary = {
  type: 'object',
  required: ['id', 'slug', 'name', 'neighbourhood', 'category'],
  properties: {
    id: { type: 'string', format: 'uuid' },
    slug: { type: 'string' },
    name: { type: 'string' },
    neighbourhood: { type: 'string' },
    nearest_tube: { type: ['string', 'null'] },
    category: { type: 'string', enum: VenueCategoryEnum },
  },
};

const Show = {
  type: 'object',
  required: [
    'id',
    'slug',
    'title',
    'show_type',
    'venue',
    'description_short',
    'genres',
    'tags',
    'price_min',
    'price_max',
    'start_date',
    'end_date',
    'next_performance',
    'performance_count',
    'image_url',
    'duration_minutes',
    'age_rating',
    'content_warnings',
    'booking_url',
  ],
  properties: {
    id: { type: 'string', format: 'uuid' },
    slug: { type: 'string' },
    title: { type: 'string' },
    show_type: { type: 'string', enum: ShowTypeEnum },
    venue: { $ref: '#/components/schemas/VenueSummary' },
    description_short: { type: 'string' },
    genres: { type: 'array', items: { type: 'string' } },
    tags: { type: 'array', items: { type: 'string' } },
    price_min: {
      type: ['integer', 'null'],
      description: 'Minimum ticket price in GBP (integer pounds). Null when unknown.',
    },
    price_max: {
      type: ['integer', 'null'],
      description: 'Maximum ticket price in GBP (integer pounds). Null when unknown.',
    },
    start_date: { type: ['string', 'null'], format: 'date' },
    end_date: { type: ['string', 'null'], format: 'date' },
    next_performance: { type: ['string', 'null'], format: 'date-time' },
    performance_count: { type: 'integer', minimum: 0 },
    image_url: { type: ['string', 'null'], format: 'uri' },
    duration_minutes: { type: ['integer', 'null'] },
    age_rating: { type: ['string', 'null'] },
    content_warnings: { type: 'array', items: { type: 'string' } },
    booking_url: { type: 'string', format: 'uri' },
  },
};

const Performance = {
  type: 'object',
  required: ['datetime', 'sold_out'],
  properties: {
    datetime: { type: 'string', format: 'date-time' },
    available_tickets_estimate: { type: ['integer', 'null'] },
    sold_out: { type: 'boolean' },
  },
};

const ShowDetail = {
  allOf: [
    { $ref: '#/components/schemas/Show' },
    {
      type: 'object',
      required: ['description_full', 'performances', 'creators'],
      properties: {
        description_full: { type: 'string' },
        performances: {
          type: 'array',
          items: { $ref: '#/components/schemas/Performance' },
        },
        reviews_summary: { type: ['string', 'null'] },
        creators: {
          type: 'object',
          required: ['cast'],
          properties: {
            writer: { type: ['string', 'null'] },
            director: { type: ['string', 'null'] },
            cast: { type: 'array', items: { type: 'string' } },
          },
        },
      },
    },
  ],
};

const Venue = {
  allOf: [
    { $ref: '#/components/schemas/VenueSummary' },
    {
      type: 'object',
      required: [
        'description',
        'capacity',
        'address',
        'lat',
        'lng',
        'website',
        'current_shows_count',
      ],
      properties: {
        description: { type: 'string' },
        capacity: { type: ['integer', 'null'] },
        address: { type: 'string' },
        postcode_prefix: { type: ['string', 'null'] },
        lat: { type: ['number', 'null'] },
        lng: { type: ['number', 'null'] },
        website: { type: 'string', format: 'uri' },
        current_shows_count: { type: 'integer', minimum: 0 },
      },
    },
  ],
};

const VenueDetail = {
  allOf: [
    { $ref: '#/components/schemas/Venue' },
    {
      type: 'object',
      required: ['current_shows'],
      properties: {
        current_shows: {
          type: 'array',
          items: { $ref: '#/components/schemas/Show' },
        },
      },
    },
  ],
};

const Recommendation = {
  type: 'object',
  required: ['show', 'why'],
  properties: {
    show: { $ref: '#/components/schemas/Show' },
    why: {
      type: 'string',
      description:
        '1–2 sentence rationale for the recommendation, generated server-side.',
    },
  },
};

const ApiError = {
  type: 'object',
  required: ['error'],
  properties: {
    error: {
      type: 'object',
      required: ['code', 'message'],
      properties: {
        code: { type: 'string' },
        message: { type: 'string' },
        details: { type: 'object', additionalProperties: true },
      },
    },
  },
};

const NearLatLng = {
  type: 'object',
  required: ['lat', 'lng'],
  properties: {
    lat: { type: 'number', minimum: -90, maximum: 90 },
    lng: { type: 'number', minimum: -180, maximum: 180 },
    radius_km: { type: 'number', exclusiveMinimum: 0, maximum: 50 },
  },
};

const spec = {
  openapi: '3.1.0',
  info: {
    title: 'Theatre Scout — Internal API',
    version: '1.0.0',
    description:
      "Public API for Theatre Scout, an index of London's non-West End theatres. Six endpoints power every surface (website, MCP server, Custom GPT). Read-only. No auth required.",
    contact: { name: 'Theatre Scout', url: SITE_URL },
  },
  servers: [{ url: `${SITE_URL}/api/v1`, description: 'production' }],
  paths: {
    '/shows': {
      get: {
        operationId: 'searchShows',
        summary: 'Flexible search across all listings',
        description:
          "The workhorse — use whenever the user gives any combination of date, location, price, or genre filter. Empty result is `{shows: [], total: 0}`, never null.",
        parameters: [
          { name: 'date_from', in: 'query', schema: { type: 'string', format: 'date' } },
          { name: 'date_to', in: 'query', schema: { type: 'string', format: 'date' } },
          { name: 'neighbourhood', in: 'query', schema: { type: 'string' } },
          { name: 'category', in: 'query', schema: { type: 'string', enum: VenueCategoryEnum } },
          { name: 'show_type', in: 'query', schema: { type: 'string', enum: ShowTypeEnum } },
          { name: 'q', in: 'query', schema: { type: 'string' }, description: 'Free-text title search.' },
          { name: 'max_price', in: 'query', schema: { type: 'number', minimum: 0 } },
          { name: 'min_price', in: 'query', schema: { type: 'number', minimum: 0 } },
          { name: 'genres', in: 'query', schema: { type: 'array', items: { type: 'string' } }, style: 'form', explode: true },
          { name: 'tags', in: 'query', schema: { type: 'array', items: { type: 'string' } }, style: 'form', explode: true },
          { name: 'venue_ids', in: 'query', schema: { type: 'array', items: { type: 'string', format: 'uuid' } }, style: 'form', explode: true },
          { name: 'sort', in: 'query', schema: { type: 'string', enum: ['start_date', 'end_date', 'title', 'venue'] } },
          { name: 'dir', in: 'query', schema: { type: 'string', enum: ['asc', 'desc'] } },
          { name: 'limit', in: 'query', schema: { type: 'integer', minimum: 1, maximum: 200 } },
        ],
        responses: {
          '200': {
            description: 'Matching shows + total count.',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  required: ['shows', 'total'],
                  properties: {
                    shows: { type: 'array', items: { $ref: '#/components/schemas/Show' } },
                    total: { type: 'integer', minimum: 0 },
                  },
                },
              },
            },
          },
          '400': errorResponse(),
        },
      },
    },
    '/shows/{id_or_slug}': {
      get: {
        operationId: 'getShow',
        summary: 'Full detail for a single show',
        parameters: [
          {
            name: 'id_or_slug',
            in: 'path',
            required: true,
            schema: { type: 'string' },
            description: 'Either a UUID id or the show slug.',
          },
        ],
        responses: {
          '200': {
            description: 'Full show with description, performances, creators.',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/ShowDetail' },
              },
            },
          },
          '404': errorResponse(),
        },
      },
    },
    '/whats-on': {
      get: {
        operationId: 'whatsOn',
        summary: "What's on tonight / this weekend / this week",
        description:
          "Convenience tool for the most common AI question. Resolves the named time window in Europe/London and returns shows running in it. The response includes the resolved window so you can confirm dates back to the user.",
        parameters: [
          {
            name: 'when',
            in: 'query',
            required: true,
            schema: { type: 'string', enum: ['tonight', 'tomorrow', 'this_weekend', 'next_weekend', 'this_week'] },
          },
          {
            name: 'near',
            in: 'query',
            schema: { type: 'string' },
            description:
              'Either a place name (e.g. "London Bridge") or a JSON-encoded `{lat, lng}` object.',
          },
          { name: 'max_price', in: 'query', schema: { type: 'number', minimum: 0 } },
        ],
        responses: {
          '200': {
            description: 'Shows running in the resolved window.',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  required: ['shows', 'total', 'window'],
                  properties: {
                    shows: { type: 'array', items: { $ref: '#/components/schemas/Show' } },
                    total: { type: 'integer', minimum: 0 },
                    window: {
                      type: 'object',
                      required: ['from', 'to'],
                      properties: {
                        from: { type: 'string', format: 'date' },
                        to: { type: 'string', format: 'date' },
                      },
                    },
                  },
                },
              },
            },
          },
          '400': errorResponse(),
        },
      },
    },
    '/recommend': {
      post: {
        operationId: 'recommendShows',
        summary: 'Vibe-based show recommendations',
        description:
          'The "take a punt" tool — use when the user asks for a recommendation by feel rather than exact filters ("something weird and political", "make me laugh", "first date show"). Returns shows ranked by relevance to the vibe with a server-generated `why` per pick.',
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: {
                type: 'object',
                required: ['vibe'],
                properties: {
                  vibe: { type: 'string', minLength: 2, maxLength: 500 },
                  constraints: {
                    type: 'object',
                    properties: {
                      date_from: { type: 'string', format: 'date' },
                      date_to: { type: 'string', format: 'date' },
                      max_price: { type: 'number', minimum: 0 },
                      neighbourhood: { type: 'string' },
                      near: { $ref: '#/components/schemas/NearLatLng' },
                    },
                  },
                  exclude_genres: { type: 'array', items: { type: 'string' } },
                  limit: { type: 'integer', minimum: 1, maximum: 20 },
                },
              },
            },
          },
        },
        responses: {
          '200': {
            description: 'Ranked recommendations with rationales.',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  required: ['recommendations'],
                  properties: {
                    recommendations: {
                      type: 'array',
                      items: { $ref: '#/components/schemas/Recommendation' },
                    },
                  },
                },
              },
            },
          },
          '400': errorResponse(),
        },
      },
    },
    '/venues': {
      get: {
        operationId: 'searchVenues',
        summary: 'Find venues by name, area, or proximity',
        parameters: [
          { name: 'query', in: 'query', schema: { type: 'string' } },
          { name: 'neighbourhood', in: 'query', schema: { type: 'string' } },
          { name: 'limit', in: 'query', schema: { type: 'integer', minimum: 1, maximum: 100 } },
        ],
        responses: {
          '200': {
            description: 'Matching venues + total count.',
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  required: ['venues', 'total'],
                  properties: {
                    venues: { type: 'array', items: { $ref: '#/components/schemas/VenueSummary' } },
                    total: { type: 'integer', minimum: 0 },
                  },
                },
              },
            },
          },
          '400': errorResponse(),
        },
      },
    },
    '/venues/{id_or_slug}': {
      get: {
        operationId: 'getVenue',
        summary: 'Full venue details, optionally with current programming',
        parameters: [
          {
            name: 'id_or_slug',
            in: 'path',
            required: true,
            schema: { type: 'string' },
            description: 'Either a UUID id or the venue slug.',
          },
          {
            name: 'include_shows',
            in: 'query',
            schema: { type: 'boolean', default: true },
          },
        ],
        responses: {
          '200': {
            description: 'Venue with optional current shows.',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/VenueDetail' },
              },
            },
          },
          '404': errorResponse(),
        },
      },
    },
  },
  components: {
    schemas: {
      Show,
      ShowDetail,
      Performance,
      VenueSummary,
      Venue,
      VenueDetail,
      Recommendation,
      NearLatLng,
      ApiError,
    },
  },
};

function errorResponse() {
  return {
    description: 'Validation or lookup error.',
    content: {
      'application/json': {
        schema: { $ref: '#/components/schemas/ApiError' },
      },
    },
  };
}

export function GET() {
  return NextResponse.json(spec, {
    headers: {
      'access-control-allow-origin': '*',
      'cache-control': 'public, max-age=3600, s-maxage=3600',
    },
  });
}
