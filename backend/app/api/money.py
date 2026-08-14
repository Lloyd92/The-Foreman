from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.money import (
    MoneyAccountCreate,
    MoneyAccountRead,
    MoneyAccountUpdate,
    MoneyCategoryCreate,
    MoneyCategoryRead,
    MoneyCategoryUpdate,
    MoneyTransactionCreate,
    MoneyTransactionRead,
    MoneyTransactionUpdate,
)
from app.services import money as money_service

router = APIRouter(prefix="/api/money", tags=["money"])
SessionDependency = Annotated[Session, Depends(get_session)]


def money_error(error: Exception) -> HTTPException:
    if isinstance(error, money_service.MoneyNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )

    if isinstance(error, money_service.MoneyConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )

    raise TypeError("Unsupported Money service error.")


@router.get("/accounts", response_model=list[MoneyAccountRead])
def list_accounts(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MoneyAccountRead]:
    return money_service.list_accounts(session, active_space)


@router.post(
    "/accounts",
    response_model=MoneyAccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    data: MoneyAccountCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyAccountRead:
    return money_service.create_account(
        session,
        active_space,
        data,
    )


@router.get(
    "/accounts/{account_id}",
    response_model=MoneyAccountRead,
)
def read_account(
    account_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyAccountRead:
    try:
        return money_service.require_account(
            session,
            active_space,
            account_id,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.patch(
    "/accounts/{account_id}",
    response_model=MoneyAccountRead,
)
def update_account(
    account_id: str,
    data: MoneyAccountUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyAccountRead:
    try:
        return money_service.update_account(
            session,
            active_space,
            account_id,
            data,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_account(
    account_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        money_service.delete_account(
            session,
            active_space,
            account_id,
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/categories", response_model=list[MoneyCategoryRead])
def list_categories(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MoneyCategoryRead]:
    return money_service.list_categories(session, active_space)


@router.post(
    "/categories",
    response_model=MoneyCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: MoneyCategoryCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyCategoryRead:
    try:
        return money_service.create_category(
            session,
            active_space,
            data,
        )
    except money_service.MoneyConflictError as error:
        raise money_error(error) from error


@router.get(
    "/categories/{category_id}",
    response_model=MoneyCategoryRead,
)
def read_category(
    category_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyCategoryRead:
    try:
        return money_service.require_category(
            session,
            active_space,
            category_id,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.patch(
    "/categories/{category_id}",
    response_model=MoneyCategoryRead,
)
def update_category(
    category_id: str,
    data: MoneyCategoryUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyCategoryRead:
    try:
        return money_service.update_category(
            session,
            active_space,
            category_id,
            data,
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    category_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        money_service.delete_category(
            session,
            active_space,
            category_id,
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.get("/transactions", response_model=list[MoneyTransactionRead])
def list_transactions(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MoneyTransactionRead]:
    return money_service.list_transactions(session, active_space)


@router.post(
    "/transactions",
    response_model=MoneyTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    data: MoneyTransactionCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyTransactionRead:
    try:
        return money_service.create_transaction(
            session,
            active_space,
            data,
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.get(
    "/transactions/{transaction_id}",
    response_model=MoneyTransactionRead,
)
def read_transaction(
    transaction_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyTransactionRead:
    try:
        return money_service.require_transaction(
            session,
            active_space,
            transaction_id,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.patch(
    "/transactions/{transaction_id}",
    response_model=MoneyTransactionRead,
)
def update_transaction(
    transaction_id: str,
    data: MoneyTransactionUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyTransactionRead:
    try:
        return money_service.update_transaction(
            session,
            active_space,
            transaction_id,
            data,
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_transaction(
    transaction_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        money_service.delete_transaction(
            session,
            active_space,
            transaction_id,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
