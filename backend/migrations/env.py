"""Alembic environment: migrations run against the app's configured DATABASE_URL."""

from alembic import context

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import get_settings
from app.db import Base, UTCDateTime, make_engine

target_metadata = Base.metadata


def render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Render app-specific column types as their plain SQLAlchemy equivalents so migrations
    don't import application code."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    return False


def run_offline() -> None:
    context.configure(url=get_settings().database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connectable = context.config.attributes.get("connection")
    if connectable is not None:
        context.configure(connection=connectable, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
