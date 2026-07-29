#!/usr/bin/env bash
# UNOTUSK init-databases.sh — Creates separate databases on first boot
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  SELECT 'CREATE DATABASE auth  OWNER ${POSTGRES_USER}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth')\gexec
  SELECT 'CREATE DATABASE company OWNER ${POSTGRES_USER}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'company')\gexec
EOSQL
