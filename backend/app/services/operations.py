from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import isfinite

from sqlalchemy.orm import Session

from app.repositories import inventory as inventory_repository
from app.repositories import projects as project_repository
from app.repositories import tasks as task_repository
from app.repositories.projects import project_status_counts
from app.repositories.tasks import task_priority_counts
from app.schemas.operations import (
    InventoryFactsSummary,
    InventoryOperationalFact,
    InventoryStockLevelEvidence,
    InventoryStockLevelFact,
    MaterialRequirementEvidence,
    NormalizedOperationalFactsResult,
    OperationalFact,
    OperationalFactsResponse,
    OperationalFactsSummary,
    ProjectFactsSummary,
    ProjectLifecycleEvidence,
    ProjectLifecycleFact,
    ProjectMaterialReadinessEvidence,
    ProjectMaterialReadinessFact,
    ProjectMaterialReadinessSummary,
    ProjectStatusSummary,
    SourceRecordReference,
    TaskFactsSummary,
    TaskPrioritySummary,
    TaskWorkStateEvidence,
    TaskWorkStateFact,
)
from app.services.inventory import list_inventory
from app.services.projects import list_projects
from app.services.tasks import list_tasks


@dataclass(frozen=True)
class MaterialRequirementSnapshot:
    inventory_item_id: str
    required_quantity: float


@dataclass(frozen=True)
class ProjectSnapshot:
    id: str
    status: str
    updated_at: datetime
    archived_at: datetime | None
    material_requirements: tuple[MaterialRequirementSnapshot, ...] = ()


@dataclass(frozen=True)
class TaskSnapshot:
    id: str
    priority: str
    completed: bool
    project_id: str | None
    updated_at: datetime


@dataclass(frozen=True)
class InventorySnapshot:
    id: str
    name: str
    quantity: float
    minimum: float
    unit: str
    updated_at: datetime


@dataclass(frozen=True)
class OperationalSnapshot:
    projects: tuple[ProjectSnapshot, ...] = ()
    tasks: tuple[TaskSnapshot, ...] = ()
    inventory: tuple[InventorySnapshot, ...] = ()


FACT_TYPE_ORDER = {
    "project.lifecycle": 0,
    "project.material-readiness": 1,
    "task.work-state": 2,
    "inventory.stock-level": 3,
}
SOURCE_RECORD_ORDER = {
    "project": 0,
    "project-material-requirement": 1,
    "task": 2,
    "inventory": 3,
}
PROJECT_LIFECYCLE_REASONS = {
    "planning": "PROJECT_STATUS_PLANNING",
    "active": "PROJECT_STATUS_ACTIVE",
    "on-hold": "PROJECT_STATUS_ON_HOLD",
    "completed": "PROJECT_STATUS_COMPLETED",
    "archived": "PROJECT_STATUS_ARCHIVED",
}
PROJECT_LIFECYCLE_REASON_ORDER = {
    "PROJECT_STATUS_PLANNING": 0,
    "PROJECT_STATUS_ACTIVE": 1,
    "PROJECT_STATUS_ON_HOLD": 2,
    "PROJECT_STATUS_COMPLETED": 3,
    "PROJECT_STATUS_ARCHIVED": 4,
    "PROJECT_STATUS_INVALID": 5,
    "PROJECT_ARCHIVE_STATE_INCONSISTENT": 6,
}
PROJECT_MATERIAL_REASON_ORDER = {
    "PROJECT_MATERIALS_NOT_LISTED": 0,
    "PROJECT_MATERIALS_SUFFICIENT": 1,
    "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT": 2,
    "PROJECT_MATERIAL_INVENTORY_MISSING": 3,
    "PROJECT_MATERIAL_DATA_INVALID": 4,
}


