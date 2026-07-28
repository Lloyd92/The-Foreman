from test_support import ApiTestCase


class ProjectApiTests(ApiTestCase):
    async def test_project_crud_and_archive(self) -> None:
        create_response = await self.client.post(
            "/api/projects",
            json={
                "name": "Workbench Build",
                "status": "active",
                "progress": 20,
                "notes": "Shop project",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        project = create_response.json()

        list_response = await self.client.get("/api/projects")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        read_response = await self.client.get(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["name"], "Workbench Build")

        update_response = await self.client.patch(
            f"/api/projects/{project['id']}",
            json={
                "name": "Assembly Workbench",
                "progress": 45,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["name"],
            "Assembly Workbench",
        )
        self.assertEqual(update_response.json()["progress"], 45)

        archive_response = await self.client.post(
            f"/api/projects/{project['id']}/archive"
        )
        self.assertEqual(archive_response.status_code, 200)
        self.assertEqual(archive_response.json()["status"], "archived")
        self.assertIsNotNone(archive_response.json()["archivedAt"])

        active_list = await self.client.get("/api/projects")
        self.assertEqual(active_list.json(), [])

        full_list = await self.client.get(
            "/api/projects",
            params={"includeArchived": "true"},
        )
        self.assertEqual(len(full_list.json()), 1)

    async def test_project_validation_errors_are_clear(self) -> None:
        empty_name = await self.client.post(
            "/api/projects",
            json={"name": ""},
        )
        invalid_progress = await self.client.post(
            "/api/projects",
            json={"name": "Invalid", "progress": 101},
        )
        whitespace_name = await self.client.post(
            "/api/projects",
            json={"name": "   "},
        )
        direct_archive = await self.client.post(
            "/api/projects",
            json={"name": "Invalid", "status": "archived"},
        )
        empty_update = await self.client.patch(
            "/api/projects/not-found",
            json={},
        )

        self.assertEqual(empty_name.status_code, 422)
        self.assertEqual(invalid_progress.status_code, 422)
        self.assertEqual(whitespace_name.status_code, 422)
        self.assertEqual(direct_archive.status_code, 422)
        self.assertEqual(empty_update.status_code, 422)
        self.assertTrue(empty_name.json()["detail"])

    async def test_missing_project_returns_not_found(self) -> None:
        response = await self.client.get("/api/projects/not-found")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Project not found.")
