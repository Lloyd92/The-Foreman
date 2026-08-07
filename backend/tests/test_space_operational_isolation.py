from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.inventory import InventoryItem
from app.models.inventory_migration import InventoryMigration
from app.models.project import Project
from app.models.project_migration import ProjectMigration
from app.models.task import Task
from app.models.task_migration import TaskMigration
from test_inventory_api import inventory_payload
from test_inventory_migrations import browser_inventory
from test_project_migrations import migration_payload
from test_support import ApiTestCase
from test_task_migrations import browser_task


class SpaceOperationalIsolationTests(ApiTestCase):
    async def create_space(self, name: str = "Workshop") -> dict:
        response = await self.client.post(
            "/api/spaces",
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    @staticmethod
    def headers(space_id: str) -> dict[str, str]:
        return {"X-Foreman-Space-Id": space_id}

    async def test_crud_isolated_by_active_space(self) -> None:
        space = await self.create_space()
        headers = self.headers(space["id"])

        task = (
            await self.client.post(
                "/api/tasks",
                headers=headers,
                json={
                    "title": "Workshop task",
                    "priority": "high",
                },
            )
        ).json()
        inventory = (
            await self.client.post(
                "/api/inventory",
                headers=headers,
                json=inventory_payload(name="Workshop inventory"),
            )
        ).json()
        project = (
            await self.client.post(
                "/api/projects",
                headers=headers,
                json={
                    "name": "Workshop project",
                    "status": "active",
                },
            )
        ).json()

        for payload in (task, inventory, project):
            self.assertNotIn("spaceId", payload)

        self.assertEqual((await self.client.get("/api/tasks")).json(), [])
        self.assertEqual(
            (await self.client.get("/api/inventory")).json(),
            [],
        )
        self.assertEqual(
            (await self.client.get("/api/projects")).json(),
            [],
        )

        self.assertEqual(
            (
                await self.client.get(
                    f"/api/tasks/{task['id']}"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/inventory/{inventory['id']}"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/projects/{project['id']}"
                )
            ).status_code,
            404,
        )

        self.assertEqual(
            (
                await self.client.patch(
                    f"/api/tasks/{task['id']}",
                    json={"title": "Leaked task update"},
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    f"/api/inventory/{inventory['id']}",
                    json={"quantity": 99},
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    f"/api/projects/{project['id']}",
                    json={"name": "Leaked project update"},
                )
            ).status_code,
            404,
        )

        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/tasks/{task['id']}"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/inventory/{inventory['id']}"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/projects/{project['id']}"
                )
            ).status_code,
            404,
        )

        selected_task = await self.client.get(
            f"/api/tasks/{task['id']}",
            headers=headers,
        )
        selected_inventory = await self.client.get(
            f"/api/inventory/{inventory['id']}",
            headers=headers,
        )
        selected_project = await self.client.get(
            f"/api/projects/{project['id']}",
            headers=headers,
        )

        self.assertEqual(selected_task.status_code, 200)
        self.assertEqual(selected_inventory.status_code, 200)
        self.assertEqual(selected_project.status_code, 200)
        self.assertEqual(
            selected_task.json()["title"],
            "Workshop task",
        )
        self.assertEqual(
            selected_inventory.json()["quantity"],
            8,
        )
        self.assertEqual(
            selected_project.json()["name"],
            "Workshop project",
        )

    async def test_cross_space_relationships_are_rejected(self) -> None:
        space = await self.create_space()
        headers = self.headers(space["id"])

        default_project = await self.create_project(
            name="Default project",
            status="active",
        )
        default_inventory = (
            await self.client.post(
                "/api/inventory",
                json=inventory_payload(name="Default inventory"),
            )
        ).json()

        rejected_task_create = await self.client.post(
            "/api/tasks",
            headers=headers,
            json={
                "title": "Cross-Space task",
                "projectId": default_project["id"],
            },
        )
        self.assertEqual(rejected_task_create.status_code, 404)
        self.assertEqual(
            rejected_task_create.json()["detail"],
            "Project not found.",
        )

        workshop_task = (
            await self.client.post(
                "/api/tasks",
                headers=headers,
                json={"title": "Workshop task"},
            )
        ).json()
        rejected_task_update = await self.client.patch(
            f"/api/tasks/{workshop_task['id']}",
            headers=headers,
            json={"projectId": default_project["id"]},
        )
        self.assertEqual(rejected_task_update.status_code, 404)
        self.assertEqual(
            rejected_task_update.json()["detail"],
            "Project not found.",
        )

        rejected_project_create = await self.client.post(
            "/api/projects",
            headers=headers,
            json={
                "name": "Cross-Space materials",
                "materials": [
                    {
                        "inventoryItemId": default_inventory["id"],
                        "requiredQuantity": 1,
                    }
                ],
            },
        )
        self.assertEqual(rejected_project_create.status_code, 409)
        self.assertEqual(
            rejected_project_create.json()["detail"],
            "Inventory item not found.",
        )

        workshop_project = (
            await self.client.post(
                "/api/projects",
                headers=headers,
                json={"name": "Workshop project"},
            )
        ).json()
        rejected_material_add = await self.client.post(
            f"/api/projects/{workshop_project['id']}/materials",
            headers=headers,
            json={
                "inventoryItemId": default_inventory["id"],
                "requiredQuantity": 1,
            },
        )
        self.assertEqual(rejected_material_add.status_code, 409)
        self.assertEqual(
            rejected_material_add.json()["detail"],
            "Inventory item not found.",
        )

        workshop_inventory = (
            await self.client.post(
                "/api/inventory",
                headers=headers,
                json=inventory_payload(name="Workshop inventory"),
            )
        ).json()
        accepted_material = await self.client.post(
            f"/api/projects/{workshop_project['id']}/materials",
            headers=headers,
            json={
                "inventoryItemId": workshop_inventory["id"],
                "requiredQuantity": 2,
            },
        )
        self.assertEqual(accepted_material.status_code, 200)

        accepted_task = await self.client.patch(
            f"/api/tasks/{workshop_task['id']}",
            headers=headers,
            json={"projectId": workshop_project["id"]},
        )
        self.assertEqual(accepted_task.status_code, 200)
        self.assertEqual(
            accepted_task.json()["projectId"],
            workshop_project["id"],
        )

    async def test_operational_facts_are_space_isolated(self) -> None:
        space = await self.create_space()
        headers = self.headers(space["id"])

        default_inventory = (
            await self.client.post(
                "/api/inventory",
                json=inventory_payload(name="Default stock"),
            )
        ).json()
        default_project = await self.create_project(
            name="Default active",
            status="active",
        )
        default_task = (
            await self.client.post(
                "/api/tasks",
                json={
                    "title": "Default task",
                    "priority": "high",
                    "projectId": default_project["id"],
                },
            )
        ).json()

        workshop_inventory = (
            await self.client.post(
                "/api/inventory",
                headers=headers,
                json=inventory_payload(name="Workshop stock"),
            )
        ).json()
        workshop_project = (
            await self.client.post(
                "/api/projects",
                headers=headers,
                json={
                    "name": "Workshop active",
                    "status": "active",
                },
            )
        ).json()
        workshop_task = (
            await self.client.post(
                "/api/tasks",
                headers=headers,
                json={
                    "title": "Workshop task",
                    "priority": "low",
                    "projectId": workshop_project["id"],
                },
            )
        ).json()

        default_facts = (
            await self.client.get("/api/operational-facts")
        ).json()
        workshop_response = await self.client.get(
            "/api/operational-facts",
            headers=headers,
        )
        self.assertEqual(workshop_response.status_code, 200)
        workshop_facts = workshop_response.json()

        default_subjects = {
            fact["subjectId"]
            for fact in default_facts["facts"]
        }
        workshop_subjects = {
            fact["subjectId"]
            for fact in workshop_facts["facts"]
        }

        self.assertIn(default_project["id"], default_subjects)
        self.assertIn(default_task["id"], default_subjects)
        self.assertIn(default_inventory["id"], default_subjects)
        self.assertNotIn(workshop_project["id"], default_subjects)
        self.assertNotIn(workshop_task["id"], default_subjects)
        self.assertNotIn(workshop_inventory["id"], default_subjects)

        self.assertIn(workshop_project["id"], workshop_subjects)
        self.assertIn(workshop_task["id"], workshop_subjects)
        self.assertIn(workshop_inventory["id"], workshop_subjects)
        self.assertNotIn(default_project["id"], workshop_subjects)
        self.assertNotIn(default_task["id"], workshop_subjects)
        self.assertNotIn(default_inventory["id"], workshop_subjects)

        self.assertEqual(
            workshop_facts["summary"]["projects"]["byStatus"]["active"],
            1,
        )
        self.assertEqual(
            workshop_facts["summary"]["tasks"]["open"],
            1,
        )
        self.assertEqual(
            workshop_facts["summary"]["inventory"]["total"],
            1,
        )
        self.assertNotIn("spaceId", workshop_response.text)

    async def test_browser_migrations_use_active_space(self) -> None:
        space = await self.create_space()
        headers = self.headers(space["id"])

        task_record = browser_task(
            "20000000-0000-4000-8000-000000000001"
        )
        inventory_record = browser_inventory(
            "30000000-0000-4000-8000-000000000001"
        )
        project_data = migration_payload(
            "space-isolation-project"
        )

        task_response = await self.client.post(
            "/api/task-migrations/browser",
            headers=headers,
            json={"records": [task_record]},
        )
        inventory_response = await self.client.post(
            "/api/inventory-migrations/browser",
            headers=headers,
            json={"records": [inventory_record]},
        )
        project_response = await self.client.post(
            "/api/project-migrations/browser",
            headers=headers,
            json=project_data,
        )

        self.assertEqual(task_response.status_code, 200)
        self.assertEqual(task_response.json()["migrated"], 1)
        self.assertEqual(inventory_response.status_code, 200)
        self.assertEqual(inventory_response.json()["migrated"], 1)
        self.assertEqual(project_response.status_code, 201)
        project_id = project_response.json()["id"]

        with SessionLocal() as session:
            task = session.scalar(
                select(Task).where(Task.id == task_record["id"])
            )
            inventory = session.scalar(
                select(InventoryItem).where(
                    InventoryItem.id == inventory_record["id"]
                )
            )
            project = session.scalar(
                select(Project).where(Project.id == project_id)
            )
            task_migration = session.scalar(
                select(TaskMigration).where(
                    TaskMigration.source_record_id
                    == task_record["id"]
                )
            )
            inventory_migration = session.scalar(
                select(InventoryMigration).where(
                    InventoryMigration.source_record_id
                    == inventory_record["id"]
                )
            )
            project_migration = session.scalar(
                select(ProjectMigration).where(
                    ProjectMigration.source_record_id
                    == project_data["sourceRecordId"]
                )
            )

            self.assertEqual(task.space_id, space["id"])
            self.assertEqual(inventory.space_id, space["id"])
            self.assertEqual(project.space_id, space["id"])
            self.assertEqual(task_migration.space_id, space["id"])
            self.assertEqual(
                inventory_migration.space_id,
                space["id"],
            )
            self.assertEqual(
                project_migration.space_id,
                space["id"],
            )

        self.assertEqual((await self.client.get("/api/tasks")).json(), [])
        self.assertEqual(
            (await self.client.get("/api/inventory")).json(),
            [],
        )
        self.assertEqual(
            (await self.client.get("/api/projects")).json(),
            [],
        )

        self.assertEqual(
            len(
                (
                    await self.client.get(
                        "/api/tasks",
                        headers=headers,
                    )
                ).json()
            ),
            1,
        )
        self.assertEqual(
            len(
                (
                    await self.client.get(
                        "/api/inventory",
                        headers=headers,
                    )
                ).json()
            ),
            1,
        )
        self.assertEqual(
            len(
                (
                    await self.client.get(
                        "/api/projects",
                        headers=headers,
                    )
                ).json()
            ),
            1,
        )

    async def test_global_migration_provenance_does_not_leak_space(
        self,
    ) -> None:
        space = await self.create_space()
        headers = self.headers(space["id"])

        task_record = browser_task(
            "20000000-0000-4000-8000-000000000002"
        )
        inventory_record = browser_inventory(
            "30000000-0000-4000-8000-000000000002"
        )
        project_data = migration_payload(
            "space-provenance-project"
        )

        await self.client.post(
            "/api/task-migrations/browser",
            headers=headers,
            json={"records": [task_record]},
        )
        await self.client.post(
            "/api/inventory-migrations/browser",
            headers=headers,
            json={"records": [inventory_record]},
        )
        await self.client.post(
            "/api/project-migrations/browser",
            headers=headers,
            json=project_data,
        )

        task_retry = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [task_record]},
        )
        inventory_retry = await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [inventory_record]},
        )
        project_retry = await self.client.post(
            "/api/project-migrations/browser",
            json=project_data,
        )

        self.assertEqual(task_retry.status_code, 200)
        self.assertEqual(task_retry.json()["status"], "failed")
        self.assertEqual(task_retry.json()["migrated"], 0)
        self.assertEqual(task_retry.json()["alreadyMigrated"], 0)
        self.assertEqual(task_retry.json()["skipped"], 1)
        self.assertIn(
            "another Space",
            task_retry.json()["errors"][0]["reason"],
        )

        self.assertEqual(inventory_retry.status_code, 200)
        self.assertEqual(inventory_retry.json()["status"], "failed")
        self.assertEqual(inventory_retry.json()["migrated"], 0)
        self.assertEqual(
            inventory_retry.json()["alreadyMigrated"],
            0,
        )
        self.assertEqual(inventory_retry.json()["duplicates"], 1)
        self.assertIn(
            "another Space",
            inventory_retry.json()["errors"][0]["reason"],
        )

        self.assertEqual(project_retry.status_code, 409)
        self.assertIn(
            "another Space",
            project_retry.json()["detail"],
        )

        self.assertEqual((await self.client.get("/api/tasks")).json(), [])
        self.assertEqual(
            (await self.client.get("/api/inventory")).json(),
            [],
        )
        self.assertEqual(
            (await self.client.get("/api/projects")).json(),
            [],
        )

    async def test_migrations_reject_cross_space_relationships(
        self,
    ) -> None:
        space = await self.create_space()
        headers = self.headers(space["id"])

        default_project = await self.create_project(
            name="Default migration project",
            status="active",
        )
        default_inventory = (
            await self.client.post(
                "/api/inventory",
                json=inventory_payload(name="Default migration stock"),
            )
        ).json()

        task_record = browser_task(
            "20000000-0000-4000-8000-000000000003"
        )
        task_record["projectId"] = default_project["id"]

        task_response = await self.client.post(
            "/api/task-migrations/browser",
            headers=headers,
            json={"records": [task_record]},
        )
        self.assertEqual(task_response.status_code, 200)
        self.assertEqual(task_response.json()["status"], "failed")
        self.assertEqual(task_response.json()["migrated"], 0)
        self.assertEqual(task_response.json()["skipped"], 1)
        self.assertIn(
            "Project not found",
            task_response.json()["errors"][0]["reason"],
        )

        project_data = migration_payload(
            "cross-space-material-project",
            materials=[
                {
                    "inventoryItemId": default_inventory["id"],
                    "requiredQuantity": 1,
                }
            ],
        )
        project_response = await self.client.post(
            "/api/project-migrations/browser",
            headers=headers,
            json=project_data,
        )
        self.assertEqual(project_response.status_code, 409)
        self.assertEqual(
            project_response.json()["detail"],
            "Inventory item not found.",
        )
