from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.space import Space
from app.models.project_material_requirement import (
    ProjectMaterialRequirement,
)
from app.repositories import inventory as inventory_repository
from app.repositories import projects as project_repository
from app.services.members import require_member
from app.schemas.project import (
    ProjectCreate,
    ProjectMaterialCreate,
    ProjectMaterialRead,
    ProjectMaterialUpdate,
    ProjectRead,
    ProjectUpdate,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def list_project_models(
    session: Session,
    active_space: Space,
    *,
    include_archived: bool = False,
) -> list[Project]:
    return project_repository.list_projects(
        session,
        active_space.id,
        include_archived=include_archived,
    )


def _inventory_names(
    session: Session,
    active_space: Space,
    projects: list[Project],
) -> dict[str, str]:
    inventory_ids = {
        requirement.inventory_item_id
        for project in projects
        for requirement in project.material_requirements
    }
    return inventory_repository.inventory_names_by_ids(
        session,
        active_space.id,
        inventory_ids,
    )


def _ordered_materials(
    project: Project,
    inventory_names: dict[str, str],
) -> list[ProjectMaterialRead]:
    def material_order(
        requirement: ProjectMaterialRequirement,
    ) -> tuple[int, str, str]:
        display_name = inventory_names.get(
            requirement.inventory_item_id
        )

        if display_name is not None:
            return (
                0,
                display_name.casefold(),
                requirement.inventory_item_id,
            )

        return (
            1,
            requirement.inventory_item_id.casefold(),
            requirement.inventory_item_id,
        )

    return [
        ProjectMaterialRead.model_validate(requirement)
        for requirement in sorted(
            project.material_requirements,
            key=material_order,
        )
    ]


def serialize_projects(
    session: Session,
    active_space: Space,
    projects: list[Project],
) -> list[ProjectRead]:
    inventory_names = _inventory_names(
        session,
        active_space,
        projects,
    )

    return [
        ProjectRead(
            id=project.id,
            name=project.name,
            type=project.type,
            status=project.status,
            priority=project.priority,
            progress=project.progress,
            start_date=project.start_date,
            target_date=project.target_date,
            responsible_member_id=project.responsible_member_id,
            estimated_cost=project.estimated_cost,
            description=project.description,
            notes=project.notes,
            materials=_ordered_materials(
                project,
                inventory_names,
            ),
            created_at=project.created_at,
            updated_at=project.updated_at,
            archived_at=project.archived_at,
        )
        for project in projects
    ]


def serialize_project(
    session: Session,
    active_space: Space,
    project: Project,
) -> ProjectRead:
    return serialize_projects(
        session,
        active_space,
        [project],
    )[0]


def list_projects(
    session: Session,
    active_space: Space,
    *,
    include_archived: bool = False,
) -> list[ProjectRead]:
    projects = list_project_models(
        session,
        active_space,
        include_archived=include_archived,
    )
    return serialize_projects(
        session,
        active_space,
        projects,
    )


def require_project(
    session: Session,
    active_space: Space,
    project_id: str,
) -> Project:
    project = project_repository.get_project(
        session,
        active_space.id,
        project_id,
    )

    if project is None:
        raise LookupError("Project not found.")

    return project


def read_project(
    session: Session,
    active_space: Space,
    project_id: str,
) -> ProjectRead:
    return serialize_project(
        session,
        active_space,
        require_project(
            session,
            active_space,
            project_id,
        ),
    )


def _require_editable(project: Project) -> None:
    if project.archived_at is not None:
        raise ValueError("Archived projects cannot be updated.")


def _require_inventory_item(
    session: Session,
    active_space: Space,
    inventory_item_id: str,
) -> None:
    if (
        inventory_repository.get_inventory_item(
            session,
            active_space.id,
            inventory_item_id,
        )
        is None
    ):
        raise ValueError("Inventory item not found.")


def build_project(
    session: Session,
    active_space: Space,
    data: ProjectCreate,
) -> Project:
    if data.responsible_member_id is not None:
        require_member(
            session,
            active_space,
            data.responsible_member_id,
        )

    for material in data.materials:
        _require_inventory_item(
            session,
            active_space,
            material.inventory_item_id,
        )

    project_data = data.model_dump(exclude={"materials"})
    project = Project(
        space_id=active_space.id,
        **project_data,
    )
    project.material_requirements = [
        ProjectMaterialRequirement(
            inventory_item_id=material.inventory_item_id,
            required_quantity=material.required_quantity,
            note=material.note,
        )
        for material in data.materials
    ]
    return project


def create_project(
    session: Session,
    active_space: Space,
    data: ProjectCreate,
) -> ProjectRead:
    project = build_project(
        session,
        active_space,
        data,
    )

    try:
        project_repository.add_project(session, project)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return read_project(
        session,
        active_space,
        project.id,
    )


def update_project(
    session: Session,
    active_space: Space,
    project_id: str,
    data: ProjectUpdate,
) -> ProjectRead:
    project = require_project(
        session,
        active_space,
        project_id,
    )
    _require_editable(project)
    changes = data.model_dump(exclude_unset=True)

    if (
        "responsible_member_id" in changes
        and changes["responsible_member_id"] is not None
    ):
        require_member(
            session,
            active_space,
            changes["responsible_member_id"],
        )

    for field, value in changes.items():
        setattr(project, field, value)

    project.updated_at = utc_now()

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return read_project(
        session,
        active_space,
        project.id,
    )


def add_material_requirement(
    session: Session,
    active_space: Space,
    project_id: str,
    data: ProjectMaterialCreate,
) -> ProjectRead:
    project = require_project(
        session,
        active_space,
        project_id,
    )
    _require_editable(project)
    _require_inventory_item(
        session,
        active_space,
        data.inventory_item_id,
    )

    if project_repository.get_material_requirement(
        session,
        project_id=project.id,
        inventory_item_id=data.inventory_item_id,
    ) is not None:
        raise ValueError(
            "That inventory item is already required by this project."
        )

    project.material_requirements.append(
        ProjectMaterialRequirement(
            inventory_item_id=data.inventory_item_id,
            required_quantity=data.required_quantity,
            note=data.note,
        )
    )
    project.updated_at = utc_now()

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return read_project(
        session,
        active_space,
        project.id,
    )


def update_material_requirement(
    session: Session,
    active_space: Space,
    project_id: str,
    inventory_item_id: str,
    data: ProjectMaterialUpdate,
) -> ProjectRead:
    project = require_project(
        session,
        active_space,
        project_id,
    )
    _require_editable(project)
    requirement = project_repository.get_material_requirement(
        session,
        project_id=project.id,
        inventory_item_id=inventory_item_id,
    )

    if requirement is None:
        raise LookupError("Project material requirement not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(requirement, field, value)

    project.updated_at = utc_now()

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return read_project(
        session,
        active_space,
        project.id,
    )


def remove_material_requirement(
    session: Session,
    active_space: Space,
    project_id: str,
    inventory_item_id: str,
) -> ProjectRead:
    project = require_project(
        session,
        active_space,
        project_id,
    )
    _require_editable(project)
    requirement = project_repository.get_material_requirement(
        session,
        project_id=project.id,
        inventory_item_id=inventory_item_id,
    )

    if requirement is None:
        raise LookupError("Project material requirement not found.")

    session.delete(requirement)
    project.updated_at = utc_now()

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return read_project(
        session,
        active_space,
        project.id,
    )


def delete_project(
    session: Session,
    active_space: Space,
    project_id: str,
) -> None:
    project = require_project(
        session,
        active_space,
        project_id,
    )

    try:
        project_repository.delete_project(session, project)
        session.commit()
    except Exception:
        session.rollback()
        raise


def archive_project(
    session: Session,
    active_space: Space,
    project_id: str,
) -> ProjectRead:
    project = require_project(
        session,
        active_space,
        project_id,
    )

    if project.archived_at is not None:
        return serialize_project(
            session,
            active_space,
            project,
        )

    archived_at = utc_now()
    project.status = "archived"
    project.archived_at = archived_at
    project.updated_at = archived_at

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return read_project(
        session,
        active_space,
        project.id,
    )
