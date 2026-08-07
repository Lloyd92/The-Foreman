from unittest.mock import patch

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.project import Project
from app.models.space import Space
from app.schemas.project import ProjectUpdate
from app.services.projects import update_project
from test_inventory_api import inventory_payload
from test_support import ApiTestCase


class ProjectApiTests(ApiTestCase):
    async def create_inventory(self, name: str) -> dict:
        response = await self.client.post(
            "/api/inventory",
            json=inventory_payload(name=name),
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_complete_project_crud(self) -> None:
        inventory = await self.create_inventory("Birch Plywood")
        create_response = await self.client.post(
            "/api/projects",
            json={
                "name": "Workbench Build",
                "type": "build",
                "status": "active",
                "priority": "high",
                "progress": 20.5,
                "startDate": "2026-07-01",
                "targetDate": "2026-08-15",
                "estimatedCost": 425.75,
                "description": "Build an assembly workbench.",
                "notes": "Shop project",
                "materials": [
                    {
                        "inventoryItemId": inventory["id"],
                        "requiredQuantity": 1.25,
                        "note": "Top and shelf",
                    }
                ],
            },
        )

        self.assertEqual(create_response.status_code, 201)
        project = create_response.json()
        self.assertNotIn("spaceId", project)

        with SessionLocal() as session:
            self.assertEqual(
                session.scalar(
                    select(Project.space_id).where(
                        Project.id == project["id"]
                    )
                ),
                DEFAULT_SPACE_ID,
            )

        self.assertEqual(project["type"], "build")
        self.assertEqual(project["priority"], "high")
        self.assertEqual(project["startDate"], "2026-07-01")
        self.assertEqual(project["targetDate"], "2026-08-15")
        self.assertAlmostEqual(project["estimatedCost"], 425.75)
        self.assertEqual(project["description"], "Build an assembly workbench.")
        self.assertEqual(len(project["materials"]), 1)
        self.assertAlmostEqual(
            project["materials"][0]["requiredQuantity"],
            1.25,
        )

        updated = await self.client.patch(
            f"/api/projects/{project['id']}",
            json={
                "name": "Assembly Workbench",
                "type": "internal",
                "priority": "urgent",
                "progress": 45.25,
                "startDate": None,
                "estimatedCost": 500.1,
                "description": "Updated description",
            },
        )
        self.assertEqual(updated.status_code, 200)
        updated_project = updated.json()
        self.assertEqual(updated_project["name"], "Assembly Workbench")
        self.assertEqual(updated_project["type"], "internal")
        self.assertEqual(updated_project["priority"], "urgent")
        self.assertIsNone(updated_project["startDate"])
        self.assertAlmostEqual(updated_project["estimatedCost"], 500.1)
        self.assertNotEqual(
            updated_project["updatedAt"],
            project["updatedAt"],
        )

        read_response = await self.client.get(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(
            read_response.json()["description"],
            "Updated description",
        )

        deleted = await self.client.delete(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual((await self.client.get("/api/projects")).json(), [])

    async def test_material_response_order_uses_inventory_name_then_id(
        self,
    ) -> None:
        zulu = await self.create_inventory("Zulu Plywood")
        alpha = await self.create_inventory("Alpha Hardware")
        project = (
            await self.client.post(
                "/api/projects",
                json={
                    "name": "Ordered Materials",
                    "materials": [
                        {
                            "inventoryItemId": zulu["id"],
                            "requiredQuantity": 0.3,
                        },
                        {
                            "inventoryItemId": alpha["id"],
                            "requiredQuantity": 0.1,
                        },
                    ],
                },
            )
        ).json()

        self.assertEqual(
            [
                material["inventoryItemId"]
                for material in project["materials"]
            ],
            [alpha["id"], zulu["id"]],
        )

        await self.client.delete(f"/api/inventory/{alpha['id']}")
        with_missing = (
            await self.client.get(f"/api/projects/{project['id']}")
        ).json()
        self.assertEqual(
            [
                material["inventoryItemId"]
                for material in with_missing["materials"]
            ],
            [zulu["id"], alpha["id"]],
        )

    async def test_material_crud_and_missing_reference_edit(self) -> None:
        inventory = await self.create_inventory("Steel Tube")
        project = await self.create_project()
        added = await self.client.post(
            f"/api/projects/{project['id']}/materials",
            json={
                "inventoryItemId": inventory["id"],
                "requiredQuantity": 0.1,
                "note": "Original",
            },
        )
        self.assertEqual(added.status_code, 200)
        added_project = added.json()
        self.assertAlmostEqual(
            added_project["materials"][0]["requiredQuantity"],
            0.1,
        )

        duplicate = await self.client.post(
            f"/api/projects/{project['id']}/materials",
            json={
                "inventoryItemId": inventory["id"],
                "requiredQuantity": 1,
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        await self.client.delete(f"/api/inventory/{inventory['id']}")
        edited = await self.client.patch(
            (
                f"/api/projects/{project['id']}/materials/"
                f"{inventory['id']}"
            ),
            json={
                "requiredQuantity": 1.25,
                "note": "Inventory reference is now missing",
            },
        )
        self.assertEqual(edited.status_code, 200)
        edited_project = edited.json()
        self.assertAlmostEqual(
            edited_project["materials"][0]["requiredQuantity"],
            1.25,
        )
        self.assertEqual(
            edited_project["materials"][0]["note"],
            "Inventory reference is now missing",
        )
        self.assertNotEqual(
            edited_project["updatedAt"],
            added_project["updatedAt"],
        )

        removed = await self.client.delete(
            (
                f"/api/projects/{project['id']}/materials/"
                f"{inventory['id']}"
            )
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()["materials"], [])

    async def test_normal_material_creation_rejects_missing_inventory(
        self,
    ) -> None:
        project = await self.create_project()
        response = await self.client.post(
            f"/api/projects/{project['id']}/materials",
            json={
                "inventoryItemId": "missing-inventory",
                "requiredQuantity": 1,
            },
        )
        self.assertEqual(response.status_code, 409)
        unchanged = (
            await self.client.get(f"/api/projects/{project['id']}")
        ).json()
        self.assertEqual(unchanged["materials"], [])

        create_response = await self.client.post(
            "/api/projects",
            json={
                "name": "Invalid material",
                "materials": [
                    {
                        "inventoryItemId": "missing-inventory",
                        "requiredQuantity": 1,
                    }
                ],
            },
        )
        self.assertEqual(create_response.status_code, 409)

    async def test_validation_failure_does_not_change_timestamp(self) -> None:
        project = await self.create_project()
        before = (
            await self.client.get(f"/api/projects/{project['id']}")
        ).json()
        invalid = await self.client.patch(
            f"/api/projects/{project['id']}",
            json={"progress": 101},
        )
        self.assertEqual(invalid.status_code, 422)
        after = (
            await self.client.get(f"/api/projects/{project['id']}")
        ).json()
        self.assertEqual(after["updatedAt"], before["updatedAt"])

    async def test_rolled_back_update_does_not_change_timestamp(self) -> None:
        project = await self.create_project()
        original_timestamp = project["updatedAt"]

        with SessionLocal() as session:
            with patch.object(
                session,
                "commit",
                side_effect=RuntimeError("forced commit failure"),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "forced commit failure",
                ):
                    update_project(
                        session,
                        Space(
                            id=DEFAULT_SPACE_ID,
                            name="HardHead Works",
                        ),
                        project["id"],
                        ProjectUpdate(name="Rolled back name"),
                    )

        stored = (
            await self.client.get(f"/api/projects/{project['id']}")
        ).json()
        self.assertEqual(stored["name"], project["name"])
        self.assertEqual(stored["updatedAt"], original_timestamp)

    async def test_project_archive_compatibility_and_deletion(self) -> None:
        project = await self.create_project(status="active")
        archive_response = await self.client.post(
            f"/api/projects/{project['id']}/archive"
        )
        self.assertEqual(archive_response.status_code, 200)
        self.assertEqual(archive_response.json()["status"], "archived")
        self.assertIsNotNone(archive_response.json()["archivedAt"])
        self.assertEqual((await self.client.get("/api/projects")).json(), [])
        full_list = await self.client.get(
            "/api/projects",
            params={"includeArchived": "true"},
        )
        self.assertEqual(len(full_list.json()), 1)

        rejected_update = await self.client.patch(
            f"/api/projects/{project['id']}",
            json={"name": "Not allowed"},
        )
        self.assertEqual(rejected_update.status_code, 409)

        deleted = await self.client.delete(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            (
                await self.client.get(
                    "/api/projects",
                    params={"includeArchived": "true"},
                )
            ).json(),
            [],
        )

    async def test_project_validation_errors_are_clear(self) -> None:
        invalid_payloads = (
            {"name": ""},
            {"name": "Invalid", "progress": 101},
            {"name": "   "},
            {"name": "Invalid", "status": "archived"},
            {"name": "Invalid", "estimatedCost": -0.01},
            {"name": "Invalid", "type": "unknown"},
            {"name": "Invalid", "priority": "unknown"},
            {"name": "Client scoped", "spaceId": "client-space"},
            {
                "name": "Duplicate materials",
                "materials": [
                    {
                        "inventoryItemId": "same-id",
                        "requiredQuantity": 1,
                    },
                    {
                        "inventoryItemId": "same-id",
                        "requiredQuantity": 2,
                    },
                ],
            },
        )

        for payload in invalid_payloads:
            response = await self.client.post(
                "/api/projects",
                json=payload,
            )
            self.assertEqual(response.status_code, 422, payload)

        empty_update = await self.client.patch(
            "/api/projects/not-found",
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

    async def test_missing_project_returns_not_found(self) -> None:
        response = await self.client.get("/api/projects/not-found")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Project not found.")
