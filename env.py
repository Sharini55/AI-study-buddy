"""
alembic/env.py
--------------
Alembic runtime environment for SunDevil AI.

Key responsibilities:
  1. Read DATABASE_URL from the environment (never hardcoded).
  2. Import our SQLAlchemy Base so Alembic can auto-detect schema changes.
  3. Support both "offline" mode (generates SQL scripts) and
     "online" mode (connects live and runs migrations).
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Make sure `utils/` is importable when Alembic runs from the repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import our models' Base so Alembic sees the full schema for autogenerate.
# If you add new SQLAlchemy models in the future, import them here too so
# Alembic picks them up automatically.
from utils.persistence import Base  # noqa: E402  (import after sys.path patch)

# ---------------------------------------------------------------------------
# Alembic Config object (wraps alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

# Inject the DATABASE_URL from the environment.
# On local dev:  export DATABASE_URL="postgresql://user:pass@localhost/sundevil"
# On Azure:      set as an App Service environment variable / Key Vault ref
# Falls back to SQLite for local smoke-testing only — never use SQLite in prod.
database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite:///sundevil_ai.db",   # local fallback — override in prod
)

# Heroku/Render historically return postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

config.set_main_option("sqlalchemy.url", database_url)

# Wire up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the MetaData object Alembic uses for --autogenerate comparisons.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — produces a .sql script without connecting to the database.
# Useful for DBAs who need to review changes before applying them.
# Usage:  alembic upgrade head --sql > migration.sql
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render column-level CHECK constraints so they appear in scripts
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connects to the live database and applies migrations directly.
# Usage:  alembic upgrade head
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # NullPool is safest for migration scripts
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # render_as_batch=True enables ALTER TABLE support for SQLite.
            # Postgres doesn't need it but it's harmless to keep for local dev.
            render_as_batch=True,
            compare_type=True,     # detect column type changes
            compare_server_default=True,  # detect default value changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
