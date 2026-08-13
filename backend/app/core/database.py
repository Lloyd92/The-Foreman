from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL
from app.core.maintenance import (
    DatabaseMaintenanceCoordinator,
    maintenance_coordinator,
)
from app.core.schema_upgrades import (
    SPACE_SCOPED_TABLE_UPGRADES,
    apply_schema_upgrades,
    assert_supported_database_version,
)
from app.models.base import Base

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# SQLite tables introduced by a versioned schema upgrade must not be
# pre-created by Base.metadata.create_all(). Existing migration/recovery
# state must be validated before a newer schema version mutates the database.
SQLITE_DEFERRED_UPGRADE_TABLES = frozenset({
    "calendar_entries",
    "calendar_series",
    "calendar_series_exclusions",
    "calendar_settings",
    "care_plans",
    "money_accounts",
    "money_budgets",
    "money_categories",
    "money_obligations",
    "money_relationships",
    "money_transactions",
    "tool_maintenance_records",
    "tools",
    "work_calendar_relationships",
    "work_dependencies",
    "work_tool_requirements",
})


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(
    database_connection,
    _,
) -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    cursor = database_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def prepare_database_schema(connection) -> None:
    import app.models  # noqa: F401

    if connection.in_transaction():
        raise RuntimeError(
            "Schema preparation requires a connection without an active "
            "transaction."
        )

    assert_supported_database_version(connection)
    connection.rollback()

    with connection.begin():
        existing_tables = set(inspect(connection).get_table_names())
        interrupted_tables = {
            upgrade.table_name
            for upgrade in SPACE_SCOPED_TABLE_UPGRADES
            if upgrade.table_name not in existing_tables
            and (
                upgrade.shadow_name in existing_tables
                or upgrade.ready_name in existing_tables
            )
        }
        tables_to_create = [
            table
            for table in Base.metadata.sorted_tables
            if table.name not in interrupted_tables
            and (
                connection.dialect.name != "sqlite"
                or table.name not in SQLITE_DEFERRED_UPGRADE_TABLES
            )
        ]
        Base.metadata.create_all(
            bind=connection,
            tables=tables_to_create,
        )

    apply_schema_upgrades(connection)


def initialize_database() -> None:
    with engine.connect() as connection:
        prepare_database_schema(connection)


@contextmanager
def database_access() -> Iterator[None]:
    with maintenance_coordinator.database_access():
        yield


def get_database_access() -> Generator[None, None, None]:
    with database_access():
        yield


@contextmanager
def database_maintenance(
    *,
    timeout_seconds: float | None = None,
) -> Iterator[DatabaseMaintenanceCoordinator]:
    with maintenance_coordinator.maintenance(
        timeout_seconds=timeout_seconds,
    ) as coordinator:
        engine.dispose()
        yield coordinator


def get_session() -> Generator[Session, None, None]:
    with database_access():
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()
