from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.space import Space


SPACE_CONTEXT_HEADER = "X-Foreman-Space-Id"

SessionDependency = Annotated[Session, Depends(get_session)]
RequestedSpaceId = Annotated[
    str | None,
    Header(alias=SPACE_CONTEXT_HEADER),
]


def get_active_space(
    session: SessionDependency,
    requested_space_id: RequestedSpaceId = None,
) -> Space:
    space_id = (
        requested_space_id.strip()
        if requested_space_id is not None
        else DEFAULT_SPACE_ID
    )
    space = session.get(Space, space_id)

    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SPACE_NOT_FOUND",
                "message": "The requested Space does not exist.",
            },
        )

    return space


ActiveSpaceDependency = Annotated[Space, Depends(get_active_space)]
