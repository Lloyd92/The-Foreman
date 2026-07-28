from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL
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


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
