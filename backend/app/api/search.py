import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.search import UniversalSearchRead
from app.services.search import universal_search


router = APIRouter(prefix="/api", tags=["search"])
SessionDependency = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)


@router.get(
    "/search",
    response_model=UniversalSearchRead,
)
def search(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
    q: Annotated[str, Query(min_length=1, max_length=160)],
) -> UniversalSearchRead:
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "SEARCH_QUERY_REQUIRED",
                "message": "Search query cannot be blank.",
            },
        )

    try:
        return universal_search(
            session,
            active_space,
            query,
        )
    except SQLAlchemyError:
        logger.exception("Universal Search query failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "UNIVERSAL_SEARCH_UNAVAILABLE",
                "message": (
                    "Universal Search is temporarily unavailable."
                ),
            },
        ) from None
