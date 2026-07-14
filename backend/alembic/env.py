"""Alembic environment for the Phase 0 no-schema baseline."""

from logging.config import fileConfig

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# SQLAlchemy models are introduced in Phase 1. Keeping this explicit prevents an
# accidental empty autogeneration from being presented as an application schema.
target_metadata = None


def run_migrations_offline() -> None:
    """Render any future migration SQL without requiring a live connection."""
    context.configure(
        dialect_name="postgresql",
        literal_binds=True,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Treat upgrades as a no-op until Phase 1 introduces a database schema."""


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
