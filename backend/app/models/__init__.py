"""SQLAlchemy persistence models."""

from app.models.calendar_entry import CalendarEntry
from app.models.calendar_series import CalendarSeries
from app.models.calendar_series_exclusion import CalendarSeriesExclusion
from app.models.calendar_setting import CalendarSetting
from app.models.inventory import InventoryItem
from app.models.inventory_migration import InventoryMigration
from app.models.library_record import LibraryRecord
from app.models.library_relationship import LibraryRelationship
from app.models.member import Member
from app.models.money_account import MoneyAccount
from app.models.money_budget import MoneyBudget
from app.models.money_category import MoneyCategory
from app.models.money_obligation import MoneyObligation
from app.models.money_relationship import MoneyRelationship
from app.models.money_transaction import MoneyTransaction
from app.models.module_state import ModuleState
from app.models.organization import Organization
from app.models.organization_space_relationship import (
    OrganizationSpaceRelationship,
)
from app.models.person import Person
from app.models.project import Project
from app.models.project_migration import ProjectMigration
from app.models.project_material_requirement import (
    ProjectMaterialRequirement,
)
from app.models.space import Space
from app.models.task import Task
from app.models.task_migration import TaskMigration
from app.models.tool import Tool
from app.models.care_plan import CarePlan
from app.models.tool_maintenance_record import ToolMaintenanceRecord
from app.models.work_calendar_relationship import WorkCalendarRelationship
from app.models.work_dependency import WorkDependency
from app.models.work_tool_requirement import WorkToolRequirement

__all__ = [
    "CalendarEntry",
    "CalendarSeries",
    "CalendarSeriesExclusion",
    "CalendarSetting",
    "InventoryItem",
    "InventoryMigration",
    "LibraryRecord",
    "LibraryRelationship",
    "Member",
    "MoneyAccount",
    "MoneyBudget",
    "MoneyCategory",
    "MoneyObligation",
    "MoneyRelationship",
    "MoneyTransaction",
    "ModuleState",
    "Organization",
    "OrganizationSpaceRelationship",
    "Person",
    "Project",
    "ProjectMigration",
    "ProjectMaterialRequirement",
    "Space",
    "Task",
    "TaskMigration",
    "Tool",
    "CarePlan",
    "ToolMaintenanceRecord",
    "WorkCalendarRelationship",
    "WorkDependency",
    "WorkToolRequirement",
]
