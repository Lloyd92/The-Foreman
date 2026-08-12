from test_support import ApiTestCase


class CalendarApiTests(ApiTestCase):
    async def configure_timezone(
        self,
        timezone_name: str = "America/New_York",
        *,
        headers: dict | None = None,
    ) -> dict:
        response = await self.client.put(
            "/api/calendar/settings",
            headers=headers,
            json={"timezoneName": timezone_name},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def test_calendar_settings_are_space_authoritative(self) -> None:
        missing = await self.client.get("/api/calendar/settings")
        self.assertEqual(missing.status_code, 404)

        settings = await self.configure_timezone()
        self.assertEqual(
            settings["timezoneName"],
            "America/New_York",
        )
        self.assertNotIn("spaceId", settings)

        read = await self.client.get("/api/calendar/settings")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(
            read.json()["timezoneName"],
            "America/New_York",
        )

        invalid = await self.client.put(
            "/api/calendar/settings",
            json={"timezoneName": "Not/A-Timezone"},
        )
        self.assertEqual(invalid.status_code, 422)

    async def test_timed_entry_uses_configured_timezone_and_crud(self) -> None:
        await self.configure_timezone()

        created = await self.client.post(
            "/api/calendar/entries",
            json={
                "kind": "commitment",
                "title": "Morning appointment",
                "allDay": False,
                "startAt": "2026-08-13T08:00:00",
                "endAt": "2026-08-13T09:30:00",
                "location": "Aberdeen",
            },
        )
        self.assertEqual(created.status_code, 201)

        entry = created.json()
        self.assertEqual(entry["timezoneName"], "America/New_York")
        self.assertEqual(entry["startAt"], "2026-08-13T12:00:00Z")
        self.assertEqual(entry["endAt"], "2026-08-13T13:30:00Z")

        updated = await self.client.patch(
            f"/api/calendar/entries/{entry['id']}",
            json={"title": "Updated appointment"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["title"],
            "Updated appointment",
        )

        read = await self.client.get(
            f"/api/calendar/entries/{entry['id']}"
        )
        self.assertEqual(read.status_code, 200)

        listed = await self.client.get("/api/calendar/entries")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        deleted = await self.client.delete(
            f"/api/calendar/entries/{entry['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_all_day_entry_uses_exclusive_end_date(self) -> None:
        await self.configure_timezone()

        response = await self.client.post(
            "/api/calendar/entries",
            json={
                "kind": "event",
                "title": "Family event",
                "allDay": True,
                "startDate": "2026-08-15",
                "endDate": "2026-08-16",
            },
        )
        self.assertEqual(response.status_code, 201)

        entry = response.json()
        self.assertEqual(entry["startDate"], "2026-08-15")
        self.assertEqual(entry["endDate"], "2026-08-16")
        self.assertIsNone(entry["startAt"])
        self.assertIsNone(entry["endAt"])

    async def test_cross_space_member_is_rejected(self) -> None:
        space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Other Space"},
            )
        ).json()

        person = (
            await self.client.post(
                "/api/people",
                json={"displayName": "Calendar Member"},
            )
        ).json()

        member = (
            await self.client.post(
                "/api/members",
                json={
                    "personId": person["id"],
                    "role": "member",
                },
            )
        ).json()

        headers = {"X-Foreman-Space-Id": space["id"]}
        await self.configure_timezone(headers=headers)

        response = await self.client.post(
            "/api/calendar/entries",
            headers=headers,
            json={
                "memberId": member["id"],
                "kind": "commitment",
                "title": "Wrong-space member",
                "startAt": "2026-08-13T08:00:00",
                "endAt": "2026-08-13T09:00:00",
            },
        )

        self.assertEqual(response.status_code, 404)

    async def test_weekly_series_crud(self) -> None:
        await self.configure_timezone()

        created = await self.client.post(
            "/api/calendar/series",
            json={
                "kind": "commitment",
                "title": "Work shift",
                "frequency": "weekly",
                "intervalValue": 1,
                "weekdays": ["monday", "tuesday", "wednesday"],
                "anchorDate": "2026-08-10",
                "localStartTime": "06:00",
                "durationMinutes": 510,
            },
        )
        self.assertEqual(created.status_code, 201)

        series = created.json()
        self.assertEqual(series["frequency"], "weekly")
        self.assertEqual(
            series["weekdays"],
            ["monday", "tuesday", "wednesday"],
        )
        self.assertEqual(series["timezoneName"], "America/New_York")

        read = await self.client.get(
            f"/api/calendar/series/{series['id']}"
        )
        self.assertEqual(read.status_code, 200)

        listed = await self.client.get("/api/calendar/series")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        deleted = await self.client.delete(
            f"/api/calendar/series/{series['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_series_exclusion_create_and_delete(self) -> None:
        await self.configure_timezone()

        created = await self.client.post(
            "/api/calendar/series",
            json={
                "kind": "commitment",
                "title": "Work shift",
                "frequency": "weekly",
                "weekdays": ["wednesday"],
                "anchorDate": "2026-08-12",
                "localStartTime": "06:00",
                "durationMinutes": 510,
            },
        )
        self.assertEqual(created.status_code, 201)
        series_id = created.json()["id"]

        excluded = await self.client.post(
            f"/api/calendar/series/{series_id}/exclusions",
            json={"excludedDate": "2026-08-19"},
        )
        self.assertEqual(excluded.status_code, 201)
        self.assertEqual(
            excluded.json()["excludedDate"],
            "2026-08-19",
        )

        deleted = await self.client.delete(
            f"/api/calendar/series/{series_id}/exclusions/2026-08-19"
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_series_update(self) -> None:
        await self.configure_timezone()

        created = await self.client.post(
            "/api/calendar/series",
            json={
                "kind": "commitment",
                "title": "Old shift",
                "frequency": "weekly",
                "weekdays": ["monday"],
                "anchorDate": "2026-08-10",
                "localStartTime": "06:00",
                "durationMinutes": 480,
            },
        )
        self.assertEqual(created.status_code, 201)
        series_id = created.json()["id"]

        updated = await self.client.patch(
            f"/api/calendar/series/{series_id}",
            json={
                "title": "Updated shift",
                "weekdays": ["monday", "wednesday"],
                "durationMinutes": 510,
            },
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "Updated shift")
        self.assertEqual(
            updated.json()["weekdays"],
            ["monday", "wednesday"],
        )
        self.assertEqual(updated.json()["durationMinutes"], 510)

    async def test_occurrences_expand_series_and_apply_exclusion(self) -> None:
        await self.configure_timezone()

        series = (
            await self.client.post(
                "/api/calendar/series",
                json={
                    "kind": "commitment",
                    "title": "Morning shift",
                    "frequency": "weekly",
                    "weekdays": ["monday"],
                    "anchorDate": "2026-08-10",
                    "localStartTime": "06:00",
                    "durationMinutes": 60,
                },
            )
        ).json()

        await self.client.post(
            f"/api/calendar/series/{series['id']}/exclusions",
            json={"excludedDate": "2026-08-17"},
        )

        response = await self.client.get(
            "/api/calendar/occurrences",
            params={
                "start_date": "2026-08-10",
                "end_date": "2026-08-25",
            },
        )

        self.assertEqual(response.status_code, 200)

        occurrences = [
            item
            for item in response.json()
            if item["sourceType"] == "series"
        ]

        self.assertEqual(len(occurrences), 2)
        self.assertEqual(
            [item["startAt"] for item in occurrences],
            [
                "2026-08-10T10:00:00Z",
                "2026-08-24T10:00:00Z",
            ],
        )

    async def test_series_preserves_timezone_snapshot(self) -> None:
        await self.configure_timezone("America/New_York")

        series = (
            await self.client.post(
                "/api/calendar/series",
                json={
                    "kind": "commitment",
                    "title": "Morning routine",
                    "frequency": "daily",
                    "anchorDate": "2026-08-10",
                    "localStartTime": "06:00",
                    "durationMinutes": 60,
                },
            )
        ).json()

        await self.configure_timezone("America/Chicago")

        response = await self.client.get(
            "/api/calendar/occurrences",
            params={
                "start_date": "2026-08-10",
                "end_date": "2026-08-11",
            },
        )

        self.assertEqual(response.status_code, 200)
        occurrence = response.json()[0]

        self.assertEqual(
            occurrence["sourceId"],
            series["id"],
        )
        self.assertEqual(
            occurrence["timezoneName"],
            "America/New_York",
        )
        self.assertEqual(
            occurrence["startAt"],
            "2026-08-10T10:00:00Z",
        )
