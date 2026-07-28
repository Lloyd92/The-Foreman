from app.core.config import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    COMPANY_NAME,
)
from app.repositories.health import database_is_available
from app.schemas.system import HealthResponse, StatusResponse


def get_status() -> StatusResponse:
    return StatusResponse(
        application=APPLICATION_NAME,
        company=COMPANY_NAME,
        status="online",
        version=APPLICATION_VERSION,
    )


def get_health() -> HealthResponse:
    database_available = database_is_available()

    return HealthResponse(
        status="healthy" if database_available else "unhealthy",
        database="online" if database_available else "offline",
        reason=(
            "Application and database are available."
            if database_available
            else "Application is available but the database is offline."
        ),
    )
