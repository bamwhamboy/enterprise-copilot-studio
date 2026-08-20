#!/usr/bin/env python
"""Waits for the database to accept connections before migrations run.

Render (and most managed Postgres providers) don't guarantee the
database instance is immediately ready to accept connections the
instant a dependent service's container starts -- this is most likely
on a database's very first boot, which is exactly when a fresh
deployment needs `alembic upgrade head` to succeed. Retries with a
short delay instead of letting the first connection attempt fail and
crash the container.
"""
import asyncio
import os
import sys

import asyncpg

MAX_ATTEMPTS = 30
DELAY_SECONDS = 2


async def wait_for_db() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("DATABASE_URL is not set -- skipping database readiness check.", file=sys.stderr)
        return

    # asyncpg.connect() expects a bare postgresql:// DSN. The app's own
    # DATABASE_URL uses the "+asyncpg" driver qualifier SQLAlchemy's
    # async engine needs, which asyncpg's own connect() doesn't parse.
    dsn = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            conn = await asyncpg.connect(dsn, timeout=5, ssl="require")
            await conn.close()
            print(f"Database is ready (attempt {attempt}/{MAX_ATTEMPTS}).")
            return
        except (OSError, asyncpg.PostgresError) as exc:
            print(
                f"Database not ready yet (attempt {attempt}/{MAX_ATTEMPTS}): {exc}",
                file=sys.stderr,
            )
            if attempt == MAX_ATTEMPTS:
                print(
                    f"Giving up after {MAX_ATTEMPTS} attempts "
                    f"({MAX_ATTEMPTS * DELAY_SECONDS}s) waiting for the database.",
                    file=sys.stderr,
                )
                sys.exit(1)
            await asyncio.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    asyncio.run(wait_for_db())
