#!/bin/sh
# Runs on every container start, on Render or anywhere else this image
# is deployed. `alembic upgrade head` is idempotent -- if the database
# is already at head (e.g. on redeploys), this is a fast no-op; on a
# fresh database, it creates every table and seeds the 5 RBAC roles.
#
# This is what was missing for Render specifically: locally, migrations
# are run manually via `docker compose exec api alembic upgrade head`
# after the stack is up -- but there's no equivalent manual step
# available for a deployed Render service, so that step was simply
# never being run there. Baking it into the container's own startup
# means a fresh deployment initializes itself automatically, with no
# separate manual step to remember.
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."

# docker-compose.yml overrides the container command to add --reload
# for local development -- if a command was passed in (as compose
# does), run that instead of the production default below, so local
# hot-reload keeps working exactly as before. Only the migration step
# above is new behavior; the actual startup command is unchanged from
# whatever was already configured for each environment.
if [ "$#" -gt 0 ]; then
  exec "$@"
else
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
