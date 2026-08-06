import copy
import math
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import inspect, select

from app.core.database import engine
from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.inventory import InventoryItem
from app.models.project import Project
from app.models.project_material_requirement import (
    ProjectMaterialRequirement,
)
from app.models.project_migration import ProjectMigration
from app.models.task import Task
from app.services.operations import (
    InventorySnapshot,
    MaterialRequirementSnapshot,
    OperationalSnapshot,
    ProjectSnapshot,
    TaskSnapshot,
    calculate_normalized_operational_facts,
    derive_operational_facts,
    load_operational_snapshot,
)
from test_support import DatabaseTestCase


NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def project(
    project_id: str,
    *,
    status: str = "planning",
    archived_at: datetime | None = None,
    requirements: tuple[MaterialRequirementSnapshot, ...] = (),
) -> ProjectSnapshot:
    return ProjectSnapshot(
        id=project_id,
        status=status,
        updated_at=NOW,
        archived_at=archived_at,
        material_requirements=requirements,
    )


def requirement(
    inventory_item_id: str,
    required_quantity: float = 1,
) -> MaterialRequirementSnapshot:
    return MaterialRequirementSnapshot(
        inventory_item_id=inventory_item_id,
        required_quantity=required_quantity,
    )


def inventory(
    inventory_id: str,
    *,
    quantity: float = 10,
    minimum: float = 1,
    name: str | None = None,
) -> InventorySnapshot:
    return InventorySnapshot(
        id=inventory_id,
        name=name or f"Item {inventory_id}",
        quantity=quantity,
        minimum=minimum,
        unit="units",
        updated_at=NOW,
    )


def task(
    task_id: str,
    *,
    completed: bool = False,
    priority: str = "medium",
    project_id: str | None = None,
) -> TaskSnapshot:
    return TaskSnapshot(
        id=task_id,
        priority=priority,
        completed=completed,
        project_id=project_id,
        updated_at=NOW,
    )


def find_fact(result, fact_type: str, subject_id: str):
    return next(
        fact
        for fact in result.facts
        if fact.fact_type == fact_type
        and fact.subject_id == subject_id
    )


