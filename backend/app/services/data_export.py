from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import APPLICATION_NAME, APPLICATION_VERSION
from app.models.inventory import InventoryItem
from app.models.project import Project
from app.models.task import Task
from app.schemas.data_export import (
    ExportInventoryItem,
    ExportProject,
    ExportProjectMaterial,
    ExportRecordCounts,
    ExportTask,
    PortableDataExport,
)


def _canonical_text_key(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _stored_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        # Application timestamps are written in UTC. SQLite may return
        # DateTime(timezone=True) values without timezone information.
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _export_created_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "Export creation time must be timezone-aware."
        )

    return value.astimezone(timezone.utc)


def _project_materials(
    project: Project,
) -> list[ExportProjectMaterial]:
    requirements = sorted(
        project.material_requirements,
        key=lambda requirement: _canonical_text_key(
            requirement.inventory_item_id
        ),
    )
    return [
        ExportProjectMaterial(
            inventory_item_id=requirement.inventory_item_id,
            required_quantity=requirement.required_quantity,
            note=requirement.note,
        )
        for requirement in requirements
    ]


def _serialize_project(project: Project) -> ExportProject:
    return ExportProject(
        id=project.id,
        name=project.name,
        type=project.type,
        status=project.status,
        priority=project.priority,
        progress=project.progress,
        start_date=project.start_date,
        target_date=project.target_date,
        estimated_cost=project.estimated_cost,
        description=project.description,
        notes=project.notes,
        materials=_project_materials(project),
        created_at=_stored_utc(project.created_at),
        updated_at=_stored_utc(project.updated_at),
        archived_at=_stored_utc(project.archived_at),
    )


def _serialize_task(task: Task) -> ExportTask:
    return ExportTask(
        id=task.id,
        title=task.title,
        priority=task.priority,
        completed=task.completed,
        project_id=task.project_id,
        created_at=_stored_utc(task.created_at),
        updated_at=_stored_utc(task.updated_at),
    )


def _serialize_inventory_item(
    item: InventoryItem,
) -> ExportInventoryItem:
    return ExportInventoryItem(
        id=item.id,
        name=item.name,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        minimum=item.minimum,
        location=item.location,
        cost=item.cost,
        supplier=item.supplier,
        notes=item.notes,
        created_at=_stored_utc(item.created_at),
        updated_at=_stored_utc(item.updated_at),
    )


def _load_projects(session: Session) -> list[Project]:
    projects = list(
        session.scalars(
            select(Project).options(
                selectinload(Project.material_requirements)
            )
        )
    )
    return sorted(
        projects,
        key=lambda project: _canonical_text_key(project.id),
    )


def _load_tasks(session: Session) -> list[Task]:
    tasks = list(session.scalars(select(Task)))
    return sorted(
        tasks,
        key=lambda task: _canonical_text_key(task.id),
    )


def _load_inventory(session: Session) -> list[InventoryItem]:
    items = list(session.scalars(select(InventoryItem)))
    return sorted(
        items,
        key=lambda item: _canonical_text_key(item.id),
    )


def build_portable_data_export(
    source_session: Session,
    *,
    created_at: datetime | None = None,
) -> PortableDataExport:
    # Use a separate read session so pending or dirty objects in the
    # caller's session cannot leak into the committed-data export.
    with Session(
        bind=source_session.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    ) as export_session:
        projects = _load_projects(export_session)
        tasks = _load_tasks(export_session)
        inventory_items = _load_inventory(export_session)

        serialized_projects = [
            _serialize_project(project)
            for project in projects
        ]
        serialized_tasks = [
            _serialize_task(task)
            for task in tasks
        ]
        serialized_inventory = [
            _serialize_inventory_item(item)
            for item in inventory_items
        ]

    return PortableDataExport(
        application_name=APPLICATION_NAME,
        application_version=APPLICATION_VERSION,
        created_at=_export_created_at(created_at),
        record_counts=ExportRecordCounts(
            projects=len(serialized_projects),
            project_material_requirements=sum(
                len(project.materials)
                for project in serialized_projects
            ),
            tasks=len(serialized_tasks),
            inventory_items=len(serialized_inventory),
        ),
        projects=serialized_projects,
        tasks=serialized_tasks,
        inventory_items=serialized_inventory,
    )