def _normalized_id(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _canonical_source_records(
    source_records: list[SourceRecordReference],
) -> list[SourceRecordReference]:
    unique: dict[tuple[str, str], SourceRecordReference] = {}

    for source_record in source_records:
        key = (source_record.record_type, source_record.record_id)
        unique[key] = source_record

    return sorted(
        unique.values(),
        key=lambda source_record: (
            SOURCE_RECORD_ORDER[source_record.record_type],
            *_normalized_id(source_record.record_id),
        ),
    )


def _canonical_non_finite(value: float) -> float | str:
    if value != value:
        return "NaN"
    if value == float("inf"):
        return "Infinity"
    if value == float("-inf"):
        return "-Infinity"
    return value


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
    )


def _valid_inventory_numbers(
    quantity: object,
    minimum: object,
) -> bool:
    return (
        _is_finite_number(quantity)
        and _is_finite_number(minimum)
        and quantity >= 0
        and minimum >= 0
    )


def _valid_required_quantity(value: object) -> bool:
    return _is_finite_number(value) and value > 0


def _shortage(
    required_quantity: float,
    available_quantity: float,
) -> float:
    return float(
        Decimal(str(required_quantity))
        - Decimal(str(available_quantity))
    )


def _read_operational_snapshot(session: Session) -> OperationalSnapshot:
    projects = project_repository.list_projects(
        session,
        include_archived=True,
    )
    tasks = task_repository.list_tasks(session)
    inventory = inventory_repository.list_inventory(session)

    return OperationalSnapshot(
        projects=tuple(
            ProjectSnapshot(
                id=project.id,
                status=project.status,
                updated_at=project.updated_at,
                archived_at=project.archived_at,
                material_requirements=tuple(
                    MaterialRequirementSnapshot(
                        inventory_item_id=requirement.inventory_item_id,
                        required_quantity=requirement.required_quantity,
                    )
                    for requirement in project.material_requirements
                ),
            )
            for project in projects
        ),
        tasks=tuple(
            TaskSnapshot(
                id=task.id,
                priority=task.priority,
                completed=task.completed,
                project_id=task.project_id,
                updated_at=task.updated_at,
            )
            for task in tasks
        ),
        inventory=tuple(
            InventorySnapshot(
                id=item.id,
                name=item.name,
                quantity=item.quantity,
                minimum=item.minimum,
                unit=item.unit,
                updated_at=item.updated_at,
            )
            for item in inventory
        ),
    )


def load_operational_snapshot(session: Session) -> OperationalSnapshot:
    if session.in_transaction():
        return _read_operational_snapshot(session)

    transaction = session.begin()

    try:
        snapshot = _read_operational_snapshot(session)
    except Exception:
        transaction.rollback()
        raise

    transaction.rollback()
    return snapshot


def _project_source(project: ProjectSnapshot) -> SourceRecordReference:
    return SourceRecordReference(
        record_type="project",
        record_id=project.id,
        updated_at=project.updated_at,
    )


def _derive_project_lifecycle_fact(
    project: ProjectSnapshot,
) -> ProjectLifecycleFact:
    status_is_supported = project.status in PROJECT_LIFECYCLE_REASONS
    archive_is_consistent = (
        (project.status == "archived")
        == (project.archived_at is not None)
    )

    if not status_is_supported:
        state = "invalid"
        reason_codes = ["PROJECT_STATUS_INVALID"]
    elif not archive_is_consistent:
        state = "invalid"
        reason_codes = [
            "PROJECT_STATUS_INVALID",
            "PROJECT_ARCHIVE_STATE_INCONSISTENT",
        ]
    else:
        state = project.status
        reason_codes = [PROJECT_LIFECYCLE_REASONS[project.status]]

    return ProjectLifecycleFact(
        fact_id=f"project/{project.id}/lifecycle",
        fact_type="project.lifecycle",
        subject_type="project",
        subject_id=project.id,
        state=state,
        reason_codes=sorted(
            reason_codes,
            key=PROJECT_LIFECYCLE_REASON_ORDER.__getitem__,
        ),
        evidence=ProjectLifecycleEvidence(
            persisted_status=project.status,
            archived_at=project.archived_at,
        ),
        source_records=[_project_source(project)],
    )


