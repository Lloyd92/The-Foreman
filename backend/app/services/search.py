from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.space import Space
from app.repositories import calendar as calendar_repository
from app.repositories import care_plans as care_plans_repository
from app.repositories import inventory as inventory_repository
from app.repositories import library as library_repository
from app.repositories import members as members_repository
from app.repositories import money as money_repository
from app.repositories import organizations as organizations_repository
from app.repositories import (
    organization_relationships as organization_relationships_repository,
)
from app.repositories import people as people_repository
from app.repositories import projects as projects_repository
from app.repositories import tasks as tasks_repository
from app.repositories import tools as tools_repository
from app.schemas.search import SearchResultRead, UniversalSearchRead


def _text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clip(value: str) -> str:
    return value if len(value) <= 500 else value[:497] + "..."


def _first_match(
    query: str,
    values: Iterable[object | None],
) -> str | None:
    needle = query.casefold()

    for value in values:
        candidate = _text(value)
        if needle in candidate.casefold():
            return candidate

    return None


def _result(
    *,
    source_type: str,
    source_id: str,
    title: str,
    summary: str,
    matched_text: str,
) -> SearchResultRead:
    return SearchResultRead(
        source_type=source_type,
        source_id=source_id,
        title=title,
        summary=_clip(summary),
        matched_text=_clip(matched_text),
    )


