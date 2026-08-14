from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.money_account import MoneyAccount
from app.models.money_category import MoneyCategory
from app.models.money_transaction import MoneyTransaction


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


def list_transactions(
    session: Session,
    space_id: str,
) -> list[MoneyTransaction]:
    statement = (
        select(MoneyTransaction)
        .where(MoneyTransaction.space_id == space_id)
        .order_by(
            MoneyTransaction.occurred_on.desc(),
            MoneyTransaction.created_at.desc(),
            MoneyTransaction.id.asc(),
        )
    )
    return list(session.scalars(statement))


def get_transaction(
    session: Session,
    space_id: str,
    transaction_id: str,
) -> MoneyTransaction | None:
    statement = select(MoneyTransaction).where(
        MoneyTransaction.id == transaction_id,
        MoneyTransaction.space_id == space_id,
    )
    return session.scalar(statement)


def add_transaction(
    session: Session,
    transaction: MoneyTransaction,
) -> MoneyTransaction:
    session.add(transaction)
    session.flush()
    return transaction


def delete_transaction(
    session: Session,
    transaction: MoneyTransaction,
) -> None:
    session.delete(transaction)
