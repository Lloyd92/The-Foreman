from test_support import ApiTestCase


class WorkCalendarRelationshipApiTests(ApiTestCase):
    async def setup_calendar(self) -> None:
        response = await self.client.put(
            "/api/calendar/settings",
            json={"timezoneName": "America/New_York"},
        )
        self.assertEqual(response.status_code, 200)

    async def create_task(self) -> dict:
        response = await self.client.post(
            "/api/tasks",
            json={"title": "Calendar-linked task"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def create_entry(self) -> dict:
        await self.setup_calendar()
        response = await self.client.post(
            "/api/calendar/entries",
            json={
                "kind": "commitment",
                "title": "Scheduled work",
                "startAt": "2026-08-13T08:00:00",
                "endAt": "2026-08-13T09:00:00",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def create_relationship(
        self,
        task_id: str,
        entry_id: str,
    ) -> dict:
        response = await self.client.post(
            "/api/work-calendar-relationships",
            json={
                "workType": "task",
                "workId": task_id,
                "calendarType": "entry",
                "calendarId": entry_id,
                "note": "User placed Work on Calendar",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_calendar_deletion_preserves_evidence(self) -> None:
        task = await self.create_task()
        entry = await self.create_entry()
        relationship = await self.create_relationship(
            task["id"],
            entry["id"],
        )

        self.assertTrue(relationship["calendarExists"])

        deleted = await self.client.delete(
            f"/api/calendar/entries/{entry['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

        read = await self.client.get(
            f"/api/work-calendar-relationships/{relationship['id']}"
        )
        self.assertEqual(read.status_code, 200)
        self.assertFalse(read.json()["calendarExists"])
        self.assertEqual(read.json()["calendarId"], entry["id"])

    async def test_work_deletion_removes_relationship(self) -> None:
        task = await self.create_task()
        entry = await self.create_entry()
        relationship = await self.create_relationship(
            task["id"],
            entry["id"],
        )

        deleted = await self.client.delete(
            f"/api/tasks/{task['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

        read = await self.client.get(
            f"/api/work-calendar-relationships/{relationship['id']}"
        )
        self.assertEqual(read.status_code, 404)
