#!/usr/bin/env node
/**
 * Tiny migration runner. Walks `migrations/` in order, tracks state in a
 * `_migrations` table. Idempotent — safe to re-run.
 *
 * Usage:
 *   DATABASE_URL=postgres://... node scripts/migrate.mjs
 */

import { readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import postgres from 'postgres';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MIG_DIR = join(__dirname, '..', 'migrations');

const url = process.env.DATABASE_URL;
if (!url) {
  console.error('DATABASE_URL is required');
  process.exit(1);
}

const sql = postgres(url, { max: 1 });

async function ensureTable() {
  await sql`
    CREATE TABLE IF NOT EXISTS _migrations (
      name TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `;
}

async function applied() {
  const rows = await sql`SELECT name FROM _migrations`;
  return new Set(rows.map((r) => r.name));
}

async function run() {
  await ensureTable();
  const done = await applied();
  const files = (await readdir(MIG_DIR))
    .filter((f) => f.endsWith('.sql'))
    .sort();

  for (const file of files) {
    if (done.has(file)) {
      console.log(`✓ ${file} (already applied)`);
      continue;
    }
    const body = await readFile(join(MIG_DIR, file), 'utf8');
    console.log(`→ applying ${file}`);
    await sql.begin(async (tx) => {
      await tx.unsafe(body);
      await tx`INSERT INTO _migrations (name) VALUES (${file})`;
    });
    console.log(`✓ ${file}`);
  }

  console.log('all migrations applied');
  await sql.end();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
