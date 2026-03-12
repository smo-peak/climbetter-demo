#!/bin/bash
set -euo pipefail

# This script runs automatically on first container start
# via /docker-entrypoint-initdb.d/

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create keycloak database and user
    CREATE DATABASE keycloak;
    CREATE USER keycloak WITH ENCRYPTED PASSWORD '${KEYCLOAK_DB_PASSWORD}';
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
    ALTER DATABASE keycloak OWNER TO keycloak;

    -- Enable TimescaleDB on main database
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EOSQL

# Enable TimescaleDB on keycloak database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "keycloak" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EOSQL

echo "=== ClimBetter databases initialized ==="
