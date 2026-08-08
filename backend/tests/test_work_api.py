from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from test_support import ApiTestCase


class WorkApiTests(ApiTestCase):
    async def create_space(self, name: str) -> dict:
        response = await self.client.post(
            "/api/spaces",
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    @staticmethod
    def headers(space_id: str) -> dict[str, str]:
        return {"X-Foreman-Space-Id": space_id}

    async def create_project(
        self,
        name: str,
        *,
        headers: dict[str, str] | None = None,
        **fields,
    ) -> dict:
        response = await self.client.post(
            "/api/projects",
            headers=headers,
            json={
                "name": name,
                **fields,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def create_task(
        self,
        title: str,
        *,
        headers: dict[str, str] | None = None,
        **fields,
    ) -> dict:
        response = await self.client.post(
            "/api/tasks",
            headers=headers,
            json={
                "title": title,
                **fields,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def create_dependency(
        self,
        dependent_type: str,
        dependent_id: str,
        prerequisite_type: str,
        prerequisite_id: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict:
        response = await self.client.post(
            "/api/work-dependencies",
            headers=headers,
            json={
                "dependentType": dependent_type,
                "dependentId": dependent_id,
                "prerequisiteType": prerequisite_type,
                "prerequisiteId": prerequisite_id,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_normalizes_tasks_projects_and_dependencies(
        self,
    ) -> None:
        project = await self.create_project(
            "Workbench",
            status="active",
            priority="urgent",
            progress=37.5,
            startDate="2026-08-01",
            targetDate="2026-08-31",
        )
        open_task = await self.create_task(
            "Cut parts",
            priority="high",
            projectId=project["id"],
            dueDate="2026-08-20",
        )
        completed_task = await self.create_task(
            "Assemble frame",
            priority="low",
        )

        completed = await self.client.post(
            f"/api/tasks/{completed_task['id']}/complete"
        )
        self.assertEqual(completed.status_code, 200)

        dependency = await self.create_dependency(
            "task",
            open_task["id"],
            "project",
            project["id"],
        )

        response = await self.client.get("/api/work")
        self.assertEqual(response.status_code, 200)
        work = response.json()

        self.assertEqual(
            [
                (item["recordType"], item["title"])
                for item in work["items"]
            ],
            [
                ("project", "Workbench"),
                ("task", "Assemble frame"),
                ("task", "Cut parts"),
            ],
        )

        items = {
            (item["recordType"], item["id"]): item
            for item in work["items"]
        }

        project_item = items[("project", project["id"])]
        self.assertEqual(project_item["title"], "Workbench")
        self.assertEqual(project_item["lifecycleState"], "active")
        self.assertEqual(project_item["priority"], "urgent")
        self.assertEqual(project_item["progress"], 37.5)
        self.assertEqual(project_item["startDate"], "2026-08-01")
        self.assertEqual(project_item["targetDate"], "2026-08-31")
        self.assertIsNone(project_item["dueDate"])
        self.assertIsNone(project_item["projectId"])

        open_item = items[("task", open_task["id"])]
        self.assertEqual(open_item["lifecycleState"], "open")
        self.assertEqual(open_item["progress"], 0.0)
        self.assertEqual(open_item["priority"], "high")
        self.assertEqual(open_item["dueDate"], "2026-08-20")
        self.assertEqual(open_item["projectId"], project["id"])
        self.assertIsNone(open_item["startDate"])
        self.assertIsNone(open_item["targetDate"])

        completed_item = items[
            ("task", completed_task["id"])
        ]
        self.assertEqual(
            completed_item["lifecycleState"],
            "completed",
        )
        self.assertEqual(completed_item["progress"], 100.0)

        self.assertEqual(work["dependencies"], [dependency])

        for item in work["items"]:
            self.assertNotIn("spaceId", item)

        for relationship in work["dependencies"]:
            self.assertNotIn("spaceId", relationship)

    async def test_archived_projects_remain_visible_in_work(
        self,
    ) -> None:
        project = await self.create_project("Retired Project")

        archived = await self.client.post(
            f"/api/projects/{project['id']}/archive"
        )
        self.assertEqual(archived.status_code, 200)

        native_projects = await self.client.get("/api/projects")
        self.assertEqual(native_projects.status_code, 200)
        self.assertNotIn(
            project["id"],
            [item["id"] for item in native_projects.json()],
        )

        work = (await self.client.get("/api/work")).json()
        project_items = {
            item["id"]: item
            for item in work["items"]
            if item["recordType"] == "project"
        }

        self.assertIn(project["id"], project_items)
        self.assertEqual(
            project_items[project["id"]]["lifecycleState"],
            "archived",
        )

    async def test_active_space_isolates_entire_work_read_model(
        self,
    ) -> None:
        default_project = await self.create_project(
            "Default Project"
        )
        default_task = await self.create_task(
            "Default Task"
        )
        default_dependency = await self.create_dependency(
            "task",
            default_task["id"],
            "project",
            default_project["id"],
        )

        other_space = await self.create_space("Other Space")
        other_headers = self.headers(other_space["id"])

        other_project = await self.create_project(
            "Other Project",
            headers=other_headers,
        )
        other_task = await self.create_task(
            "Other Task",
            headers=other_headers,
        )
        other_dependency = await self.create_dependency(
            "task",
            other_task["id"],
            "project",
            other_project["id"],
            headers=other_headers,
        )

        default_work = (
            await self.client.get("/api/work")
        ).json()
        other_work = (
            await self.client.get(
                "/api/work",
                headers=other_headers,
            )
        ).json()

        self.assertEqual(
            {item["id"] for item in default_work["items"]},
            {default_project["id"], default_task["id"]},
        )
        self.assertEqual(
            [item["id"] for item in default_work["dependencies"]],
            [default_dependency["id"]],
        )

        self.assertEqual(
            {item["id"] for item in other_work["items"]},
            {other_project["id"], other_task["id"]},
        )
        self.assertEqual(
            [item["id"] for item in other_work["dependencies"]],
            [other_dependency["id"]],
        )

    async def test_work_surface_is_read_only(self) -> None:
        requests = (
            self.client.post("/api/work", json={}),
            self.client.patch("/api/work", json={}),
            self.client.delete("/api/work"),
        )

        for request in requests:
            with self.subTest():
                response = await request
                self.assertEqual(response.status_code, 405)

    async def test_database_failure_is_controlled(self) -> None:
        with patch(
            "app.api.work.get_work",
            side_effect=SQLAlchemyError(
                "Private database path: /data/foreman.db"
            ),
        ):
            response = await self.client.get("/api/work")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"],
            "WORK_READ_MODEL_UNAVAILABLE",
        )
        self.assertNotIn(
            "/data/foreman.db",
            response.text,
        )
