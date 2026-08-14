from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.money_account import MoneyAccount
from app.models.money_budget import MoneyBudget
from app.models.money_obligation import MoneyObligation
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



def list_budgets(session: Session, space_id: str) -> list[MoneyBudget]:
    statement = (
        select(MoneyBudget)
        .where(MoneyBudget.space_id == space_id)
        .order_by(MoneyBudget.start_date.desc(), MoneyBudget.id.asc())
    )
    return list(session.scalars(statement))


def get_budget(
    session: Session,
    space_id: str,
    budget_id: str,
) -> MoneyBudget | None:
    return session.scalar(
        select(MoneyBudget).where(
            MoneyBudget.id == budget_id,
            MoneyBudget.space_id == space_id,
        )
    )


def add_budget(session: Session, budget: MoneyBudget) -> MoneyBudget:
    session.add(budget)
    session.flush()
    return budget


def delete_budget(session: Session, budget: MoneyBudget) -> None:
    session.delete(budget)


def list_obligations(
    session: Session,
    space_id: str,
) -> list[MoneyObligation]:
    statement = (
        select(MoneyObligation)
        .where(MoneyObligation.space_id == space_id)
        .order_by(MoneyObligation.start_date.asc(), MoneyObligation.id.asc())
    )
    return list(session.scalars(statement))


def get_obligation(
    session: Session,
    space_id: str,
    obligation_id: str,
) -> MoneyObligation | None:
    return session.scalar(
        select(MoneyObligation).where(
            MoneyObligation.id == obligation_id,
            MoneyObligation.space_id == space_id,
        )
    )


def add_obligation(
    session: Session,
    obligation: MoneyObligation,
) -> MoneyObligation:
    session.add(obligation)
    session.flush()
    return obligation


def delete_obligation(
    session: Session,
    obligation: MoneyObligation,
) -> None:
    session.delete(obligation)