def _material_evidence(
    requirement: MaterialRequirementSnapshot,
    inventory_item: InventorySnapshot | None,
) -> MaterialRequirementEvidence:
    required_is_valid = _valid_required_quantity(
        requirement.required_quantity
    )
    inventory_is_valid = (
        inventory_item is None
        or _valid_inventory_numbers(
            inventory_item.quantity,
            inventory_item.minimum,
        )
    )

    if not required_is_valid or not inventory_is_valid:
        return MaterialRequirementEvidence(
            inventory_item_id=requirement.inventory_item_id,
            item_name=inventory_item.name if inventory_item else None,
            unit=inventory_item.unit if inventory_item else None,
            required_quantity=_canonical_non_finite(
                requirement.required_quantity
            ),
            available_quantity=(
                _canonical_non_finite(inventory_item.quantity)
                if inventory_item
                else None
            ),
            shortage_quantity=None,
            reason_code="PROJECT_MATERIAL_DATA_INVALID",
        )

    if inventory_item is None:
        return MaterialRequirementEvidence(
            inventory_item_id=requirement.inventory_item_id,
            item_name=None,
            unit=None,
            required_quantity=requirement.required_quantity,
            available_quantity=None,
            shortage_quantity=None,
            reason_code="PROJECT_MATERIAL_INVENTORY_MISSING",
        )

    if inventory_item.quantity < requirement.required_quantity:
        return MaterialRequirementEvidence(
            inventory_item_id=requirement.inventory_item_id,
            item_name=inventory_item.name,
            unit=inventory_item.unit,
            required_quantity=requirement.required_quantity,
            available_quantity=inventory_item.quantity,
            shortage_quantity=_shortage(
                requirement.required_quantity,
                inventory_item.quantity,
            ),
            reason_code="PROJECT_MATERIAL_QUANTITY_INSUFFICIENT",
        )

    return MaterialRequirementEvidence(
        inventory_item_id=requirement.inventory_item_id,
        item_name=inventory_item.name,
        unit=inventory_item.unit,
        required_quantity=requirement.required_quantity,
        available_quantity=inventory_item.quantity,
        shortage_quantity=0,
        reason_code="PROJECT_MATERIALS_SUFFICIENT",
    )


def _derive_material_readiness_fact(
    project: ProjectSnapshot,
    inventory_by_id: dict[str, InventorySnapshot],
) -> ProjectMaterialReadinessFact:
    requirements = sorted(
        project.material_requirements,
        key=lambda requirement: _normalized_id(
            requirement.inventory_item_id
        ),
    )
    evidence = [
        _material_evidence(
            requirement,
            inventory_by_id.get(requirement.inventory_item_id),
        )
        for requirement in requirements
    ]

    if not evidence:
        state = "not-applicable"
        reason_codes = ["PROJECT_MATERIALS_NOT_LISTED"]
    else:
        evidence_reason_codes = {
            requirement.reason_code
            for requirement in evidence
        }

        if "PROJECT_MATERIAL_DATA_INVALID" in evidence_reason_codes:
            state = "invalid"
            reason_codes = ["PROJECT_MATERIAL_DATA_INVALID"]
        elif (
            "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"
            in evidence_reason_codes
            or "PROJECT_MATERIAL_INVENTORY_MISSING"
            in evidence_reason_codes
        ):
            state = "needs-materials"
            reason_codes = sorted(
                evidence_reason_codes
                - {"PROJECT_MATERIALS_SUFFICIENT"},
                key=PROJECT_MATERIAL_REASON_ORDER.__getitem__,
            )
        else:
            state = "ready"
            reason_codes = ["PROJECT_MATERIALS_SUFFICIENT"]

    source_records = [_project_source(project)]

    for requirement in requirements:
        source_records.append(
            SourceRecordReference(
                record_type="project-material-requirement",
                record_id=(
                    f"{project.id}/{requirement.inventory_item_id}"
                ),
                updated_at=project.updated_at,
            )
        )
        inventory_item = inventory_by_id.get(
            requirement.inventory_item_id
        )

        if inventory_item is not None:
            source_records.append(
                SourceRecordReference(
                    record_type="inventory",
                    record_id=inventory_item.id,
                    updated_at=inventory_item.updated_at,
                )
            )

    return ProjectMaterialReadinessFact(
        fact_id=f"project/{project.id}/material-readiness",
        fact_type="project.material-readiness",
        subject_type="project",
        subject_id=project.id,
        state=state,
        reason_codes=reason_codes,
        evidence=ProjectMaterialReadinessEvidence(
            requirements=evidence
        ),
        source_records=_canonical_source_records(source_records),
    )


