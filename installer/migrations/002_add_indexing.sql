-- UNOTUSK DB Migration: 002_add_indexing.sql
-- Optimizes historical lookup indexes

CREATE INDEX IF NOT EXISTS idx_schema_migration_filename ON schema_migration_history(filename);
