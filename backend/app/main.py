from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.inventory import router as inventory_router
from app.api.inventory_migrations import router as inventory_migrations_router
from app.api.operations import router as operations_router
from app.api.projects import router as projects_router
from app.api.system import router as system_router
from app.api.task_migrations import router as task_migrations_router
from app.api.tasks import router as tasks_router
from app.core.database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="The Foreman",
    version="0.6.4",
    lifespan=lifespan,
)
app.include_router(system_router)
app.include_router(inventory_router)
app.include_router(inventory_migrations_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(task_migrations_router)
app.include_router(operations_router)