def _derive_task_fact(task: TaskSnapshot) -> TaskWorkStateFact:
    state = "completed" if task.completed else "open"
    reason_code = "TASK_COMPLETED" if task.completed else "TASK_INCOMPLETE"
    return TaskWorkStateFact(
        fact_id=f"task/{task.id}/work-state",
        fact_type="task.work-state",
        subject_type="task",
        subject_id=task.id,
        state=state,
        reason_codes=[reason_code],
        evidence=TaskWorkStateEvidence(
            priority=task.priority,
            project_id=task.project_id,
        ),
        source_records=[
            SourceRecordReference(
                record_type="task",
                record_id=task.id,
                updated_at=task.updated_at,
            )
        ],
    )


def _derive_inventory_fact(
    inventory_item: InventorySnapshot,
) -> InventoryStockLevelFact:
    if not _valid_inventory_numbers(
        inventory_item.quantity,
        inventory_item.minimum,
    ):
        state = "invalid"
        reason_code = "INVENTORY_STOCK_DATA_INVALID"
    elif inventory_item.quantity == 0:
        state = "out-of-stock"
        reason_code = "INVENTORY_OUT_OF_STOCK"
    elif inventory_item.quantity <= inventory_item.minimum:
        state = "low-stock"
        reason_code = "INVENTORY_AT_OR_BELOW_MINIMUM"
    else:
        state = "in-stock"
        reason_code = "INVENTORY_ABOVE_MINIMUM"

    return InventoryStockLevelFact(
        fact_id=f"inventory/{inventory_item.id}/stock-level",
        fact_type="inventory.stock-level",
        subject_type="inventory",
        subject_id=inventory_item.id,
        state=state,
        reason_codes=[reason_code],
        evidence=InventoryStockLevelEvidence(
            quantity=_canonical_non_finite(inventory_item.quantity),
            minimum=_canonical_non_finite(inventory_item.minimum),
            unit=inventory_item.unit,
        ),
        source_records=[
            SourceRecordReference(
                record_type="inventory",
                record_id=inventory_item.id,
                updated_at=inventory_item.updated_at,
            )
        ],
    )


