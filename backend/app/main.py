from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.data_export import router as data_export_router
from app.api.inventory import router as inventory_router
from app.api.inventory_migrations import router as inventory_migrations_router
from app.api.members import router as members_router
from app.api.organization_relationships import (
    router as organization_relationships_router,
)
from app.api.operations import router as operations_router
from app.api.organizations import router as organizations_router
from app.api.people import router as people_router
from app.api.project_migrations import router as project_migrations_router
from app.api.projects import router as projects_router
from app.api.recovery import router as recovery_router
from app.api.spaces import router as spaces_router
from app.api.system import router as system_router
from app.api.task_migrations import router as task_migrations_router
from app.api.tasks import router as tasks_router
from app.core.database import initialize_database
from app.core.maintenance import DatabaseMaintenanceActive


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="The Foreman",
    version="0.7.3",
    lifespan=lifespan,
)


@app.exception_handler(DatabaseMaintenanceActive)
async def database_maintenance_active_handler(
    _: Request,
    __: DatabaseMaintenanceActive,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": {
                "code": "DATABASE_MAINTENANCE_ACTIVE",
                "message": (
                    "The Foreman is temporarily unavailable while "
                    "database maintenance is in progress."
                ),
            }
        },
        headers={
            "Cache-Control": "no-store",
            "Retry-After": "1",
        },
    )


app.include_router(system_router)
app.include_router(spaces_router)
app.include_router(people_router)
app.include_router(organizations_router)
app.include_router(members_router)
app.include_router(organization_relationships_router)
app.include_router(data_export_router)
app.include_router(inventory_router)
app.include_router(inventory_migrations_router)
app.include_router(projects_router)
app.include_router(project_migrations_router)
app.include_router(tasks_router)
app.include_router(task_migrations_router)
app.include_router(operations_router)
app.include_router(recovery_router)
