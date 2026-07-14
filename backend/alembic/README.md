# Alembic migrations

Phase 0 intentionally has no application schema or migration revisions. The Alembic
environment therefore treats `upgrade head` as a no-op. Phase 1 will add the database
connection, SQLAlchemy metadata, and the first schema migration together.

