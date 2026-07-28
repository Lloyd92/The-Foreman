from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task_migration import TaskMigration

SOURCE_BROWSER_LOCAL = "browser-local"


def get_browser_migration(
    session: Session,
    source_record_id: str,
) -> TaskMigration | None:
    statement = select(TaskMigration).where(
        TaskMigration.source == SOURCE_BROWSER_LOCAL,
        TaskMigration.source_record_id == source_record_id,
    )
    return session.scalar(statement)


def add_browser_migration(
    session: Session,
    *,
    source_record_id: str,
    task_id: str,
) -> TaskMigration:
    migration = TaskMigration(
        source=SOURCE_BROWSER_LOCAL,
        source_record_id=source_record_id,
        task_id=task_id,
    )
    session.add(migration)
    session.flush()
    return migration
