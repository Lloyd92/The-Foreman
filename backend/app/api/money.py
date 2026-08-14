from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.money import (
    MoneyAccountCreate,
    MoneyAccountRead,
    MoneyAccountUpdate,
    MoneyBudgetCreate,
    MoneyBudgetRead,
    MoneyBudgetUpdate,
    MoneyObligationCreate,
    MoneyObligationRead,
    MoneyObligationUpdate,
    MoneyRelationshipCreate,
    MoneyRelationshipRead,
    MoneyRelationshipUpdate,
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



@router.get("/budgets", response_model=list[MoneyBudgetRead])
def list_budgets(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MoneyBudgetRead]:
    return money_service.list_budgets(session, active_space)


@router.post(
    "/budgets",
    response_model=MoneyBudgetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_budget(
    data: MoneyBudgetCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyBudgetRead:
    try:
        return money_service.create_budget(session, active_space, data)
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.get("/budgets/{budget_id}", response_model=MoneyBudgetRead)
def read_budget(
    budget_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyBudgetRead:
    try:
        return money_service.require_budget(session, active_space, budget_id)
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.patch("/budgets/{budget_id}", response_model=MoneyBudgetRead)
def update_budget(
    budget_id: str,
    data: MoneyBudgetUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyBudgetRead:
    try:
        return money_service.update_budget(
            session, active_space, budget_id, data
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.delete(
    "/budgets/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_budget(
    budget_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        money_service.delete_budget(session, active_space, budget_id)
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/obligations", response_model=list[MoneyObligationRead])
def list_obligations(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MoneyObligationRead]:
    return money_service.list_obligations(session, active_space)


@router.post(
    "/obligations",
    response_model=MoneyObligationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_obligation(
    data: MoneyObligationCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyObligationRead:
    try:
        return money_service.create_obligation(
            session, active_space, data
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.get(
    "/obligations/{obligation_id}",
    response_model=MoneyObligationRead,
)
def read_obligation(
    obligation_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyObligationRead:
    try:
        return money_service.require_obligation(
            session, active_space, obligation_id
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.patch(
    "/obligations/{obligation_id}",
    response_model=MoneyObligationRead,
)
def update_obligation(
    obligation_id: str,
    data: MoneyObligationUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyObligationRead:
    try:
        return money_service.update_obligation(
            session, active_space, obligation_id, data
        )
    except (
        money_service.MoneyNotFoundError,
        money_service.MoneyConflictError,
    ) as error:
        raise money_error(error) from error


@router.delete(
    "/obligations/{obligation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_obligation(
    obligation_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        money_service.delete_obligation(
            session, active_space, obligation_id
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.get(
    "/relationships",
    response_model=list[MoneyRelationshipRead],
)
def list_relationships(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MoneyRelationshipRead]:
    return money_service.list_relationships(session, active_space)


@router.post(
    "/relationships",
    response_model=MoneyRelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    data: MoneyRelationshipCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyRelationshipRead:
    try:
        return money_service.create_relationship(
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
    "/relationships/{relationship_id}",
    response_model=MoneyRelationshipRead,
)
def read_relationship(
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyRelationshipRead:
    try:
        value = money_service.require_relationship_model(
            session,
            active_space,
            relationship_id,
        )
        return money_service.serialize_relationship(
            session,
            active_space,
            value,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.patch(
    "/relationships/{relationship_id}",
    response_model=MoneyRelationshipRead,
)
def update_relationship(
    relationship_id: str,
    data: MoneyRelationshipUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MoneyRelationshipRead:
    try:
        return money_service.update_relationship(
            session,
            active_space,
            relationship_id,
            data,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error


@router.delete(
    "/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship(
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        money_service.delete_relationship(
            session,
            active_space,
            relationship_id,
        )
    except money_service.MoneyNotFoundError as error:
        raise money_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
