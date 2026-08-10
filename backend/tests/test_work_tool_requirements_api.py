from test_support import ApiTestCase


def tool_payload(
    name: str = "Circular Saw",
) -> dict:
    return {
        "name": name,
        "category": "Power Tools",
        "condition": "good",
        "location": "Workshop",
        "availability": "available",
        "notes": "",
    }


class WorkToolRequirementApiTests(ApiTestCase):
    async def create_tool(
        self,
        name: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict:
        response = await self.client.post(
            "/api/tools",
            headers=headers,
            json=tool_payload(name),
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

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

    async def create_requirement(
        self,
        work_type: str,
        work_id: str,
        tool_id: str,
        *,
        note: str = "",
        headers: dict[str, str] | None = None,
    ) -> dict:
        response = await self.client.post(
            "/api/work-tool-requirements",
            headers=headers,
            json={
                "workType": work_type,
                "workId": work_id,
                "toolId": tool_id,
                "note": note,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_task_and_project_requirements_are_authoritative(
        self,
    ) -> None:
        tool = await self.create_tool("Track Saw")
        task = await self.create_task("Cut cabinet panels")
        project = await self.create_project("Cabinet Build")

        task_requirement = await self.create_requirement(
            "task",
            task["id"],
            tool["id"],
            note="Required for panel cuts",
        )
        project_requirement = await self.create_requirement(
            "project",
            project["id"],
            tool["id"],
            note="Primary cutting tool",
        )

        self.assertNotIn("spaceId", task_requirement)
        self.assertTrue(task_requirement["toolExists"])
        self.assertEqual(
            task_requirement["toolName"],
            "Track Saw",
        )
        self.assertTrue(
            task_requirement["createdAt"].endswith("Z")
        )

        filtered = await self.client.get(
            "/api/work-tool-requirements",
            params={
                "workType": "task",
                "workId": task["id"],
            },
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(
            [
                item["id"]
                for item in filtered.json()
            ],
            [task_requirement["id"]],
        )

        read = await self.client.get(
            (
                "/api/work-tool-requirements/"
                f"{project_requirement['id']}"
            )
        )
        self.assertEqual(read.status_code, 200)

        updated = await self.client.patch(
            (
                "/api/work-tool-requirements/"
                f"{task_requirement['id']}"
            ),
            json={"note": "Updated factual requirement"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["note"],
            "Updated factual requirement",
        )

    async def test_missing_tool_remains_evidence_and_can_be_replaced(
        self,
    ) -> None:
        original_tool = await self.create_tool("Old Drill")
        task = await self.create_task("Drill mounting holes")

        requirement = await self.create_requirement(
            "task",
            task["id"],
            original_tool["id"],
        )

        deleted = await self.client.delete(
            f"/api/tools/{original_tool['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

        missing = (
            await self.client.get(
                (
                    "/api/work-tool-requirements/"
                    f"{requirement['id']}"
                )
            )
        ).json()

        self.assertEqual(
            missing["toolId"],
            original_tool["id"],
        )
        self.assertFalse(missing["toolExists"])
        self.assertIsNone(missing["toolName"])

        note_update = await self.client.patch(
            (
                "/api/work-tool-requirements/"
                f"{requirement['id']}"
            ),
            json={"note": "Referenced Tool was removed"},
        )
        self.assertEqual(note_update.status_code, 200)
        self.assertFalse(
            note_update.json()["toolExists"]
        )

        replacement = await self.create_tool(
            "Replacement Drill"
        )

        replaced = await self.client.patch(
            (
                "/api/work-tool-requirements/"
                f"{requirement['id']}"
            ),
            json={"toolId": replacement["id"]},
        )
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(
            replaced.json()["toolId"],
            replacement["id"],
        )
        self.assertEqual(
            replaced.json()["toolName"],
            "Replacement Drill",
        )
        self.assertTrue(
            replaced.json()["toolExists"]
        )

    async def test_creation_validates_space_and_duplicates(
        self,
    ) -> None:
        tool = await self.create_tool("Router")
        task = await self.create_task("Route edge")

        await self.create_requirement(
            "task",
            task["id"],
            tool["id"],
        )

        duplicate = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "task",
                "workId": task["id"],
                "toolId": tool["id"],
            },
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"]["code"],
            "WORK_TOOL_REQUIREMENT_ALREADY_EXISTS",
        )

        missing_work = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "task",
                "workId": "missing-task",
                "toolId": tool["id"],
            },
        )
        self.assertEqual(missing_work.status_code, 404)
        self.assertEqual(
            missing_work.json()["detail"]["code"],
            "WORK_TOOL_REQUIREMENT_WORK_NOT_FOUND",
        )

        missing_tool = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "task",
                "workId": task["id"],
                "toolId": "missing-tool",
            },
        )
        self.assertEqual(missing_tool.status_code, 404)
        self.assertEqual(
            missing_tool.json()["detail"]["code"],
            "WORK_TOOL_REQUIREMENT_TOOL_NOT_FOUND",
        )

        other_space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Other Workshop"},
            )
        ).json()
        headers = {
            "X-Foreman-Space-Id": other_space["id"]
        }

        other_tool = await self.create_tool(
            "Other Router",
            headers=headers,
        )
        other_task = await self.create_task(
            "Other Work",
            headers=headers,
        )

        cross_space_work = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "task",
                "workId": other_task["id"],
                "toolId": tool["id"],
            },
        )
        self.assertEqual(
            cross_space_work.status_code,
            404,
        )

        cross_space_tool = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "task",
                "workId": task["id"],
                "toolId": other_tool["id"],
            },
        )
        self.assertEqual(
            cross_space_tool.status_code,
            404,
        )

    async def test_deleting_work_removes_owned_requirements(
        self,
    ) -> None:
        tool = await self.create_tool("Impact Driver")
        task = await self.create_task("Install fasteners")
        project = await self.create_project("Deck Repair")

        task_requirement = await self.create_requirement(
            "task",
            task["id"],
            tool["id"],
        )
        project_requirement = await self.create_requirement(
            "project",
            project["id"],
            tool["id"],
        )

        deleted_task = await self.client.delete(
            f"/api/tasks/{task['id']}"
        )
        self.assertEqual(deleted_task.status_code, 204)

        task_requirement_after = await self.client.get(
            (
                "/api/work-tool-requirements/"
                f"{task_requirement['id']}"
            )
        )
        self.assertEqual(
            task_requirement_after.status_code,
            404,
        )

        remaining = (
            await self.client.get(
                "/api/work-tool-requirements"
            )
        ).json()
        self.assertEqual(
            [item["id"] for item in remaining],
            [project_requirement["id"]],
        )

        deleted_project = await self.client.delete(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(
            deleted_project.status_code,
            204,
        )

        self.assertEqual(
            (
                await self.client.get(
                    "/api/work-tool-requirements"
                )
            ).json(),
            [],
        )

    async def test_requirements_are_isolated_by_active_space(
        self,
    ) -> None:
        other_space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Detached Shop"},
            )
        ).json()
        headers = {
            "X-Foreman-Space-Id": other_space["id"]
        }

        tool = await self.create_tool(
            "Shop Lathe",
            headers=headers,
        )
        project = await self.create_project(
            "Turn Parts",
            headers=headers,
        )
        requirement = await self.create_requirement(
            "project",
            project["id"],
            tool["id"],
            headers=headers,
        )

        self.assertEqual(
            (
                await self.client.get(
                    "/api/work-tool-requirements"
                )
            ).json(),
            [],
        )

        hidden = await self.client.get(
            (
                "/api/work-tool-requirements/"
                f"{requirement['id']}"
            )
        )
        self.assertEqual(hidden.status_code, 404)

        selected = await self.client.get(
            (
                "/api/work-tool-requirements/"
                f"{requirement['id']}"
            ),
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)

    async def test_validation_and_normalized_work_read_model(
        self,
    ) -> None:
        tool = await self.create_tool("Miter Saw")
        project = await self.create_project("Trim Project")

        requirement = await self.create_requirement(
            "project",
            project["id"],
            tool["id"],
            note="Required for trim cuts",
        )

        invalid_type = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "goal",
                "workId": project["id"],
                "toolId": tool["id"],
            },
        )
        self.assertEqual(invalid_type.status_code, 422)

        client_scoped = await self.client.post(
            "/api/work-tool-requirements",
            json={
                "workType": "project",
                "workId": project["id"],
                "toolId": tool["id"],
                "spaceId": "client-space",
            },
        )
        self.assertEqual(client_scoped.status_code, 422)

        empty_update = await self.client.patch(
            (
                "/api/work-tool-requirements/"
                f"{requirement['id']}"
            ),
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

        for field in ("toolId", "note"):
            with self.subTest(null_field=field):
                response = await self.client.patch(
                    (
                        "/api/work-tool-requirements/"
                        f"{requirement['id']}"
                    ),
                    json={field: None},
                )
                self.assertEqual(
                    response.status_code,
                    422,
                )

        work = (
            await self.client.get("/api/work")
        ).json()

        self.assertEqual(
            work["toolRequirements"],
            [requirement],
        )
        self.assertNotIn(
            "spaceId",
            work["toolRequirements"][0],
        )
