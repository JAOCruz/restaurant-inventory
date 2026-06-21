#!/usr/bin/env bash
set -euo pipefail

# Initialize the local SQLite database for development.
# Usage: ./scripts/init_db.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
DB_FILE="${DATA_DIR}/inventory.db"

echo "Creating data directory at ${DATA_DIR}..."
mkdir -p "${DATA_DIR}"

echo "Initializing SQLite database at ${DB_FILE}..."
sqlite3 "${DB_FILE}" < "${PROJECT_ROOT}/sql/schema.sql"

echo "Seeding database..."
sqlite3 "${DB_FILE}" < "${PROJECT_ROOT}/sql/seed.sql"

echo "Database initialized successfully."
