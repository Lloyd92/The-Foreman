import copy
from datetime import date, datetime, timedelta, timezone

from pydantic import ValidationError

from app.core.default_space import DEFAULT_SPACE_ID
from app.models.inventory import InventoryItem
from app.models.inventory_migration import InventoryMigration
from app.models.project import Project
from app.models.project_material_requirement import (
    ProjectMaterialRequirement,
)
from app.models.project_migration import ProjectMigration
from app.models.task import Task
from app.models.task_migration import TaskMigration
from app.schemas.data_export import PortableDataExport
from app.services.data_export import build_portable_data_export
from test_support import DatabaseTestCase


CREATED_AT = datetime(2026, 8, 1, 20, 0, tzinfo=timezone.utc)
STORED_AT = datetime(2026, 7, 31, 16, 0)


class PortableDataExportServiceTests(DatabaseTestCase):
    def add_committed_fixture(self) -> None:
        inventory_b = InventoryItem(
            id="inventory-b",
            space_id=DEFAULT_SPACE_ID,
            name="Board",
            category="Lumber",
            quantity=8,
            unit="sheets",
            minimum=2,
            location="Rack B",
            cost=48.5,
            supplier="Workshop Supply",
            notes="Keep dry",
            created_at=STORED_AT,
            updated_at=STORED_AT,
        )
        inventory_a = InventoryItem(
            id="inventory-a",
            space_id=DEFAULT_SPACE_ID,
            name="Fastener",
            category="Hardware",
            quantity=100,
            unit="pieces",
            minimum=25,
            location="Bin A",
            cost=0.15,
            supplier="Local Supply",
            notes="",
            created_at=STORED_AT,
            updated_at=STORED_AT,
        )
        archived_project = Project(
            id="project-b",
            space_id=DEFAULT_SPACE_ID,
            name="Archived Project",
            type="internal",
            status="archived",
            priority="low",
            progress=100,
            start_date=date(2026, 6, 1),
            target_date=date(2026, 6, 30),
            estimated_cost=50,
            description="Completed test project",
            notes="Included in portable export",
            created_at=STORED_AT,
            updated_at=STORED_AT,
            archived_at=STORED_AT,
        )
        active_project = Project(
            id="project-a",
            space_id=DEFAULT_SPACE_ID,
            name="Active Project",
            type="build",
            status="active",
            priority="high",
            progress=25.5,
            start_date=date(2026, 7, 1),
            target_date=None,
            estimated_cost=425.75,
            description="Current build",
            notes="Authoritative project data",
            created_at=STORED_AT,
            updated_at=STORED_AT,
            archived_at=None,
        )
        active_project.material_requirements = [
            ProjectMaterialRequirement(
                inventory_item_id="missing-inventory",
                required_quantity=2.5,
                note="Reference intentionally missing",
            ),
            ProjectMaterialRequirement(
                inventory_item_id="inventory-a",
                required_quantity=12,
                note="Required hardware",
            ),
        ]
        task_b = Task(
            id="task-b",
            space_id=DEFAULT_SPACE_ID,
            title="Archived project follow-up",
            priority="low",
            completed=True,
            project_id="project-b",
            created_at=STORED_AT,
            updated_at=STORED_AT,
        )
        task_a = Task(
            id="task-a",
            space_id=DEFAULT_SPACE_ID,
            title="Cut material",
            priority="high",
            completed=False,
            project_id="project-a",
            created_at=STORED_AT,
            updated_at=STORED_AT,
        )

        self.session.add_all(
            [
                inventory_b,
                inventory_a,
                archived_project,
                active_project,
                task_b,
                task_a,
            ]
        )
        self.session.flush()
        self.session.add_all(
            [
                InventoryMigration(
                    id=1,
                    space_id=DEFAULT_SPACE_ID,
                    source="browser",
                    source_record_id="legacy-inventory",
                    inventory_item_id="inventory-a",
                    migrated_at=STORED_AT,
                ),
                ProjectMigration(
                    id=1,
                    space_id=DEFAULT_SPACE_ID,
                    source="browser",
                    source_record_id="legacy-project",
                    project_id="project-a",
                    payload_hash="a" * 64,
                    migrated_at=STORED_AT,
                ),
                TaskMigration(
                    id=1,
                    space_id=DEFAULT_SPACE_ID,
                    source="browser",
                    source_record_id="legacy-task",
                    task_id="task-a",
                    migrated_at=STORED_AT,
                ),
            ]
        )
        self.session.commit()

    def test_empty_export_has_explicit_non_restorable_contract(
        self,
    ) -> None:
        result = build_portable_data_export(
            self.session,
            created_at=CREATED_AT,
        )
        payload = result.model_dump(mode="json", by_alias=True)

        self.assertEqual(payload["exportFormatVersion"], 1)
        self.assertEqual(
            payload["artifactType"],
            "portable-data-export",
        )
        self.assertFalse(payload["restorable"])
        self.assertEqual(payload["applicationName"], "The Foreman")
        self.assertEqual(payload["applicationVersion"], "0.7.5")
        self.assertEqual(
            payload["createdAt"],
            "2026-08-01T20:00:00Z",
        )
        self.assertEqual(
            payload["recordCounts"],
            {
                "projects": 0,
                "projectMaterialRequirements": 0,
                "tasks": 0,
                "inventoryItems": 0,
            },
        )
        self.assertEqual(payload["projects"], [])
        self.assertEqual(payload["tasks"], [])
        self.assertEqual(payload["inventoryItems"], [])

    def test_export_contains_only_authoritative_portable_data(
        self,
    ) -> None:
        self.add_committed_fixture()
        result = build_portable_data_export(
            self.session,
            created_at=CREATED_AT,
        )
        payload = result.model_dump(mode="json", by_alias=True)

        self.assertEqual(
            payload["recordCounts"],
            {
                "projects": 2,
                "projectMaterialRequirements": 2,
                "tasks": 2,
                "inventoryItems": 2,
            },
        )
        self.assertEqual(
            [project["id"] for project in payload["projects"]],
            ["project-a", "project-b"],
        )
        self.assertEqual(
            [
                material["inventoryItemId"]
                for material in payload["projects"][0]["materials"]
            ],
            ["inventory-a", "missing-inventory"],
        )
        self.assertEqual(
            payload["projects"][1]["status"],
            "archived",
        )
        self.assertEqual(
            [task["id"] for task in payload["tasks"]],
            ["task-a", "task-b"],
        )
        self.assertEqual(
            [item["id"] for item in payload["inventoryItems"]],
            ["inventory-a", "inventory-b"],
        )
        self.assertEqual(
            set(payload["inventoryItems"][0]),
            {
                "id",
                "name",
                "category",
                "quantity",
                "unit",
                "minimum",
                "location",
                "cost",
                "supplier",
                "notes",
                "createdAt",
                "updatedAt",
            },
        )
        self.assertNotIn("isLow", payload["inventoryItems"][0])
        self.assertNotIn("status", payload["inventoryItems"][0])
        self.assertNotIn("explanation", payload["inventoryItems"][0])
        self.assertNotIn("inventoryMigrations", payload)
        self.assertNotIn("projectMigrations", payload)
        self.assertNotIn("taskMigrations", payload)
        self.assertNotIn("operationalFacts", payload)

    def test_export_order_and_serialization_are_repeatable(
        self,
    ) -> None:
        self.add_committed_fixture()

        first = build_portable_data_export(
            self.session,
            created_at=CREATED_AT,
        ).model_dump_json(by_alias=True)

        self.session.expire_all()

        second = build_portable_data_export(
            self.session,
            created_at=CREATED_AT,
        ).model_dump_json(by_alias=True)

        self.assertEqual(first, second)
        self.assertIn('"createdAt":"2026-07-31T16:00:00Z"', first)

    def test_export_uses_committed_state_without_mutating_caller(
        self,
    ) -> None:
        self.add_committed_fixture()
        pending = InventoryItem(
            id="inventory-pending",
            space_id=DEFAULT_SPACE_ID,
            name="Uncommitted",
            category="Test",
            quantity=1,
            unit="item",
            minimum=0,
            location="Pending",
            cost=0,
            supplier="",
            notes="Must not be exported",
            created_at=STORED_AT,
            updated_at=STORED_AT,
        )
        self.session.add(pending)

        result = build_portable_data_export(
            self.session,
            created_at=CREATED_AT,
        )

        self.assertEqual(
            [item.id for item in result.inventory_items],
            ["inventory-a", "inventory-b"],
        )
        self.assertIn(pending, self.session.new)
        self.assertFalse(self.session.dirty)
        self.assertFalse(self.session.deleted)

    def test_export_contract_rejects_bad_counts_and_non_utc_time(
        self,
    ) -> None:
        valid = build_portable_data_export(
            self.session,
            created_at=CREATED_AT,
        ).model_dump(mode="json", by_alias=True)

        bad_counts = copy.deepcopy(valid)
        bad_counts["recordCounts"]["projects"] = 1

        with self.assertRaises(ValidationError):
            PortableDataExport.model_validate(bad_counts)

        non_utc = copy.deepcopy(valid)
        non_utc["createdAt"] = datetime(
            2026,
            8,
            1,
            16,
            0,
            tzinfo=timezone(timedelta(hours=-4)),
        )

        with self.assertRaises(ValidationError):
            PortableDataExport.model_validate(non_utc)

        with self.assertRaises(ValueError):
            build_portable_data_export(
                self.session,
                created_at=datetime(2026, 8, 1, 20, 0),
            )
