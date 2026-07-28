from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_migration import ProjectMigration

SOURCE_BROWSER_LOCAL = "browser-local"


def get_browser_migration(
    session: Session,
    source_record_id: str,
) -> ProjectMigration | None:
    statement = select(ProjectMigration).where(
        ProjectMigration.source == SOURCE_BROWSER_LOCAL,
        ProjectMigration.source_record_id == source_record_id,
    )
    return session.scalar(statement)


def add_browser_migration(
    session: Session,
    *,
    source_record_id: str,
    project_id: str,
    payload_hash: str,
) -> ProjectMigration:
    migration = ProjectMigration(
        source=SOURCE_BROWSER_LOCAL,
        source_record_id=source_record_id,
        project_id=project_id,
        payload_hash=payload_hash,
    )
    session.add(migration)
    session.flush()
    return migration
