from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.money_account import MoneyAccount
from app.models.money_category import MoneyCategory


def list_accounts(
    session: Session,
    space_id: str,
) -> list[MoneyAccount]:
    statement = (
        select(MoneyAccount)
        .where(MoneyAccount.space_id == space_id)
        .order_by(
            MoneyAccount.name.asc(),
            MoneyAccount.id.asc(),
        )
    )
    return list(session.scalars(statement))


def get_account(
    session: Session,
    space_id: str,
    account_id: str,
) -> MoneyAccount | None:
    statement = select(MoneyAccount).where(
        MoneyAccount.id == account_id,
        MoneyAccount.space_id == space_id,
    )
    return session.scalar(statement)


def add_account(
    session: Session,
    account: MoneyAccount,
) -> MoneyAccount:
    session.add(account)
    session.flush()
    return account


def delete_account(
    session: Session,
    account: MoneyAccount,
) -> None:
    session.delete(account)


def list_categories(
    session: Session,
    space_id: str,
) -> list[MoneyCategory]:
    statement = (
        select(MoneyCategory)
        .where(MoneyCategory.space_id == space_id)
        .order_by(
            MoneyCategory.kind.asc(),
            MoneyCategory.name.asc(),
            MoneyCategory.id.asc(),
        )
    )
    return list(session.scalars(statement))


def get_category(
    session: Session,
    space_id: str,
    category_id: str,
) -> MoneyCategory | None:
    statement = select(MoneyCategory).where(
        MoneyCategory.id == category_id,
        MoneyCategory.space_id == space_id,
    )
    return session.scalar(statement)


def get_category_by_identity(
    session: Session,
    space_id: str,
    kind: str,
    name: str,
) -> MoneyCategory | None:
    statement = select(MoneyCategory).where(
        MoneyCategory.space_id == space_id,
        MoneyCategory.kind == kind,
        MoneyCategory.name == name,
    )
    return session.scalar(statement)


def add_category(
    session: Session,
    category: MoneyCategory,
) -> MoneyCategory:
    session.add(category)
    session.flush()
    return category


def delete_category(
    session: Session,
    category: MoneyCategory,
) -> None:
    session.delete(category)
