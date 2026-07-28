from sqlalchemy.orm import Session

from app.repositories.projects import project_status_counts
from app.repositories.tasks import task_priority_counts
from app.schemas.operations import (
    InventoryOperationalFact,
    OperationalFactsResponse,
)
from app.services.inventory import list_inventory
from app.services.projects import list_projects
from app.services.tasks import list_tasks


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
