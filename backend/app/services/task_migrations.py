from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.default_space import DEFAULT_SPACE_ID
from app.models.task import Task
from app.repositories.task_migrations import (
    add_browser_migration,
    get_browser_migration,
)
from app.repositories.tasks import add_task, get_task
from app.schemas.task_migration import (
    BrowserTaskRecord,
    TaskMigrationError,
    TaskMigrationResponse,
)
from app.services.tasks import validate_project_reference


def get_source_record_id(
    raw_record: dict[str, Any],
) -> str | None:
    value = raw_record.get("id")

    if not isinstance(value, str) or not value.strip():
        return None

    return value


def migrate_browser_tasks(
    session: Session,
    raw_records: list[dict[str, Any]],
) -> TaskMigrationResponse:
    migrated = 0
    already_migrated = 0
    skipped = 0
    confirmed_source_ids: list[str] = []
    errors: list[TaskMigrationError] = []

    try:
        for index, raw_record in enumerate(raw_records):
            source_record_id = get_source_record_id(raw_record)

            try:
                record = BrowserTaskRecord.model_validate(raw_record)
            except ValidationError as error:
                skipped += 1
                errors.append(
                    TaskMigrationError(
                        index=index,
                        source_record_id=source_record_id,
                        reason=str(error),
                    )
                )
                continue

            migration = get_browser_migration(
                session,
                record.id,
            )

            if migration is not None:
                already_migrated += 1
                confirmed_source_ids.append(record.id)
                continue

            if get_task(session, record.id) is not None:
                skipped += 1
                errors.append(
                    TaskMigrationError(
                        index=index,
                        source_record_id=record.id,
                        reason=(
                            "A backend task already uses this ID. "
                            "The existing task was not overwritten."
                        ),
                    )
                )
                continue

            try:
                validate_project_reference(
                    session,
                    record.project_id,
                )
            except (LookupError, ValueError) as error:
                skipped += 1
                errors.append(
                    TaskMigrationError(
                        index=index,
                        source_record_id=record.id,
                        reason=str(error),
                    )
                )
                continue

            task = Task(
                id=record.id,
                space_id=DEFAULT_SPACE_ID,
                title=record.title,
                priority=record.priority,
                completed=record.completed,
                project_id=record.project_id,
                created_at=record.created_at,
                updated_at=record.created_at,
            )
            add_task(session, task)
            add_browser_migration(
                session,
                source_record_id=record.id,
                task_id=task.id,
                space_id=DEFAULT_SPACE_ID,
            )
            migrated += 1
            confirmed_source_ids.append(record.id)

        session.commit()
    except Exception:
        session.rollback()
        raise

    if errors and not (migrated or already_migrated):
        migration_status = "failed"
    elif errors:
        migration_status = "partial"
    else:
        migration_status = "success"

    return TaskMigrationResponse(
        status=migration_status,
        migrated=migrated,
        already_migrated=already_migrated,
        skipped=skipped,
        confirmed_source_ids=confirmed_source_ids,
        errors=errors,
        browser_data_retained=True,
    )
