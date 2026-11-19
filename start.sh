#!/bin/sh
# start.sh â€” Container / platform startup script for TeachWise AI
#
# 1. Seeds the CS201 synthetic academic dataset idempotently
#    (seed_academic.py is a no-op if already seeded).
# 2. Starts Gunicorn on 0.0.0.0:$PORT.
#
# IMPORTANT â€” SQLite persistence note:
#   On stateless platforms (Code Engine, Render free tier), the SQLite file
#   lives in the container filesystem and is lost on restart/redeploy.
#   Re-seeding runs automatically on each cold start, so the demo dataset
#   is always present. User-uploaded CSVs and generated content (lesson plans,
#   assessments, analysis sessions) are lost on restart.
#   For persistent storage, replace DATABASE_URL with a PostgreSQL URL.

set -e

echo "[TeachWise AI] Seeding CS201 academic dataset (idempotent)..."
python seed_academic.py

echo "[TeachWise AI] Starting Gunicorn on 0.0.0.0:${PORT:-8080}..."
exec gunicorn run:app \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
