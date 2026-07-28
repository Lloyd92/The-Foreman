from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.operations import OperationalFactsResponse
from app.services.operations import get_operational_facts

router = APIRouter(prefix="/api", tags=["operations"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get(
    "/operational-facts",
    response_model=OperationalFactsResponse,
)
def operational_facts(
    session: SessionDependency,
) -> OperationalFactsResponse:
    return get_operational_facts(session)
