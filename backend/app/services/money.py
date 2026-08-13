from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.money_account import MoneyAccount
from app.models.money_category import MoneyCategory
from app.models.space import Space
from app.repositories import money as money_repository
from app.schemas.money import (
    MoneyAccountCreate,
    MoneyAccountUpdate,
    MoneyCategoryCreate,
    MoneyCategoryUpdate,
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
