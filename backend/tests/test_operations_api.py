import math
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal, engine
from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.models.project_migration import ProjectMigration
from app.services.operations import (
    InventorySnapshot,
    OperationalSnapshot,
    load_operational_snapshot,
)
from test_support import ApiTestCase


NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
TOP_LEVEL_FIELDS = {
    "schemaVersion",
    "facts",
    "summary",
    "activeProjects",
    "completedTasks",
    "incompleteTasks",
    "inventory",
    "projectStatusCounts",
    "taskPriorityCounts",
}
ZERO_SUMMARY = {
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
}


def find_fact(
    response: dict,
    fact_type: str,
    subject_id: str,
) -> dict:
    return next(
        fact
        for fact in response["facts"]
        if fact["factType"] == fact_type
        and fact["subjectId"] == subject_id
    )


class OperationalFactsApiTests(ApiTestCase):
    async def test_empty_operational_facts_have_complete_contract(
        self,
    ) -> None:
        tables_before = set(inspect(engine).get_table_names())

        response = await self.client.get("/api/operational-facts")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), TOP_LEVEL_FIELDS)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertIsInstance(payload["schemaVersion"], int)
        self.assertEqual(payload["facts"], [])
        self.assertEqual(payload["summary"], ZERO_SUMMARY)
        self.assertEqual(payload["activeProjects"], [])
        self.assertEqual(payload["completedTasks"], [])
        self.assertEqual(payload["incompleteTasks"], [])
        self.assertEqual(payload["inventory"], [])
        self.assertEqual(payload["projectStatusCounts"], {})
        self.assertEqual(
            payload["taskPriorityCounts"],
            {"high": 0, "medium": 0, "low": 0},
        )

        tables_after = set(inspect(engine).get_table_names())
        self.assertEqual(tables_after, tables_before)
        self.assertFalse(
            any("fact" in table_name for table_name in tables_after)
        )
        with engine.connect() as connection:
            version = connection.exec_driver_sql(
                "PRAGMA user_version"
            ).scalar_one()
        self.assertEqual(version, CURRENT_DATABASE_SCHEMA_VERSION)
        self.assertEqual(version, 2)

        status_response = await self.client.get("/api/status")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["version"], "0.7.3")
        unknown_response = await self.client.get(
            "/api/operational-facts/unknown"
        )
        self.assertEqual(unknown_response.status_code, 404)

    async def test_operational_facts_expose_normalized_and_legacy_state(
        self,
    ) -> None:
        inventory_response = await self.client.post(
            "/api/inventory",
            json={
                "name": "Shop Towels",
                "category": "Consumables",
                "quantity": 0,
                "unit": "rolls",
                "minimum": 2,
                "location": "Cabinet",
            },
        )
        self.assertEqual(inventory_response.status_code, 201)
        inventory = inventory_response.json()

        active_response = await self.client.post(
            "/api/projects",
            json={
                "name": "Active Build",
                "status": "active",
                "materials": [
                    {
                        "inventoryItemId": inventory["id"],
                        "requiredQuantity": 2,
                    }
                ],
            },
        )
        self.assertEqual(active_response.status_code, 201)
        active_project = active_response.json()
        planning_project = await self.create_project(
            name="Planning Build",
            status="planning",
        )

        incomplete_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Open task",
                "priority": "high",
                "projectId": active_project["id"],
            },
        )
        self.assertEqual(incomplete_response.status_code, 201)
        incomplete_task = incomplete_response.json()
        completed_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Finished task",
                "priority": "low",
            },
        )
        self.assertEqual(completed_response.status_code, 201)
        completed_task = completed_response.json()
        completion_response = await self.client.post(
            f"/api/tasks/{completed_task['id']}/complete"
        )
        self.assertEqual(completion_response.status_code, 200)

        with SessionLocal() as session:
            session.add(
                ProjectMigration(
                    source="browser-local",
                    source_record_id="legacy-project",
                    project_id=active_project["id"],
                    payload_hash="0" * 64,
                    migrated_at=NOW,
                )
            )
            session.commit()

        tables_before = set(inspect(engine).get_table_names())
        first_response = await self.client.get(
            "/api/operational-facts"
        )
        second_response = await self.client.get(
            "/api/operational-facts"
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        payload = first_response.json()
        repeated = second_response.json()
        self.assertEqual(set(payload), TOP_LEVEL_FIELDS)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["facts"], repeated["facts"])
        self.assertEqual(payload["summary"], repeated["summary"])

        fact_types = [fact["factType"] for fact in payload["facts"]]
        self.assertEqual(
            set(fact_types),
            {
                "project.lifecycle",
                "project.material-readiness",
                "task.work-state",
                "inventory.stock-level",
            },
        )
        canonical_order = {
            "project.lifecycle": 0,
            "project.material-readiness": 1,
            "task.work-state": 2,
            "inventory.stock-level": 3,
        }
        self.assertEqual(
            [canonical_order[fact_type] for fact_type in fact_types],
            sorted(canonical_order[fact_type] for fact_type in fact_types),
        )
        fact_ids = [fact["factId"] for fact in payload["facts"]]
        self.assertEqual(len(fact_ids), len(set(fact_ids)))

        lifecycle = find_fact(
            payload,
            "project.lifecycle",
            active_project["id"],
        )
        self.assertEqual(
            lifecycle["factId"],
            f"project/{active_project['id']}/lifecycle",
        )
        self.assertEqual(lifecycle["state"], "active")
        self.assertEqual(
            lifecycle["reasonCodes"],
            ["PROJECT_STATUS_ACTIVE"],
        )
        self.assertEqual(
            lifecycle["evidence"],
            {
                "persistedStatus": "active",
                "archivedAt": None,
            },
        )
        self.assertEqual(
            lifecycle["sourceRecords"][0]["recordType"],
            "project",
        )
        self.assertIn(
            "updatedAt",
            lifecycle["sourceRecords"][0],
        )

        readiness = find_fact(
            payload,
            "project.material-readiness",
            active_project["id"],
        )
        self.assertEqual(
            readiness["factId"],
            f"project/{active_project['id']}/material-readiness",
        )
        self.assertEqual(readiness["state"], "needs-materials")
        self.assertEqual(
            readiness["reasonCodes"],
            ["PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"],
        )
        self.assertEqual(
            readiness["evidence"]["requirements"],
            [
                {
                    "inventoryItemId": inventory["id"],
                    "itemName": "Shop Towels",
                    "unit": "rolls",
                    "requiredQuantity": 2.0,
                    "availableQuantity": 0.0,
                    "shortageQuantity": 2.0,
                    "reasonCode": (
                        "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"
                    ),
                }
            ],
        )
        self.assertEqual(
            [
                record["recordType"]
                for record in readiness["sourceRecords"]
            ],
            [
                "project",
                "project-material-requirement",
                "inventory",
            ],
        )

        open_fact = find_fact(
            payload,
            "task.work-state",
            incomplete_task["id"],
        )
        self.assertEqual(
            open_fact["factId"],
            f"task/{incomplete_task['id']}/work-state",
        )
        self.assertEqual(open_fact["state"], "open")
        self.assertEqual(
            open_fact["reasonCodes"],
            ["TASK_INCOMPLETE"],
        )
        self.assertEqual(
            open_fact["evidence"],
            {
                "priority": "high",
                "projectId": active_project["id"],
            },
        )

        stock_fact = find_fact(
            payload,
            "inventory.stock-level",
            inventory["id"],
        )
        self.assertEqual(
            stock_fact["factId"],
            f"inventory/{inventory['id']}/stock-level",
        )
        self.assertEqual(stock_fact["state"], "out-of-stock")
        self.assertEqual(
            stock_fact["reasonCodes"],
            ["INVENTORY_OUT_OF_STOCK"],
        )
        self.assertEqual(
            stock_fact["evidence"],
            {
                "quantity": 0.0,
                "minimum": 2.0,
                "unit": "rolls",
            },
        )

        self.assertEqual(
            payload["summary"],
            {
                "projects": {
                    "byStatus": {
                        "planning": 1,
                        "active": 1,
                        "onHold": 0,
                        "completed": 0,
                        "archived": 0,
                        "invalid": 0,
                    },
                    "materialReadiness": {
                        "ready": 0,
                        "needsMaterials": 1,
                        "notApplicable": 1,
                        "invalid": 0,
                    },
                },
                "tasks": {
                    "open": 1,
                    "completed": 1,
                    "byPriority": {
                        "high": 1,
                        "medium": 0,
                        "low": 1,
                    },
                },
                "inventory": {
                    "total": 1,
                    "inStock": 0,
                    "lowStock": 0,
                    "outOfStock": 1,
                    "lowOrOutOfStock": 1,
                    "invalid": 0,
                },
            },
        )

        self.assertEqual(
            [project["id"] for project in payload["activeProjects"]],
            [active_project["id"]],
        )
        self.assertEqual(
            [task["id"] for task in payload["incompleteTasks"]],
            [incomplete_task["id"]],
        )
        self.assertEqual(
            [task["id"] for task in payload["completedTasks"]],
            [completed_task["id"]],
        )
        self.assertEqual(
            payload["projectStatusCounts"],
            {"planning": 1, "active": 1},
        )
        self.assertEqual(
            payload["taskPriorityCounts"],
            {"high": 1, "medium": 0, "low": 1},
        )
        inventory_fact = payload["inventory"][0]
        self.assertEqual(inventory_fact["sourceModule"], "inventory")
        self.assertEqual(inventory_fact["recordId"], inventory["id"])
        self.assertEqual(inventory_fact["currentQuantity"], 0)
        self.assertEqual(inventory_fact["lowStockThreshold"], 2)
        self.assertTrue(inventory_fact["isLow"])
        self.assertTrue(inventory_fact["isOutOfStock"])
        self.assertEqual(inventory_fact["status"], "out-of-stock")
        self.assertTrue(inventory_fact["explanation"])

        serialized = first_response.text
        self.assertNotIn("browser-local", serialized)
        self.assertNotIn("legacy-project", serialized)
        self.assertNotIn("migration", serialized.lower())
        self.assertEqual(
            {
                record["recordType"]
                for fact in payload["facts"]
                for record in fact["sourceRecords"]
            },
            {
                "project",
                "project-material-requirement",
                "task",
                "inventory",
            },
        )
        self.assertEqual(
            set(inspect(engine).get_table_names()),
            tables_before,
        )
        self.assertNotIn("calculatedAt", payload)
        self.assertNotIn("generatedAt", payload)
        self.assertNotIn("applicationVersion", payload)
        self.assertNotIn("databaseVersion", payload)
        self.assertEqual(
            find_fact(
                payload,
                "project.lifecycle",
                planning_project["id"],
            )["reasonCodes"],
            ["PROJECT_STATUS_PLANNING"],
        )

    async def test_missing_inventory_serializes_unknown_availability(
        self,
    ) -> None:
        inventory_response = await self.client.post(
            "/api/inventory",
            json={
                "name": "Temporary Stock",
                "category": "Material",
                "quantity": 5,
                "unit": "pieces",
                "minimum": 1,
                "location": "Shelf",
            },
        )
        self.assertEqual(inventory_response.status_code, 201)
        inventory = inventory_response.json()
        project_response = await self.client.post(
            "/api/projects",
            json={
                "name": "Missing Reference Build",
                "status": "active",
                "materials": [
                    {
                        "inventoryItemId": inventory["id"],
                        "requiredQuantity": 3,
                    }
                ],
            },
        )
        self.assertEqual(project_response.status_code, 201)
        project = project_response.json()
        delete_response = await self.client.delete(
            f"/api/inventory/{inventory['id']}"
        )
        self.assertEqual(delete_response.status_code, 204)

        response = await self.client.get("/api/operational-facts")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        readiness = find_fact(
            payload,
            "project.material-readiness",
            project["id"],
        )
        self.assertEqual(readiness["state"], "needs-materials")
        self.assertEqual(
            readiness["reasonCodes"],
            ["PROJECT_MATERIAL_INVENTORY_MISSING"],
        )
        requirement = readiness["evidence"]["requirements"][0]
        self.assertIsNone(requirement["itemName"])
        self.assertIsNone(requirement["unit"])
        self.assertIsNone(requirement["availableQuantity"])
        self.assertIsNone(requirement["shortageQuantity"])
        self.assertNotEqual(requirement["availableQuantity"], 0)
        self.assertNotIn(
            "inventory",
            [
                record["recordType"]
                for record in readiness["sourceRecords"]
            ],
        )
        self.assertEqual(payload["inventory"], [])

    async def test_non_finite_evidence_is_json_safe_and_snapshot_once(
        self,
    ) -> None:
        snapshot = OperationalSnapshot(
            inventory=(
                InventorySnapshot(
                    id="infinity",
                    name="Infinite",
                    quantity=math.inf,
                    minimum=1,
                    unit="units",
                    updated_at=NOW,
                ),
                InventorySnapshot(
                    id="negative-infinity",
                    name="Negative Infinite",
                    quantity=-math.inf,
                    minimum=1,
                    unit="units",
                    updated_at=NOW,
                ),
                InventorySnapshot(
                    id="nan",
                    name="Not a Number",
                    quantity=math.nan,
                    minimum=1,
                    unit="units",
                    updated_at=NOW,
                ),
            )
        )
        with patch(
            "app.services.operations.load_operational_snapshot",
            return_value=snapshot,
        ) as snapshot_loader:
            response = await self.client.get(
                "/api/operational-facts"
            )

        self.assertEqual(response.status_code, 200)
        snapshot_loader.assert_called_once()
        payload = response.json()
        evidence = {
            fact["subjectId"]: fact["evidence"]["quantity"]
            for fact in payload["facts"]
        }
        self.assertEqual(
            evidence,
            {
                "infinity": "Infinity",
                "nan": "NaN",
                "negative-infinity": "-Infinity",
            },
        )
        self.assertEqual(payload["summary"]["inventory"]["invalid"], 3)
        self.assertNotIn(":NaN", response.text.replace(" ", ""))
        self.assertNotIn(":Infinity", response.text.replace(" ", ""))
        self.assertNotIn(":-Infinity", response.text.replace(" ", ""))

    async def test_each_request_loads_one_authoritative_snapshot(
        self,
    ) -> None:
        with patch(
            "app.services.operations.load_operational_snapshot",
            wraps=load_operational_snapshot,
        ) as snapshot_loader:
            response = await self.client.get(
                "/api/operational-facts"
            )

        self.assertEqual(response.status_code, 200)
        snapshot_loader.assert_called_once()

    async def test_database_failure_returns_non_sensitive_503(
        self,
    ) -> None:
        sensitive_text = (
            "sqlite3.OperationalError: no such table "
            "/private/foreman.db"
        )
        with patch(
            "app.api.operations.get_operational_facts",
            side_effect=SQLAlchemyError(sensitive_text),
        ):
            response = await self.client.get(
                "/api/operational-facts"
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "OPERATIONAL_FACTS_UNAVAILABLE",
                    "message": (
                        "Operational facts are temporarily unavailable."
                    ),
                }
            },
        )
        self.assertNotIn(sensitive_text, response.text)
        self.assertNotIn("sqlite", response.text.lower())
        self.assertNotIn("foreman.db", response.text)

    async def test_programmer_errors_are_not_mapped_to_503(self) -> None:
        with patch(
            "app.api.operations.get_operational_facts",
            side_effect=ValueError("response contract defect"),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "response contract defect",
            ):
                await self.client.get("/api/operational-facts")
