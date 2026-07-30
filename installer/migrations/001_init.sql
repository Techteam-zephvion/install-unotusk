-- UNOTUSK DB Migration: 001_init.sql
-- Creates schema history table and baseline indices

CREATE TABLE IF NOT EXISTS schema_migration_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
