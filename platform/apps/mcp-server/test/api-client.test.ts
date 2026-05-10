import { describe, expect, it, vi, beforeEach } from 'vitest';
import { ApiClient } from '../src/api-client.js';

describe('ApiClient', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ shows: [], total: 0 }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;
  });

  it('passes filters as query params', async () => {
    const api = new ApiClient('http://example/api/v1');
    await api.searchShows({
      neighbourhood: 'Hackney',
      max_price: 20,
      min_price: 0,
      limit: 10,
    });
    const url = new URL(String(fetchMock.mock.calls[0]![0]));
    expect(url.pathname).toBe('/api/v1/shows');
    expect(url.searchParams.get('neighbourhood')).toBe('Hackney');
    expect(url.searchParams.get('max_price')).toBe('20');
    expect(url.searchParams.get('limit')).toBe('10');
  });

  it('serialises array params as repeated keys', async () => {
    const api = new ApiClient('http://example/api/v1');
    await api.searchShows({
      genres: ['comedy', 'experimental'],
      min_price: 0,
      limit: 20,
    });
    const url = new URL(String(fetchMock.mock.calls[0]![0]));
    expect(url.searchParams.getAll('genres')).toEqual([
      'comedy',
      'experimental',
    ]);
  });

  it('throws on non-2xx', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('not found', { status: 404 }),
    );
    const api = new ApiClient('http://example/api/v1');
    await expect(api.searchShows({ min_price: 0, limit: 20 })).rejects.toThrow(
      /404/,
    );
  });
});
