from fastapi import APIRouter, HTTPException, status

from app.schemas.system import HealthResponse, StatusResponse
from app.services.system import get_health, get_status

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/status", response_model=StatusResponse)
def status_endpoint() -> StatusResponse:
    return get_status()


@router.get("/health", response_model=HealthResponse)
def health_endpoint() -> HealthResponse:
    health = get_health()

    if health.status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health.reason,
        )

    return health
