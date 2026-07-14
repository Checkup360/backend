#!/usr/bin/env sh
set -eu

# Tiny dispatcher used as the container ENTRYPOINT.
#
# Subcommands:
#   serve            Run alembic migrations, optionally seed a superuser, and
#                    start uvicorn (default).
#   migrate          Run alembic upgrade head and exit.
#   seed-superuser   Run the superuser/org seeding script and exit.
#   <anything else>  Exec it as-is (lets you do `docker run ... bash`, etc.).
#
# The seed-on-boot is opt-in: it only runs if both SUPERUSER_EMAIL and
# SUPERUSER_PASSWORD are set in the environment. It is idempotent and by
# default does not touch existing users (set SEED_OVERWRITE=true to force).

cmd="${1:-serve}"
shift || true

run_migrations() {
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
}

run_seed_if_configured() {
  if [ -n "${SUPERUSER_EMAIL:-}" ] && [ -n "${SUPERUSER_PASSWORD:-}" ]; then
    echo "[entrypoint] SUPERUSER_EMAIL set, running seed (overwrite=${SEED_OVERWRITE:-false})"
    python -m scripts.seed_superuser
  else
    echo "[entrypoint] SUPERUSER_EMAIL/PASSWORD not set, skipping seed"
  fi
}

case "$cmd" in
  serve)
    run_migrations
    run_seed_if_configured
    echo "[entrypoint] starting uvicorn on 0.0.0.0:${PORT:-8000}"
    exec uvicorn app.presentation.main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
    ;;
  migrate)
    exec alembic upgrade head
    ;;
  seed-superuser)
    echo "[entrypoint] seeding superuser"
    exec python -m scripts.seed_superuser "$@"
    ;;
  *)
    exec "$cmd" "$@"
    ;;
esac
