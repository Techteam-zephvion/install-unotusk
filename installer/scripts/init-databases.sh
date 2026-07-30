#!/bin/sh
# Runs once on Postgres container first boot to initialize logical databases
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    SELECT 'CREATE DATABASE auth'    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth')\gexec
    SELECT 'CREATE DATABASE company' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'company')\gexec
SQL
