import { NextResponse, type NextRequest } from 'next/server';
import { SearchVenuesInput } from '@platform/shared';
import { searchVenues } from '@/lib/queries/venues';
import { paramsFromUrl, parseInput } from '@/lib/api';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const parsed = await parseInput(
    SearchVenuesInput,
    paramsFromUrl(new URL(req.url)),
  );
  if (!parsed.ok) return parsed.response;
  const result = await searchVenues(parsed.data);
  return NextResponse.json(result);
}
