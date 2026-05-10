-- Initial migration. Mirrors schema.sql at v0.0.0.
-- Apply with: psql $DATABASE_URL -f migrations/0001_init.sql

\i ../schema.sql
