from app.schemas.common import ApiModel
from app.schemas.inventory import InventoryStatus
from app.schemas.project import ProjectRead
from app.schemas.task import TaskRead


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
    active_projects: list[ProjectRead]
    incomplete_tasks: list[TaskRead]
    completed_tasks: list[TaskRead]
    task_priority_counts: dict[str, int]
    project_status_counts: dict[str, int]
    inventory: list[InventoryOperationalFact]
