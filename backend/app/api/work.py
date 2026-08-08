import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.work import WorkRead
from app.services.work import get_work


router = APIRouter(prefix="/api", tags=["work"])
SessionDependency = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)


@router.get(
    "/work",
    response_model=WorkRead,
)
def read_work(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> WorkRead:
    try:
        return get_work(
            session,
            active_space,
        )
    except SQLAlchemyError:
        logger.exception("Normalized Work read model query failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "WORK_READ_MODEL_UNAVAILABLE",
                "message": (
                    "The normalized Work read model is temporarily "
                    "unavailable."
                ),
            },
        ) from None