def universal_search(
    session: Session,
    active_space: Space,
    query: str,
) -> UniversalSearchRead:
    results: list[SearchResultRead] = []
    space_id = active_space.id

    for project in projects_repository.list_projects(
        session,
        space_id,
        include_archived=True,
    ):
        matched = _first_match(
            query,
            (
                project.name,
                project.type,
                project.status,
                project.description,
                project.notes,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="project",
                    source_id=project.id,
                    title=project.name,
                    summary=project.description or project.notes,
                    matched_text=matched,
                )
            )

    for task in tasks_repository.list_tasks(session, space_id):
        matched = _first_match(
            query,
            (
                task.title,
                task.priority,
                task.due_date,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="task",
                    source_id=task.id,
                    title=task.title,
                    summary=(
                        "Completed"
                        if task.completed
                        else "Open"
                    ),
                    matched_text=matched,
                )
            )

    for tool in tools_repository.list_tools(session, space_id):
        matched = _first_match(
            query,
            (
                tool.name,
                tool.category,
                tool.condition,
                tool.location,
                tool.availability,
                tool.notes,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="tool",
                    source_id=tool.id,
                    title=tool.name,
                    summary=" · ".join(
                        value
                        for value in (
                            tool.category,
                            tool.location,
                            tool.condition,
                        )
                        if value
                    ),
                    matched_text=matched,
                )
            )

    for item in inventory_repository.list_inventory(session, space_id):
        matched = _first_match(
            query,
            (
                item.name,
                item.category,
                item.location,
                item.supplier,
                item.notes,
                item.unit,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="inventory",
                    source_id=item.id,
                    title=item.name,
                    summary=" · ".join(
                        value
                        for value in (
                            item.category,
                            item.location,
                            item.supplier,
                        )
                        if value
                    ),
                    matched_text=matched,
                )
            )

    for plan in care_plans_repository.list_care_plans(
        session,
        space_id,
    ):
        matched = _first_match(
            query,
            (
                plan.name,
                plan.care_type,
                plan.description,
                plan.notes,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="care_plan",
                    source_id=plan.id,
                    title=plan.name,
                    summary=plan.description or plan.notes,
                    matched_text=matched,
                )
            )

    for entry in calendar_repository.list_entries(session, space_id):
        matched = _first_match(
            query,
            (
                entry.title,
                entry.kind,
                entry.location,
                entry.notes,
                entry.start_at,
                entry.start_date,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="calendar_entry",
                    source_id=entry.id,
                    title=entry.title,
                    summary=" · ".join(
                        value
                        for value in (
                            entry.kind,
                            entry.location,
                        )
                        if value
                    ),
                    matched_text=matched,
                )
            )

    for series in calendar_repository.list_series(session, space_id):
        matched = _first_match(
            query,
            (
                series.title,
                series.kind,
                series.frequency,
                series.location,
                series.notes,
                series.anchor_date,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="calendar_series",
                    source_id=series.id,
                    title=series.title,
                    summary=" · ".join(
                        value
                        for value in (
                            series.kind,
                            series.frequency,
                            series.location,
                        )
                        if value
                    ),
                    matched_text=matched,
                )
            )

    for account in money_repository.list_accounts(session, space_id):
        matched = _first_match(
            query,
            (
                account.name,
                account.kind,
                account.currency_code,
                account.notes,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="money_account",
                    source_id=account.id,
                    title=account.name,
                    summary=account.kind,
                    matched_text=matched,
                )
            )

    for category in money_repository.list_categories(session, space_id):
        matched = _first_match(
            query,
            (
                category.name,
                category.kind,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="money_category",
                    source_id=category.id,
                    title=category.name,
                    summary=category.kind,
                    matched_text=matched,
                )
            )

    for transaction in money_repository.list_transactions(
        session,
        space_id,
    ):
        matched = _first_match(
            query,
            (
                transaction.description,
                transaction.counterparty,
                transaction.kind,
                transaction.notes,
                transaction.occurred_on,
                transaction.currency_code,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="money_transaction",
                    source_id=transaction.id,
                    title=transaction.description,
                    summary=" · ".join(
                        value
                        for value in (
                            transaction.counterparty,
                            transaction.kind,
                        )
                        if value
                    ),
                    matched_text=matched,
                )
            )

    for budget in money_repository.list_budgets(session, space_id):
        matched = _first_match(
            query,
            (
                budget.name,
                budget.notes,
                budget.start_date,
                budget.end_date,
                budget.currency_code,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="money_budget",
                    source_id=budget.id,
                    title=budget.name,
                    summary=f"{budget.start_date} – {budget.end_date}",
                    matched_text=matched,
                )
            )

    for obligation in money_repository.list_obligations(
        session,
        space_id,
    ):
        matched = _first_match(
            query,
            (
                obligation.name,
                obligation.frequency,
                obligation.notes,
                obligation.start_date,
                obligation.end_date,
                obligation.currency_code,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="money_obligation",
                    source_id=obligation.id,
                    title=obligation.name,
                    summary=obligation.frequency,
                    matched_text=matched,
                )
            )

    for record in library_repository.list_records(session, space_id):
        matched = _first_match(
            query,
            (
                record.title,
                record.kind,
                record.content,
                record.reference_location,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="library_record",
                    source_id=record.id,
                    title=record.title,
                    summary=(
                        record.reference_location
                        or record.content
                        or record.kind
                    ),
                    matched_text=matched,
                )
            )

    for member in members_repository.list_members(session, space_id):
        person = people_repository.get_person(
            session,
            member.person_id,
        )
        if person is None:
            continue

        matched = _first_match(
            query,
            (
                person.display_name,
                person.given_name,
                person.family_name,
                person.description,
                member.role,
                member.responsibilities,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="person",
                    source_id=person.id,
                    title=person.display_name,
                    summary=member.role,
                    matched_text=matched,
                )
            )

    organization_ids: set[str] = set()
    for relationship in (
        organization_relationships_repository
        .list_organization_relationships(
            session,
            space_id,
        )
    ):
        if relationship.organization_id in organization_ids:
            continue

        organization = organizations_repository.get_organization(
            session,
            relationship.organization_id,
        )
        if organization is None:
            continue

        related_roles = [
            item.role
            for item in (
                organization_relationships_repository
                .list_organization_relationships(
                    session,
                    space_id,
                )
            )
            if item.organization_id == organization.id
        ]

        matched = _first_match(
            query,
            (
                organization.name,
                organization.description,
                *related_roles,
            ),
        )
        if matched is not None:
            results.append(
                _result(
                    source_type="organization",
                    source_id=organization.id,
                    title=organization.name,
                    summary=", ".join(related_roles),
                    matched_text=matched,
                )
            )

        organization_ids.add(organization.id)

    source_order = {
        source_type: index
        for index, source_type in enumerate(
            (
                "project",
                "task",
                "tool",
                "inventory",
                "care_plan",
                "calendar_entry",
                "calendar_series",
                "money_account",
                "money_category",
                "money_transaction",
                "money_budget",
                "money_obligation",
                "library_record",
                "person",
                "organization",
            )
        )
    }

    results.sort(
        key=lambda item: (
            source_order[item.source_type],
            item.title.casefold(),
            item.title,
            item.source_id,
        )
    )

    return UniversalSearchRead(
        query=query,
        results=results,
    )