class OperationalFactCalculationTests(unittest.TestCase):
    def test_empty_snapshot_has_stable_zero_filled_contract(self) -> None:
        result = derive_operational_facts(OperationalSnapshot())

        self.assertEqual(result.schema_version, 1)
        self.assertEqual(result.facts, [])
        self.assertEqual(
            result.model_dump(mode="json", by_alias=True),
            {
                "schemaVersion": 1,
                "facts": [],
                "summary": {
                    "projects": {
                        "byStatus": {
                            "planning": 0,
                            "active": 0,
                            "onHold": 0,
                            "completed": 0,
                            "archived": 0,
                            "invalid": 0,
                        },
                        "materialReadiness": {
                            "ready": 0,
                            "needsMaterials": 0,
                            "notApplicable": 0,
                            "invalid": 0,
                        },
                    },
                    "tasks": {
                        "open": 0,
                        "completed": 0,
                        "byPriority": {
                            "high": 0,
                            "medium": 0,
                            "low": 0,
                        },
                    },
                    "inventory": {
                        "total": 0,
                        "inStock": 0,
                        "lowStock": 0,
                        "outOfStock": 0,
                        "lowOrOutOfStock": 0,
                        "invalid": 0,
                    },
                },
            },
        )

    def test_schema_uses_camel_case_and_exact_discriminators(self) -> None:
        snapshot = OperationalSnapshot(
            projects=(
                project(
                    "project-1",
                    requirements=(requirement("inventory-1"),),
                ),
            ),
            tasks=(task("task-1"),),
            inventory=(inventory("inventory-1"),),
        )
        serialized = derive_operational_facts(snapshot).model_dump(
            mode="json",
            by_alias=True,
        )

        self.assertEqual(
            [fact["factType"] for fact in serialized["facts"]],
            [
                "project.lifecycle",
                "project.material-readiness",
                "task.work-state",
                "inventory.stock-level",
            ],
        )
        self.assertIn("factId", serialized["facts"][0])
        self.assertIn("subjectType", serialized["facts"][0])
        self.assertIn("subjectId", serialized["facts"][0])
        self.assertIn("reasonCodes", serialized["facts"][0])
        self.assertIn("sourceRecords", serialized["facts"][0])
        self.assertIn(
            "updatedAt",
            serialized["facts"][0]["sourceRecords"][0],
        )

    def test_fact_ids_stay_stable_across_state_changes(self) -> None:
        first = derive_operational_facts(
            OperationalSnapshot(
                projects=(project("project-1"),),
                tasks=(task("task-1"),),
                inventory=(inventory("inventory-1"),),
            )
        )
        second = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "project-1",
                        status="active",
                        requirements=(requirement("inventory-1", 20),),
                    ),
                ),
                tasks=(task("task-1", completed=True),),
                inventory=(
                    inventory("inventory-1", quantity=0),
                ),
            )
        )

        first_ids = {
            fact.fact_type: fact.fact_id
            for fact in first.facts
        }
        second_ids = {
            fact.fact_type: fact.fact_id
            for fact in second.facts
        }
        self.assertEqual(
            first_ids["project.lifecycle"],
            second_ids["project.lifecycle"],
        )
        self.assertEqual(
            first_ids["project.material-readiness"],
            second_ids["project.material-readiness"],
        )
        self.assertEqual(
            first_ids["task.work-state"],
            second_ids["task.work-state"],
        )
        self.assertEqual(
            first_ids["inventory.stock-level"],
            second_ids["inventory.stock-level"],
        )
        self.assertEqual(
            second_ids,
            {
                "project.lifecycle": "project/project-1/lifecycle",
                "project.material-readiness": (
                    "project/project-1/material-readiness"
                ),
                "task.work-state": "task/task-1/work-state",
                "inventory.stock-level": (
                    "inventory/inventory-1/stock-level"
                ),
            },
        )

    def test_fact_order_and_ids_are_canonical_and_unique(self) -> None:
        snapshot = OperationalSnapshot(
            projects=(project("Zulu"), project("alpha")),
            tasks=(task("Zulu"), task("alpha")),
            inventory=(inventory("Zulu"), inventory("alpha")),
        )
        facts = derive_operational_facts(snapshot).facts

        self.assertEqual(
            [(fact.fact_type, fact.subject_id) for fact in facts],
            [
                ("project.lifecycle", "alpha"),
                ("project.lifecycle", "Zulu"),
                ("project.material-readiness", "alpha"),
                ("project.material-readiness", "Zulu"),
                ("task.work-state", "alpha"),
                ("task.work-state", "Zulu"),
                ("inventory.stock-level", "alpha"),
                ("inventory.stock-level", "Zulu"),
            ],
        )
        fact_ids = [fact.fact_id for fact in facts]
        self.assertEqual(len(fact_ids), len(set(fact_ids)))

    def test_duplicate_source_ids_cannot_create_duplicate_facts(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate operational fact ID",
        ):
            derive_operational_facts(
                OperationalSnapshot(
                    projects=(project("same"), project("same")),
                )
            )

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate Inventory source ID",
        ):
            derive_operational_facts(
                OperationalSnapshot(
                    inventory=(
                        inventory("same"),
                        inventory("same"),
                    )
                )
            )

    def test_every_valid_project_lifecycle_state(self) -> None:
        for status in (
            "planning",
            "active",
            "on-hold",
            "completed",
            "archived",
        ):
            with self.subTest(status=status):
                archived_at = NOW if status == "archived" else None
                result = derive_operational_facts(
                    OperationalSnapshot(
                        projects=(
                            project(
                                "project-1",
                                status=status,
                                archived_at=archived_at,
                            ),
                        )
                    )
                )
                fact = find_fact(
                    result,
                    "project.lifecycle",
                    "project-1",
                )
                expected_reason = (
                    f"PROJECT_STATUS_{status.replace('-', '_').upper()}"
                )
                self.assertEqual(fact.state, status)
                self.assertEqual(
                    fact.reason_codes,
                    [expected_reason],
                )

    def test_project_lifecycle_invalid_states_are_explainable(self) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "unexpected",
                        status="mystery",
                    ),
                    project(
                        "archived-without-time",
                        status="archived",
                    ),
                    project(
                        "active-with-time",
                        status="active",
                        archived_at=NOW,
                    ),
                )
            )
        )

        unsupported = find_fact(
            result,
            "project.lifecycle",
            "unexpected",
        )
        self.assertEqual(unsupported.state, "invalid")
        self.assertEqual(
            unsupported.reason_codes,
            ["PROJECT_STATUS_INVALID"],
        )

        for project_id in (
            "archived-without-time",
            "active-with-time",
        ):
            inconsistent = find_fact(
                result,
                "project.lifecycle",
                project_id,
            )
            self.assertEqual(inconsistent.state, "invalid")
            self.assertEqual(
                inconsistent.reason_codes,
                [
                    "PROJECT_STATUS_INVALID",
                    "PROJECT_ARCHIVE_STATE_INCONSISTENT",
                ],
            )

    def test_material_readiness_applies_to_planning_and_active_only(
        self,
    ) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=tuple(
                    project(status, status=status)
                    for status in (
                        "planning",
                        "active",
                        "on-hold",
                        "completed",
                        "archived",
                    )
                )
            )
        )
        readiness_subjects = [
            fact.subject_id
            for fact in result.facts
            if fact.fact_type == "project.material-readiness"
        ]

        self.assertEqual(readiness_subjects, ["active", "planning"])
        for project_id in readiness_subjects:
            fact = find_fact(
                result,
                "project.material-readiness",
                project_id,
            )
            self.assertEqual(fact.state, "not-applicable")
            self.assertEqual(
                fact.reason_codes,
                ["PROJECT_MATERIALS_NOT_LISTED"],
            )

    def test_sufficient_requirements_are_ready_and_canonical(self) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "project-1",
                        requirements=(
                            requirement("zulu", 2),
                            requirement("Alpha", 1),
                        ),
                    ),
                ),
                inventory=(
                    inventory("zulu", quantity=2),
                    inventory("Alpha", quantity=3),
                ),
            )
        )
        fact = find_fact(
            result,
            "project.material-readiness",
            "project-1",
        )

        self.assertEqual(fact.state, "ready")
        self.assertEqual(
            fact.reason_codes,
            ["PROJECT_MATERIALS_SUFFICIENT"],
        )
        self.assertEqual(
            [
                evidence.inventory_item_id
                for evidence in fact.evidence.requirements
            ],
            ["Alpha", "zulu"],
        )
        self.assertEqual(
            [
                evidence.shortage_quantity
                for evidence in fact.evidence.requirements
            ],
            [0, 0],
        )
        self.assertEqual(
            [
                source.record_type
                for source in fact.source_records
            ],
            [
                "project",
                "project-material-requirement",
                "project-material-requirement",
                "inventory",
                "inventory",
            ],
        )
        self.assertTrue(
            all(
                source.updated_at == NOW
                for source in fact.source_records
            )
        )

    def test_insufficient_requirements_have_exact_shortages(
        self,
    ) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "project-1",
                        requirements=(
                            requirement("one", 0.3),
                            requirement("two", 5),
                            requirement("enough", 2),
                        ),
                    ),
                ),
                inventory=(
                    inventory("one", quantity=0.1, minimum=0),
                    inventory("two", quantity=1),
                    inventory("enough", quantity=2),
                ),
            )
        )
        fact = find_fact(
            result,
            "project.material-readiness",
            "project-1",
        )
        evidence = {
            item.inventory_item_id: item
            for item in fact.evidence.requirements
        }

        self.assertEqual(fact.state, "needs-materials")
        self.assertEqual(
            fact.reason_codes,
            ["PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"],
        )
        self.assertEqual(evidence["one"].shortage_quantity, 0.2)
        self.assertEqual(evidence["two"].shortage_quantity, 4)
        self.assertEqual(evidence["enough"].shortage_quantity, 0)

    def test_missing_inventory_uses_unknown_not_zero(self) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "project-1",
                        requirements=(requirement("missing", 3),),
                    ),
                )
            )
        )
        fact = find_fact(
            result,
            "project.material-readiness",
            "project-1",
        )
        evidence = fact.evidence.requirements[0]

        self.assertEqual(fact.state, "needs-materials")
        self.assertEqual(
            fact.reason_codes,
            ["PROJECT_MATERIAL_INVENTORY_MISSING"],
        )
        self.assertIsNone(evidence.item_name)
        self.assertIsNone(evidence.unit)
        self.assertIsNone(evidence.available_quantity)
        self.assertIsNone(evidence.shortage_quantity)
        self.assertNotIn(
            "inventory",
            [
                source.record_type
                for source in fact.source_records
            ],
        )

    def test_material_reason_and_source_order_are_deterministic(
        self,
    ) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "project-1",
                        requirements=(
                            requirement("missing", 2),
                            requirement("short", 2),
                        ),
                    ),
                ),
                inventory=(inventory("short", quantity=1),),
            )
        )
        fact = find_fact(
            result,
            "project.material-readiness",
            "project-1",
        )

        self.assertEqual(
            fact.reason_codes,
            [
                "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT",
                "PROJECT_MATERIAL_INVENTORY_MISSING",
            ],
        )
        self.assertEqual(
            [
                (source.record_type, source.record_id)
                for source in fact.source_records
            ],
            [
                ("project", "project-1"),
                (
                    "project-material-requirement",
                    "project-1/missing",
                ),
                (
                    "project-material-requirement",
                    "project-1/short",
                ),
                ("inventory", "short"),
            ],
        )

    def test_invalid_material_data_wins_precedence(self) -> None:
        cases = (
            (
                requirement("valid-inventory", 0),
                inventory("valid-inventory"),
                10,
            ),
            (
                requirement("bad-inventory", 1),
                inventory("bad-inventory", quantity=-1),
                -1,
            ),
            (
                requirement("bad-minimum", 1),
                inventory("bad-minimum", minimum=-1),
                10,
            ),
            (
                requirement("not-finite", 1),
                inventory("not-finite", quantity=math.nan),
                "NaN",
            ),
        )

        for requirement_record, item, expected_available in cases:
            with self.subTest(item=item.id):
                result = derive_operational_facts(
                    OperationalSnapshot(
                        projects=(
                            project(
                                "project-1",
                                requirements=(requirement_record,),
                            ),
                        ),
                        inventory=(item,),
                    )
                )
                fact = find_fact(
                    result,
                    "project.material-readiness",
                    "project-1",
                )
                evidence = fact.evidence.requirements[0]

                self.assertEqual(fact.state, "invalid")
                self.assertEqual(
                    fact.reason_codes,
                    ["PROJECT_MATERIAL_DATA_INVALID"],
                )
                self.assertEqual(
                    evidence.reason_code,
                    "PROJECT_MATERIAL_DATA_INVALID",
                )
                self.assertEqual(
                    evidence.available_quantity,
                    expected_available,
                )
                self.assertIsNone(evidence.shortage_quantity)

    def test_readiness_is_isolated_per_project(self) -> None:
        shared_requirement = (requirement("shared", 5),)
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project(
                        "project-1",
                        requirements=shared_requirement,
                    ),
                    project(
                        "project-2",
                        requirements=shared_requirement,
                    ),
                ),
                inventory=(inventory("shared", quantity=5),),
            )
        )

        self.assertEqual(
            [
                fact.state
                for fact in result.facts
                if fact.fact_type == "project.material-readiness"
            ],
            ["ready", "ready"],
        )

    def test_task_states_and_nullable_relationship_evidence(self) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                tasks=(
                    task(
                        "open",
                        priority="high",
                        project_id=None,
                    ),
                    task(
                        "done",
                        completed=True,
                        priority="low",
                        project_id="project-1",
                    ),
                )
            )
        )
        open_fact = find_fact(result, "task.work-state", "open")
        done_fact = find_fact(result, "task.work-state", "done")

        self.assertEqual(open_fact.state, "open")
        self.assertEqual(
            open_fact.reason_codes,
            ["TASK_INCOMPLETE"],
        )
        self.assertIsNone(open_fact.evidence.project_id)
        self.assertEqual(done_fact.state, "completed")
        self.assertEqual(
            done_fact.reason_codes,
            ["TASK_COMPLETED"],
        )
        self.assertEqual(done_fact.evidence.project_id, "project-1")

    def test_inventory_stock_rules_and_invalid_numeric_state(self) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                inventory=(
                    inventory("stocked", quantity=3, minimum=2),
                    inventory("at-minimum", quantity=2, minimum=2),
                    inventory("below", quantity=1, minimum=2),
                    inventory("zero", quantity=0, minimum=2),
                    inventory("negative", quantity=-1, minimum=2),
                    inventory("bad-minimum", quantity=1, minimum=-1),
                    inventory(
                        "infinite",
                        quantity=math.inf,
                        minimum=2,
                    ),
                )
            )
        )
        expected = {
            "stocked": (
                "in-stock",
                "INVENTORY_ABOVE_MINIMUM",
            ),
            "at-minimum": (
                "low-stock",
                "INVENTORY_AT_OR_BELOW_MINIMUM",
            ),
            "below": (
                "low-stock",
                "INVENTORY_AT_OR_BELOW_MINIMUM",
            ),
            "zero": (
                "out-of-stock",
                "INVENTORY_OUT_OF_STOCK",
            ),
            "negative": (
                "invalid",
                "INVENTORY_STOCK_DATA_INVALID",
            ),
            "bad-minimum": (
                "invalid",
                "INVENTORY_STOCK_DATA_INVALID",
            ),
            "infinite": (
                "invalid",
                "INVENTORY_STOCK_DATA_INVALID",
            ),
        }

        for inventory_id, (state, reason) in expected.items():
            with self.subTest(inventory_id=inventory_id):
                fact = find_fact(
                    result,
                    "inventory.stock-level",
                    inventory_id,
                )
                self.assertEqual(fact.state, state)
                self.assertEqual(fact.reason_codes, [reason])

        infinite = find_fact(
            result,
            "inventory.stock-level",
            "infinite",
        )
        self.assertEqual(infinite.evidence.quantity, "Infinity")

    def test_summary_is_derived_from_normalized_facts(self) -> None:
        result = derive_operational_facts(
            OperationalSnapshot(
                projects=(
                    project("ready"),
                    project(
                        "needs",
                        status="active",
                        requirements=(requirement("low", 2),),
                    ),
                    project("completed", status="completed"),
                ),
                tasks=(
                    task("open", priority="high"),
                    task("done", completed=True, priority="low"),
                ),
                inventory=(
                    inventory("low", quantity=1, minimum=1),
                    inventory("empty", quantity=0),
                    inventory("full", quantity=5),
                ),
            )
        )
        summary = result.summary.model_dump(mode="json", by_alias=True)

        self.assertEqual(
            summary["projects"]["byStatus"],
            {
                "planning": 1,
                "active": 1,
                "onHold": 0,
                "completed": 1,
                "archived": 0,
                "invalid": 0,
            },
        )
        self.assertEqual(
            summary["projects"]["materialReadiness"],
            {
                "ready": 0,
                "needsMaterials": 1,
                "notApplicable": 1,
                "invalid": 0,
            },
        )
        self.assertEqual(
            summary["tasks"],
            {
                "open": 1,
                "completed": 1,
                "byPriority": {
                    "high": 1,
                    "medium": 0,
                    "low": 1,
                },
            },
        )
        self.assertEqual(
            summary["inventory"],
            {
                "total": 3,
                "inStock": 1,
                "lowStock": 1,
                "outOfStock": 1,
                "lowOrOutOfStock": 2,
                "invalid": 0,
            },
        )

    def test_calculation_is_pure_and_serialization_is_repeatable(
        self,
    ) -> None:
        snapshot = OperationalSnapshot(
            projects=(
                project(
                    "project-1",
                    requirements=(requirement("inventory-1", 2),),
                ),
            ),
            tasks=(task("task-1"),),
            inventory=(inventory("inventory-1", quantity=1),),
        )
        before = copy.deepcopy(snapshot)
        first = derive_operational_facts(snapshot)
        second = derive_operational_facts(snapshot)

        self.assertEqual(snapshot, before)
        self.assertEqual(
            first.model_dump_json(by_alias=True),
            second.model_dump_json(by_alias=True),
        )


