import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories import project_migrations as migration_repository
from app.repositories import projects as project_repository
from app.schemas.project_migration import (
    BrowserProjectMigrationRequest,
    ProjectMigrationResponse,
)
from app.schemas.project import ProjectCreate
from app.services import projects as project_service


class ProjectMigrationConflictError(ValueError):
    pass


class ProjectMigrationGoneError(LookupError):
    pass


def migration_payload_hash(
    data: BrowserProjectMigrationRequest,
) -> str:
    payload = data.model_dump(
        mode="json",
        exclude={"source_record_id"},
    )
    canonical_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _existing_migration_response(
    session: Session,
    data: BrowserProjectMigrationRequest,
    payload_hash: str,
) -> ProjectMigrationResponse | None:
    migration = migration_repository.get_browser_migration(
        session,
        data.source_record_id,
    )

    if migration is None:
        return None

    if migration.payload_hash != payload_hash:
        raise ProjectMigrationConflictError(
            "This browser Project source ID was already migrated "
            "with different Project data."
        )

    if migration.project_id is None:
        raise ProjectMigrationGoneError(
            "The Project previously migrated from this browser "
            "source ID has been deleted and will not be recreated."
        )

    project = project_repository.get_project(
        session,
        migration.project_id,
    )

    if project is None:
        raise ProjectMigrationGoneError(
            "The migrated Project is no longer available and will "
            "not be recreated."
        )

    return ProjectMigrationResponse(
        **project_service.serialize_project(
            session,
            project,
        ).model_dump(),
        migration_status="already-migrated",
        source_record_id=data.source_record_id,
    )


def migrate_browser_project(
    session: Session,
    data: BrowserProjectMigrationRequest,
) -> ProjectMigrationResponse:
    payload_hash = migration_payload_hash(data)
    existing = _existing_migration_response(
        session,
        data,
        payload_hash,
    )

    if existing is not None:
        return existing

    project_data = data.model_dump(
        exclude={
            "source_record_id",
            "created_at",
            "updated_at",
        }
    )
    project = project_service.build_project(
        session,
        ProjectCreate.model_validate(project_data),
    )
    project.created_at = data.created_at
    project.updated_at = data.updated_at or data.created_at

    try:
        project_repository.add_project(session, project)
        migration_repository.add_browser_migration(
            session,
            source_record_id=data.source_record_id,
            project_id=project.id,
            payload_hash=payload_hash,
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        concurrent = _existing_migration_response(
            session,
            data,
            payload_hash,
        )

        if concurrent is not None:
            return concurrent

        raise
    except Exception:
        session.rollback()
        raise

    return ProjectMigrationResponse(
        **project_service.read_project(
            session,
            project.id,
        ).model_dump(),
        migration_status="migrated",
        source_record_id=data.source_record_id,
    )
