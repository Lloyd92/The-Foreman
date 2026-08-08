from app.core.database import SessionLocal
from app.models.work_dependency import WorkDependency
from test_support import ApiTestCase


class WorkDependencyApiTests(ApiTestCase):
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

    async def create_task(
        self,
        title: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict:
        response = await self.client.post(
            "/api/tasks",
            headers=headers,
            json={"title": title},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def create_project(
        self,
        name: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict:
        response = await self.client.post(
            "/api/projects",
            headers=headers,
            json={"name": name},
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
    ):
        return await self.client.post(
            "/api/work-dependencies",
            headers=headers,
            json={
                "dependentType": dependent_type,
                "dependentId": dependent_id,
                "prerequisiteType": prerequisite_type,
                "prerequisiteId": prerequisite_id,
            },
        )

    async def test_dependency_crud_is_factual_and_space_scoped(
        self,
    ) -> None:
        task = await self.create_task("Install top")
        project = await self.create_project("Build bench")

        created = await self.create_dependency(
            "task",
            task["id"],
            "project",
            project["id"],
        )
        self.assertEqual(created.status_code, 201)
        dependency = created.json()

        self.assertEqual(dependency["dependentType"], "task")
        self.assertEqual(dependency["dependentId"], task["id"])
        self.assertEqual(dependency["prerequisiteType"], "project")
        self.assertEqual(
            dependency["prerequisiteId"],
            project["id"],
        )
        self.assertIn("createdAt", dependency)
        self.assertNotIn("spaceId", dependency)

        with SessionLocal() as session:
            persisted = session.get(
                WorkDependency,
                dependency["id"],
            )
            self.assertIsNotNone(persisted)

        read = await self.client.get(
            f"/api/work-dependencies/{dependency['id']}"
        )
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), dependency)

        listed = await self.client.get("/api/work-dependencies")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [dependency])

        deleted = await self.client.delete(
            f"/api/work-dependencies/{dependency['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

        # Removing a relationship must not change either Work endpoint.
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/tasks/{task['id']}"
                )
            ).status_code,
            200,
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/projects/{project['id']}"
                )
            ).status_code,
            200,
        )

        missing = await self.client.get(
            f"/api/work-dependencies/{dependency['id']}"
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "WORK_DEPENDENCY_NOT_FOUND",
        )

    async def test_all_typed_endpoint_combinations_are_supported(
        self,
    ) -> None:
        task_a = await self.create_task("Task A")
        task_b = await self.create_task("Task B")
        task_c = await self.create_task("Task C")
        task_d = await self.create_task("Task D")

        project_a = await self.create_project("Project A")
        project_b = await self.create_project("Project B")
        project_c = await self.create_project("Project C")
        project_d = await self.create_project("Project D")

        combinations = (
            ("task", task_a["id"], "task", task_b["id"]),
            ("task", task_c["id"], "project", project_a["id"]),
            ("project", project_b["id"], "task", task_d["id"]),
            ("project", project_c["id"], "project", project_d["id"]),
        )

        for combination in combinations:
            with self.subTest(combination=combination):
                response = await self.create_dependency(*combination)
                self.assertEqual(response.status_code, 201)

        listed = await self.client.get("/api/work-dependencies")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 4)

    async def test_missing_and_cross_space_endpoints_are_rejected(
        self,
    ) -> None:
        default_task = await self.create_task("Default task")

        other_space = await self.create_space("Other Space")
        other_headers = self.headers(other_space["id"])
        other_project = await self.create_project(
            "Other project",
            headers=other_headers,
        )

        missing = await self.create_dependency(
            "task",
            default_task["id"],
            "project",
            "missing-project",
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "WORK_DEPENDENCY_ENDPOINT_NOT_FOUND",
        )

        cross_space = await self.create_dependency(
            "task",
            default_task["id"],
            "project",
            other_project["id"],
        )
        self.assertEqual(cross_space.status_code, 404)
        self.assertEqual(
            cross_space.json()["detail"]["code"],
            "WORK_DEPENDENCY_ENDPOINT_NOT_FOUND",
        )

        other_task = await self.create_task(
            "Other task",
            headers=other_headers,
        )
        created_other = await self.create_dependency(
            "task",
            other_task["id"],
            "project",
            other_project["id"],
            headers=other_headers,
        )
        self.assertEqual(created_other.status_code, 201)

        default_list = await self.client.get(
            "/api/work-dependencies"
        )
        self.assertEqual(default_list.status_code, 200)
        self.assertEqual(default_list.json(), [])

        inaccessible = await self.client.get(
            (
                "/api/work-dependencies/"
                f"{created_other.json()['id']}"
            )
        )
        self.assertEqual(inaccessible.status_code, 404)
        self.assertEqual(
            inaccessible.json()["detail"]["code"],
            "WORK_DEPENDENCY_NOT_FOUND",
        )

        inaccessible_delete = await self.client.delete(
            (
                "/api/work-dependencies/"
                f"{created_other.json()['id']}"
            )
        )
        self.assertEqual(inaccessible_delete.status_code, 404)

        still_present = await self.client.get(
            (
                "/api/work-dependencies/"
                f"{created_other.json()['id']}"
            ),
            headers=other_headers,
        )
        self.assertEqual(still_present.status_code, 200)

    async def test_duplicate_and_self_dependencies_are_controlled(
        self,
    ) -> None:
        task = await self.create_task("Dependent task")
        project = await self.create_project("Prerequisite project")

        first = await self.create_dependency(
            "task",
            task["id"],
            "project",
            project["id"],
        )
        self.assertEqual(first.status_code, 201)

        duplicate = await self.create_dependency(
            "task",
            task["id"],
            "project",
            project["id"],
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"]["code"],
            "WORK_DEPENDENCY_ALREADY_EXISTS",
        )

        self_reference = await self.create_dependency(
            "task",
            task["id"],
            "task",
            task["id"],
        )
        self.assertEqual(self_reference.status_code, 409)
        self.assertEqual(
            self_reference.json()["detail"]["code"],
            "WORK_DEPENDENCY_SELF_REFERENCE",
        )

        listed = await self.client.get("/api/work-dependencies")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

    async def test_transitive_mixed_type_cycle_is_rejected(
        self,
    ) -> None:
        task_a = await self.create_task("Task A")
        project_b = await self.create_project("Project B")
        task_c = await self.create_task("Task C")

        first = await self.create_dependency(
            "task",
            task_a["id"],
            "project",
            project_b["id"],
        )
        second = await self.create_dependency(
            "project",
            project_b["id"],
            "task",
            task_c["id"],
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        # Existing graph:
        # Task A -> Project B -> Task C
        # Adding Task C -> Task A would close the cycle.
        cycle = await self.create_dependency(
            "task",
            task_c["id"],
            "task",
            task_a["id"],
        )
        self.assertEqual(cycle.status_code, 409)
        self.assertEqual(
            cycle.json()["detail"]["code"],
            "WORK_DEPENDENCY_CYCLE",
        )

        listed = await self.client.get("/api/work-dependencies")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 2)

    async def test_dependency_payload_boundaries(self) -> None:
        invalid_payloads = (
            {
                "dependentType": "goal",
                "dependentId": "work-a",
                "prerequisiteType": "task",
                "prerequisiteId": "work-b",
            },
            {
                "dependentType": "task",
                "dependentId": "",
                "prerequisiteType": "project",
                "prerequisiteId": "work-b",
            },
            {
                "dependentType": "task",
                "dependentId": "work-a",
                "prerequisiteType": "project",
                "prerequisiteId": "work-b",
                "spaceId": "client-space",
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = await self.client.post(
                    "/api/work-dependencies",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)
