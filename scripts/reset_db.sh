#!/usr/bin/env bash
# Reset SQLite DB and WAL files. Restart the server to re-seed.

set -e
cd "$(dirname "$0")/.."

rm -f data/carrier.db data/carrier.db-wal data/carrier.db-shm
echo "✅ DB reset. Restart the server (uv run uvicorn app.main:app --reload) to re-seed."
