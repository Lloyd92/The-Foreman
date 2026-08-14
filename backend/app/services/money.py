from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.money_account import MoneyAccount
from app.models.money_category import MoneyCategory
from app.models.money_transaction import MoneyTransaction
from app.models.space import Space
from app.repositories import money as money_repository
from app.schemas.money import (
    MoneyAccountCreate,
    MoneyAccountUpdate,
    MoneyCategoryCreate,
    MoneyCategoryUpdate,
    MoneyTransactionCreate,
    MoneyTransactionUpdate,
)


class MoneyNotFoundError(LookupError):
    pass


class MoneyConflictError(ValueError):
    pass


def list_accounts(
    session: Session,
    active_space: Space,
) -> list[MoneyAccount]:
    return money_repository.list_accounts(
        session,
        active_space.id,
    )


def require_account(
    session: Session,
    active_space: Space,
    account_id: str,
) -> MoneyAccount:
    account = money_repository.get_account(
        session,
        active_space.id,
        account_id,
    )
    if account is None:
        raise MoneyNotFoundError("Money Account not found.")
    return account


def create_account(
    session: Session,
    active_space: Space,
    data: MoneyAccountCreate,
) -> MoneyAccount:
    account = MoneyAccount(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        money_repository.add_account(session, account)
        session.commit()
        session.refresh(account)
    except Exception:
        session.rollback()
        raise

    return account


def update_account(
    session: Session,
    active_space: Space,
    account_id: str,
    data: MoneyAccountUpdate,
) -> MoneyAccount:
    account = require_account(
        session,
        active_space,
        account_id,
    )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(account, field, value)

    try:
        session.commit()
        session.refresh(account)
    except Exception:
        session.rollback()
        raise

    return account


def delete_account(
    session: Session,
    active_space: Space,
    account_id: str,
) -> None:
    account = require_account(
        session,
        active_space,
        account_id,
    )

    try:
        money_repository.delete_account(session, account)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise MoneyConflictError(
            "Money Account cannot be deleted while records reference it."
        ) from error
    except Exception:
        session.rollback()
        raise


def list_categories(
    session: Session,
    active_space: Space,
) -> list[MoneyCategory]:
    return money_repository.list_categories(
        session,
        active_space.id,
    )


def require_category(
    session: Session,
    active_space: Space,
    category_id: str,
) -> MoneyCategory:
    category = money_repository.get_category(
        session,
        active_space.id,
        category_id,
    )
    if category is None:
        raise MoneyNotFoundError("Money Category not found.")
    return category


def _require_category_identity_available(
    session: Session,
    active_space: Space,
    *,
    kind: str,
    name: str,
    category_id: str | None = None,
) -> None:
    existing = money_repository.get_category_by_identity(
        session,
        active_space.id,
        kind,
        name,
    )
    if existing is not None and existing.id != category_id:
        raise MoneyConflictError(
            "A Money Category with this kind and name already exists."
        )


def create_category(
    session: Session,
    active_space: Space,
    data: MoneyCategoryCreate,
) -> MoneyCategory:
    _require_category_identity_available(
        session,
        active_space,
        kind=data.kind,
        name=data.name,
    )

    category = MoneyCategory(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        money_repository.add_category(session, category)
        session.commit()
        session.refresh(category)
    except IntegrityError as error:
        session.rollback()
        raise MoneyConflictError(
            "A Money Category with this kind and name already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return category


def update_category(
    session: Session,
    active_space: Space,
    category_id: str,
    data: MoneyCategoryUpdate,
) -> MoneyCategory:
    category = require_category(
        session,
        active_space,
        category_id,
    )

    changes = data.model_dump(exclude_unset=True)
    kind = changes.get("kind", category.kind)
    name = changes.get("name", category.name)

    _require_category_identity_available(
        session,
        active_space,
        kind=kind,
        name=name,
        category_id=category.id,
    )

    for field, value in changes.items():
        setattr(category, field, value)

    try:
        session.commit()
        session.refresh(category)
    except IntegrityError as error:
        session.rollback()
        raise MoneyConflictError(
            "A Money Category with this kind and name already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return category


def delete_category(
    session: Session,
    active_space: Space,
    category_id: str,
) -> None:
    category = require_category(
        session,
        active_space,
        category_id,
    )

    try:
        money_repository.delete_category(session, category)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise MoneyConflictError(
            "Money Category cannot be deleted while records reference it."
        ) from error
    except Exception:
        session.rollback()
        raise


def list_transactions(
    session: Session,
    active_space: Space,
) -> list[MoneyTransaction]:
    return money_repository.list_transactions(
        session,
        active_space.id,
    )


def require_transaction(
    session: Session,
    active_space: Space,
    transaction_id: str,
) -> MoneyTransaction:
    transaction = money_repository.get_transaction(
        session,
        active_space.id,
        transaction_id,
    )
    if transaction is None:
        raise MoneyNotFoundError("Money Transaction not found.")
    return transaction


def _require_transaction_category(
    session: Session,
    active_space: Space,
    category_id: str,
    kind: str,
) -> MoneyCategory:
    category = require_category(
        session,
        active_space,
        category_id,
    )
    if category.kind != kind:
        raise MoneyConflictError(
            "Money Transaction kind must match its Category kind."
        )
    return category


def create_transaction(
    session: Session,
    active_space: Space,
    data: MoneyTransactionCreate,
) -> MoneyTransaction:
    require_account(
        session,
        active_space,
        data.account_id,
    )

    if data.category_id is not None:
        _require_transaction_category(
            session,
            active_space,
            data.category_id,
            data.kind,
        )

    transaction = MoneyTransaction(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        money_repository.add_transaction(session, transaction)
        session.commit()
        session.refresh(transaction)
    except Exception:
        session.rollback()
        raise

    return transaction


def update_transaction(
    session: Session,
    active_space: Space,
    transaction_id: str,
    data: MoneyTransactionUpdate,
) -> MoneyTransaction:
    transaction = require_transaction(
        session,
        active_space,
        transaction_id,
    )
    changes = data.model_dump(exclude_unset=True)

    account_id = changes.get("account_id", transaction.account_id)
    require_account(
        session,
        active_space,
        account_id,
    )

    kind = changes.get("kind", transaction.kind)
    category_id = changes.get(
        "category_id",
        transaction.category_id,
    )

    if category_id is not None:
        _require_transaction_category(
            session,
            active_space,
            category_id,
            kind,
        )

    for field, value in changes.items():
        setattr(transaction, field, value)

    try:
        session.commit()
        session.refresh(transaction)
    except Exception:
        session.rollback()
        raise

    return transaction


def delete_transaction(
    session: Session,
    active_space: Space,
    transaction_id: str,
) -> None:
    transaction = require_transaction(
        session,
        active_space,
        transaction_id,
    )

    try:
        money_repository.delete_transaction(
            session,
            transaction,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
