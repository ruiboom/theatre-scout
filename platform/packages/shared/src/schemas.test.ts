import { describe, expect, it } from 'vitest';
import {
  SearchShowsInput,
  GetShowInput,
  WhatsOnInput,
  RecommendShowsInput,
  GetVenueInput,
} from './schemas.js';

describe('SearchShowsInput', () => {
  it('accepts an empty object (defaults applied)', () => {
    const out = SearchShowsInput.parse({});
    expect(out.limit).toBe(20);
    expect(out.min_price).toBe(0);
  });

  it('caps limit at 50', () => {
    expect(() => SearchShowsInput.parse({ limit: 51 })).toThrow();
  });

  it('rejects malformed dates', () => {
    expect(() => SearchShowsInput.parse({ date_from: '2026/09/12' })).toThrow();
  });
});

describe('GetShowInput', () => {
  it('accepts show_id alone', () => {
    GetShowInput.parse({ show_id: '550e8400-e29b-41d4-a716-446655440000' });
  });

  it('accepts slug alone', () => {
    GetShowInput.parse({ slug: 'a-good-show' });
  });

  it('rejects both at once', () => {
    expect(() =>
      GetShowInput.parse({
        show_id: '550e8400-e29b-41d4-a716-446655440000',
        slug: 'a-good-show',
      }),
    ).toThrow();
  });

  it('rejects neither', () => {
    expect(() => GetShowInput.parse({})).toThrow();
  });
});

describe('WhatsOnInput', () => {
  it('rejects unknown when value', () => {
    expect(() => WhatsOnInput.parse({ when: 'next_decade' })).toThrow();
  });

  it('accepts string near', () => {
    WhatsOnInput.parse({ when: 'tonight', near: 'London Bridge' });
  });

  it('accepts coordinate near', () => {
    WhatsOnInput.parse({
      when: 'this_weekend',
      near: { lat: 51.5, lng: -0.09 },
    });
  });
});

describe('RecommendShowsInput', () => {
  it('requires a vibe string', () => {
    expect(() => RecommendShowsInput.parse({})).toThrow();
  });

  it('defaults limit to 5', () => {
    const out = RecommendShowsInput.parse({ vibe: 'weird and political' });
    expect(out.limit).toBe(5);
  });
});

describe('GetVenueInput', () => {
  it('defaults include_shows to true', () => {
    const out = GetVenueInput.parse({ slug: 'bush-theatre' });
    expect(out.include_shows).toBe(true);
  });
});
