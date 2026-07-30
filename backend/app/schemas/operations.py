from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.inventory import InventoryStatus
from app.schemas.project import ProjectRead
from app.schemas.task import TaskRead


CanonicalNonFiniteNumber = Literal["NaN", "Infinity", "-Infinity"]
OperationalNumber: TypeAlias = CanonicalNonFiniteNumber | float

ProjectLifecycleReasonCode = Literal[
    "PROJECT_STATUS_PLANNING",
    "PROJECT_STATUS_ACTIVE",
    "PROJECT_STATUS_ON_HOLD",
    "PROJECT_STATUS_COMPLETED",
    "PROJECT_STATUS_ARCHIVED",
    "PROJECT_STATUS_INVALID",
    "PROJECT_ARCHIVE_STATE_INCONSISTENT",
]
ProjectMaterialReasonCode = Literal[
    "PROJECT_MATERIALS_NOT_LISTED",
    "PROJECT_MATERIALS_SUFFICIENT",
    "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT",
    "PROJECT_MATERIAL_INVENTORY_MISSING",
    "PROJECT_MATERIAL_DATA_INVALID",
]
TaskWorkReasonCode = Literal[
    "TASK_INCOMPLETE",
    "TASK_COMPLETED",
]
InventoryStockReasonCode = Literal[
    "INVENTORY_ABOVE_MINIMUM",
    "INVENTORY_AT_OR_BELOW_MINIMUM",
    "INVENTORY_OUT_OF_STOCK",
    "INVENTORY_STOCK_DATA_INVALID",
]


class SourceRecordReference(ApiModel):
    record_type: Literal[
        "project",
        "project-material-requirement",
        "task",
        "inventory",
    ]
    record_id: str
    updated_at: datetime


class ProjectLifecycleEvidence(ApiModel):
    persisted_status: str
    archived_at: datetime | None


class ProjectLifecycleFact(ApiModel):
    fact_id: str
    fact_type: Literal["project.lifecycle"]
    subject_type: Literal["project"]
    subject_id: str
    state: Literal[
        "planning",
        "active",
        "on-hold",
        "completed",
        "archived",
        "invalid",
    ]
    reason_codes: list[ProjectLifecycleReasonCode]
    evidence: ProjectLifecycleEvidence
    source_records: list[SourceRecordReference]


class MaterialRequirementEvidence(ApiModel):
    inventory_item_id: str
    item_name: str | None
    unit: str | None
    required_quantity: OperationalNumber
    available_quantity: OperationalNumber | None
    shortage_quantity: float | None
    reason_code: ProjectMaterialReasonCode


class ProjectMaterialReadinessEvidence(ApiModel):
    requirements: list[MaterialRequirementEvidence]


class ProjectMaterialReadinessFact(ApiModel):
    fact_id: str
    fact_type: Literal["project.material-readiness"]
    subject_type: Literal["project"]
    subject_id: str
    state: Literal[
        "ready",
        "needs-materials",
        "not-applicable",
        "invalid",
    ]
    reason_codes: list[ProjectMaterialReasonCode]
    evidence: ProjectMaterialReadinessEvidence
    source_records: list[SourceRecordReference]


class TaskWorkStateEvidence(ApiModel):
    priority: str
    project_id: str | None


class TaskWorkStateFact(ApiModel):
    fact_id: str
    fact_type: Literal["task.work-state"]
    subject_type: Literal["task"]
    subject_id: str
    state: Literal["open", "completed"]
    reason_codes: list[TaskWorkReasonCode]
    evidence: TaskWorkStateEvidence
    source_records: list[SourceRecordReference]


class InventoryStockLevelEvidence(ApiModel):
    quantity: OperationalNumber
    minimum: OperationalNumber
    unit: str


class InventoryStockLevelFact(ApiModel):
    fact_id: str
    fact_type: Literal["inventory.stock-level"]
    subject_type: Literal["inventory"]
    subject_id: str
    state: Literal[
        "in-stock",
        "low-stock",
        "out-of-stock",
        "invalid",
    ]
    reason_codes: list[InventoryStockReasonCode]
    evidence: InventoryStockLevelEvidence
    source_records: list[SourceRecordReference]


OperationalFact: TypeAlias = Annotated[
    ProjectLifecycleFact
    | ProjectMaterialReadinessFact
    | TaskWorkStateFact
    | InventoryStockLevelFact,
    Field(discriminator="fact_type"),
]


class ProjectStatusSummary(ApiModel):
    planning: int = 0
    active: int = 0
    on_hold: int = 0
    completed: int = 0
    archived: int = 0
    invalid: int = 0


class ProjectMaterialReadinessSummary(ApiModel):
    ready: int = 0
    needs_materials: int = 0
    not_applicable: int = 0
    invalid: int = 0


class ProjectFactsSummary(ApiModel):
    by_status: ProjectStatusSummary = Field(
        default_factory=ProjectStatusSummary
    )
    material_readiness: ProjectMaterialReadinessSummary = Field(
        default_factory=ProjectMaterialReadinessSummary
    )


class TaskPrioritySummary(ApiModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class TaskFactsSummary(ApiModel):
    open: int = 0
    completed: int = 0
    by_priority: TaskPrioritySummary = Field(
        default_factory=TaskPrioritySummary
    )


class InventoryFactsSummary(ApiModel):
    total: int = 0
    in_stock: int = 0
    low_stock: int = 0
    out_of_stock: int = 0
    low_or_out_of_stock: int = 0
    invalid: int = 0


class OperationalFactsSummary(ApiModel):
    projects: ProjectFactsSummary = Field(
        default_factory=ProjectFactsSummary
    )
    tasks: TaskFactsSummary = Field(default_factory=TaskFactsSummary)
    inventory: InventoryFactsSummary = Field(
        default_factory=InventoryFactsSummary
    )


class NormalizedOperationalFactsResult(ApiModel):
    schema_version: Literal[1] = 1
    facts: list[OperationalFact]
    summary: OperationalFactsSummary = Field(
        default_factory=OperationalFactsSummary
    )


class InventoryOperationalFact(ApiModel):
    source_module: str
    record_id: str
    name: str
    current_quantity: float
    low_stock_threshold: float
    is_low: bool
    is_out_of_stock: bool
    status: InventoryStatus
    explanation: str


class OperationalFactsResponse(ApiModel):
    schema_version: Literal[1] = 1
    facts: list[OperationalFact]
    summary: OperationalFactsSummary = Field(
        default_factory=OperationalFactsSummary
    )
    active_projects: list[ProjectRead]
    incomplete_tasks: list[TaskRead]
    completed_tasks: list[TaskRead]
    task_priority_counts: dict[str, int]
    project_status_counts: dict[str, int]
    inventory: list[InventoryOperationalFact]
