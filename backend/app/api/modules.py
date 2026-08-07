from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.module_registry import (
    ModuleRegistryRead,
    ModuleStateUpdate,
)
from app.services import modules as module_service


router = APIRouter(prefix="/api/modules", tags=["modules"])
SessionDependency = Annotated[Session, Depends(get_session)]


def module_error(error: Exception) -> HTTPException:
    if isinstance(error, module_service.ModuleNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "MODULE_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(
        error,
        module_service.ModuleDependenciesUnsatisfiedError,
    ):
        code = "MODULE_DEPENDENCIES_UNSATISFIED"
    elif isinstance(
        error,
        module_service.ModuleEnabledDependentsError,
    ):
        code = "MODULE_ENABLED_DEPENDENTS"
    else:
        raise TypeError("Unsupported module service error.")

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": code,
            "message": str(error),
        },
    )


@router.get("", response_model=list[ModuleRegistryRead])
def list_modules(
    session: SessionDependency,
) -> list[ModuleRegistryRead]:
    return module_service.list_modules(session)


@router.get(
    "/{module_id}",
    response_model=ModuleRegistryRead,
)
def read_module(
    module_id: str,
    session: SessionDependency,
) -> ModuleRegistryRead:
    try:
        return module_service.require_module(
            session,
            module_id,
        )
    except module_service.ModuleNotFoundError as error:
        raise module_error(error) from error


@router.patch(
    "/{module_id}",
    response_model=ModuleRegistryRead,
)
def update_module_state(
    module_id: str,
    data: ModuleStateUpdate,
    session: SessionDependency,
) -> ModuleRegistryRead:
    try:
        return module_service.set_module_enabled(
            session,
            module_id,
            data.enabled,
        )
    except (
        module_service.ModuleNotFoundError,
        module_service.ModuleDependenciesUnsatisfiedError,
        module_service.ModuleEnabledDependentsError,
    ) as error:
        raise module_error(error) from error