class OperationalSnapshotDatabaseTests(DatabaseTestCase):
    def test_snapshot_uses_current_records_without_migration_inputs(
        self,
    ) -> None:
        inventory_item = InventoryItem(
            id="inventory-1",
            space_id=DEFAULT_SPACE_ID,
            name="Fasteners",
            category="Hardware",
            quantity=4,
            unit="boxes",
            minimum=1,
            location="Shelf",
            cost=0,
            supplier="",
            notes="",
            created_at=NOW,
            updated_at=NOW,
        )
        project_model = Project(
            id="project-1",
            space_id=DEFAULT_SPACE_ID,
            name="Workbench",
            type="build",
            status="active",
            priority="high",
            progress=10,
            estimated_cost=0,
            description="",
            notes="",
            created_at=NOW,
            updated_at=NOW,
        )
        project_model.material_requirements = [
            ProjectMaterialRequirement(
                inventory_item_id=inventory_item.id,
                required_quantity=2,
                note="",
            )
        ]
        task_model = Task(
            id="task-1",
            space_id=DEFAULT_SPACE_ID,
            title="Assemble top",
            priority="high",
            completed=False,
            project_id=project_model.id,
            created_at=NOW,
            updated_at=NOW,
        )
        migration = ProjectMigration(
            space_id=DEFAULT_SPACE_ID,
            source="browser-local",
            source_record_id="legacy-project",
            project_id=project_model.id,
            payload_hash="0" * 64,
            migrated_at=NOW,
        )
        self.session.add_all(
            [
                inventory_item,
                project_model,
                task_model,
                migration,
            ]
        )
        self.session.commit()
        self.assertFalse(self.session.in_transaction())

        snapshot = load_operational_snapshot(self.session)

        self.assertFalse(self.session.in_transaction())
        self.assertEqual(
            [record.id for record in snapshot.projects],
            ["project-1"],
        )
        self.assertEqual(
            [record.id for record in snapshot.tasks],
            ["task-1"],
        )
        self.assertEqual(
            [record.id for record in snapshot.inventory],
            ["inventory-1"],
        )
        self.assertEqual(
            snapshot.projects[0].material_requirements,
            (
                MaterialRequirementSnapshot(
                    inventory_item_id="inventory-1",
                    required_quantity=2,
                ),
            ),
        )
        result = derive_operational_facts(snapshot)
        self.assertEqual(
            {fact.fact_type for fact in result.facts},
            {
                "project.lifecycle",
                "project.material-readiness",
                "task.work-state",
                "inventory.stock-level",
            },
        )
        self.assertNotIn(
            "migration",
            result.model_dump_json(by_alias=True),
        )

    def test_calculation_does_not_persist_or_mutate_records(self) -> None:
        item = InventoryItem(
            id="inventory-1",
            space_id=DEFAULT_SPACE_ID,
            name="Oil",
            category="Vehicle",
            quantity=1,
            unit="quarts",
            minimum=2,
            location="Shed",
            cost=0,
            supplier="",
            notes="Original",
            created_at=NOW,
            updated_at=NOW,
        )
        self.session.add(item)
        self.session.commit()
        tables_before = set(inspect(engine).get_table_names())

        result = calculate_normalized_operational_facts(self.session)

        self.assertEqual(len(result.facts), 1)
        tables_after = set(inspect(engine).get_table_names())
        self.assertEqual(tables_after, tables_before)
        self.assertFalse(
            any("fact" in table for table in tables_after)
        )
        persisted = self.session.scalar(
            select(InventoryItem).where(
                InventoryItem.id == "inventory-1"
            )
        )
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.quantity, 1)
        self.assertEqual(persisted.minimum, 2)
        self.assertEqual(persisted.notes, "Original")

        with engine.connect() as connection:
            version = connection.exec_driver_sql(
                "PRAGMA user_version"
            ).scalar_one()
        self.assertEqual(version, CURRENT_DATABASE_SCHEMA_VERSION)
