from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.care_plan import (
    CarePlanCreate,
    CarePlanListQuery,
    CarePlanRead,
    CarePlanUpdate,
)
from app.services import care_plans as care_plan_service


router = APIRouter(
    prefix="/api/care-plans",
    tags=["care"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


def care_plan_error(
    error: Exception,
) -> HTTPException:
    if isinstance(
        error,
        care_plan_service.CarePlanNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CARE_PLAN_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(
        error,
        care_plan_service.CarePlanToolNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CARE_PLAN_TOOL_NOT_FOUND",
                "message": str(error),
            },
        )

    raise TypeError(
        "Unsupported Care Plan service error."
    )


@router.get("", response_model=list[CarePlanRead])
def list_care_plans(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
    filters: Annotated[CarePlanListQuery, Query()],
) -> list[CarePlanRead]:
    return care_plan_service.list_care_plans(
        session,
        active_space,
        search=(
            filters.search.strip()
            if filters.search
            else None
        ),
        care_type=filters.care_type,
        tool_id=filters.tool_id,
        sort_by=filters.sort_by,
        sort_direction=filters.sort_direction,
    )


@router.post(
    "",
    response_model=CarePlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_care_plan(
    data: CarePlanCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CarePlanRead:
    try:
        return care_plan_service.create_care_plan(
            session,
            active_space,
            data,
        )
    except care_plan_service.CarePlanToolNotFoundError as error:
        raise care_plan_error(error) from error


@router.get(
    "/{care_plan_id}",
    response_model=CarePlanRead,
)
def read_care_plan(
    care_plan_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CarePlanRead:
    try:
        return care_plan_service.require_care_plan(
            session,
            active_space,
            care_plan_id,
        )
    except care_plan_service.CarePlanNotFoundError as error:
        raise care_plan_error(error) from error


@router.patch(
    "/{care_plan_id}",
    response_model=CarePlanRead,
)
def update_care_plan(
    care_plan_id: str,
    data: CarePlanUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CarePlanRead:
    try:
        return care_plan_service.update_care_plan(
            session,
            active_space,
            care_plan_id,
            data,
        )
    except (
        care_plan_service.CarePlanNotFoundError,
        care_plan_service.CarePlanToolNotFoundError,
    ) as error:
        raise care_plan_error(error) from error


@router.delete(
    "/{care_plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_care_plan(
    care_plan_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        care_plan_service.delete_care_plan(
            session,
            active_space,
            care_plan_id,
        )
    except care_plan_service.CarePlanNotFoundError as error:
        raise care_plan_error(error) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
