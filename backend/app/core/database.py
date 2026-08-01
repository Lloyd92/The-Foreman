from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL
from app.core.maintenance import maintenance_coordinator
from app.core.schema_upgrades import apply_schema_upgrades
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


def initialize_database() -> None:
    import app.models  # noqa: F401

    with engine.begin() as connection:
        Base.metadata.create_all(bind=connection)
        apply_schema_upgrades(connection)


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
) -> Iterator[None]:
    with maintenance_coordinator.maintenance(
        timeout_seconds=timeout_seconds,
    ):
        engine.dispose()
        yield


def get_session() -> Generator[Session, None, None]:
    with database_access():
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()
