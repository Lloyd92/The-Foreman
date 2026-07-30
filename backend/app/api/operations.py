import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.operations import OperationalFactsResponse
from app.services.operations import get_operational_facts

router = APIRouter(prefix="/api", tags=["operations"])
SessionDependency = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)


@router.get(
    "/operational-facts",
    response_model=OperationalFactsResponse,
)
def operational_facts(
    session: SessionDependency,
) -> OperationalFactsResponse:
    try:
        return get_operational_facts(session)
    except SQLAlchemyError:
        logger.exception("Operational facts database query failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OPERATIONAL_FACTS_UNAVAILABLE",
                "message": (
                    "Operational facts are temporarily unavailable."
                ),
            },
        ) from None