def _derive_summary(
    facts: list[OperationalFact],
) -> OperationalFactsSummary:
    project_status = {
        "planning": 0,
        "active": 0,
        "on-hold": 0,
        "completed": 0,
        "archived": 0,
        "invalid": 0,
    }
    material_readiness = {
        "ready": 0,
        "needs-materials": 0,
        "not-applicable": 0,
        "invalid": 0,
    }
    task_states = {"open": 0, "completed": 0}
    task_priorities = {"high": 0, "medium": 0, "low": 0}
    inventory_states = {
        "in-stock": 0,
        "low-stock": 0,
        "out-of-stock": 0,
        "invalid": 0,
    }

    for fact in facts:
        if fact.fact_type == "project.lifecycle":
            project_status[fact.state] += 1
        elif fact.fact_type == "project.material-readiness":
            material_readiness[fact.state] += 1
        elif fact.fact_type == "task.work-state":
            task_states[fact.state] += 1

            if fact.evidence.priority in task_priorities:
                task_priorities[fact.evidence.priority] += 1
        elif fact.fact_type == "inventory.stock-level":
            inventory_states[fact.state] += 1

    low_or_out = (
        inventory_states["low-stock"]
        + inventory_states["out-of-stock"]
    )
    return OperationalFactsSummary(
        projects=ProjectFactsSummary(
            by_status=ProjectStatusSummary(
                planning=project_status["planning"],
                active=project_status["active"],
                on_hold=project_status["on-hold"],
                completed=project_status["completed"],
                archived=project_status["archived"],
                invalid=project_status["invalid"],
            ),
            material_readiness=ProjectMaterialReadinessSummary(
                ready=material_readiness["ready"],
                needs_materials=material_readiness["needs-materials"],
                not_applicable=material_readiness["not-applicable"],
                invalid=material_readiness["invalid"],
            ),
        ),
        tasks=TaskFactsSummary(
            open=task_states["open"],
            completed=task_states["completed"],
            by_priority=TaskPrioritySummary(**task_priorities),
        ),
        inventory=InventoryFactsSummary(
            total=sum(inventory_states.values()),
            in_stock=inventory_states["in-stock"],
            low_stock=inventory_states["low-stock"],
            out_of_stock=inventory_states["out-of-stock"],
            low_or_out_of_stock=low_or_out,
            invalid=inventory_states["invalid"],
        ),
    )


def derive_operational_facts(
    snapshot: OperationalSnapshot,
) -> NormalizedOperationalFactsResult:
    inventory_by_id: dict[str, InventorySnapshot] = {}

    for inventory_item in snapshot.inventory:
        if inventory_item.id in inventory_by_id:
            raise ValueError(
                f"Duplicate Inventory source ID: {inventory_item.id}"
            )
        inventory_by_id[inventory_item.id] = inventory_item

    facts: list[OperationalFact] = []

    for project in snapshot.projects:
        facts.append(_derive_project_lifecycle_fact(project))

        if project.status in {"planning", "active"}:
            facts.append(
                _derive_material_readiness_fact(
                    project,
                    inventory_by_id,
                )
            )

    facts.extend(_derive_task_fact(task) for task in snapshot.tasks)
    facts.extend(
        _derive_inventory_fact(inventory_item)
        for inventory_item in snapshot.inventory
    )
    facts.sort(
        key=lambda fact: (
            FACT_TYPE_ORDER[fact.fact_type],
            *_normalized_id(fact.subject_id),
        )
    )
    fact_ids = [fact.fact_id for fact in facts]

    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("Duplicate operational fact ID.")

    return NormalizedOperationalFactsResult(
        facts=facts,
        summary=_derive_summary(facts),
    )


def calculate_normalized_operational_facts(
    session: Session,
) -> NormalizedOperationalFactsResult:
    return derive_operational_facts(
        load_operational_snapshot(session)
    )


def get_operational_facts(
    session: Session,
) -> OperationalFactsResponse:
    projects = list_projects(session)
    tasks = list_tasks(session)
    inventory = list_inventory(session)

    return OperationalFactsResponse(
        active_projects=[
            project
            for project in projects
            if project.status == "active"
        ],
        incomplete_tasks=[
            task
            for task in tasks
            if not task.completed
        ],
        completed_tasks=[
            task
            for task in tasks
            if task.completed
        ],
        task_priority_counts=task_priority_counts(session),
        project_status_counts=project_status_counts(session),
        inventory=[
            InventoryOperationalFact(
                source_module="inventory",
                record_id=item.id,
                name=item.name,
                current_quantity=item.quantity,
                low_stock_threshold=item.minimum,
                is_low=item.is_low,
                is_out_of_stock=item.is_out_of_stock,
                status=item.status,
                explanation=item.explanation,
            )
            for item in inventory
        ],
    )
