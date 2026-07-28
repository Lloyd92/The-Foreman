from datetime import datetime, timezone

from test_support import ApiTestCase


def browser_task(
    task_id: str,
    *,
    title: str = "Migrated task",
) -> dict:
    return {
        "id": task_id,
        "title": title,
        "priority": "high",
        "completed": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


class TaskMigrationTests(ApiTestCase):
    async def test_migration_succeeds_and_retains_browser_data(self) -> None:
        record = browser_task(
            "00000000-0000-4000-8000-000000000001"
        )
        response = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [record]},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["migrated"], 1)
        self.assertTrue(result["browserDataRetained"])
        self.assertEqual(
            result["confirmedSourceIds"],
            [record["id"]],
        )

        task_response = await self.client.get(
            f"/api/tasks/{record['id']}"
        )
        self.assertEqual(task_response.status_code, 200)
        self.assertEqual(task_response.json()["title"], record["title"])

    async def test_migration_retry_is_idempotent(self) -> None:
        record = browser_task(
            "00000000-0000-4000-8000-000000000002"
        )

        first_response = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [record]},
        )
        retry_response = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [record]},
        )

        self.assertEqual(first_response.json()["migrated"], 1)
        self.assertEqual(retry_response.json()["migrated"], 0)
        self.assertEqual(
            retry_response.json()["alreadyMigrated"],
            1,
        )

        tasks_response = await self.client.get("/api/tasks")
        self.assertEqual(len(tasks_response.json()), 1)

    async def test_deleted_migrated_task_is_not_reimported(self) -> None:
        record = browser_task(
            "00000000-0000-4000-8000-000000000006"
        )
        await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [record]},
        )
        await self.client.delete(f"/api/tasks/{record['id']}")

        retry_response = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [record]},
        )

        self.assertEqual(
            retry_response.json()["alreadyMigrated"],
            1,
        )
        tasks_response = await self.client.get("/api/tasks")
        self.assertEqual(tasks_response.json(), [])

    async def test_duplicate_backend_id_is_not_overwritten(self) -> None:
        record = browser_task(
            "00000000-0000-4000-8000-000000000003"
        )
        create_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Backend task",
                "priority": "low",
            },
        )
        backend_task = create_response.json()
        record["id"] = backend_task["id"]

        migration_response = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [record]},
        )

        result = migration_response.json()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["skipped"], 1)
        self.assertIn(
            "not overwritten",
            result["errors"][0]["reason"],
        )

        task_response = await self.client.get(
            f"/api/tasks/{backend_task['id']}"
        )
        self.assertEqual(
            task_response.json()["title"],
            "Backend task",
        )

    async def test_malformed_record_is_reported_not_discarded(self) -> None:
        valid_record = browser_task(
            "00000000-0000-4000-8000-000000000004"
        )
        malformed_record = browser_task(
            "00000000-0000-4000-8000-000000000005",
            title="",
        )

        response = await self.client.post(
            "/api/task-migrations/browser",
            json={"records": [valid_record, malformed_record]},
        )

        result = response.json()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["migrated"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(
            result["errors"][0]["sourceRecordId"],
            malformed_record["id"],
        )
        self.assertTrue(result["errors"][0]["reason"])

        tasks_response = await self.client.get("/api/tasks")
        self.assertEqual(len(tasks_response.json()), 1)
