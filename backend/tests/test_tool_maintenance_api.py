from test_support import ApiTestCase


def tool_payload(
    name: str = "Planer",
) -> dict:
    return {
        "name": name,
        "category": "Power Tools",
        "condition": "good",
        "location": "Workshop",
        "availability": "available",
        "notes": "",
    }


def maintenance_payload(
    *,
    maintenance_type: str = "inspection",
    performed_at: str = "2026-08-01T12:00:00Z",
) -> dict:
    return {
        "maintenanceType": maintenance_type,
        "performedAt": performed_at,
        "notes": "Completed factual maintenance.",
    }


class ToolMaintenanceApiTests(ApiTestCase):
    async def test_maintenance_crud_and_history_order(
        self,
    ) -> None:
        tool = (
            await self.client.post(
                "/api/tools",
                json=tool_payload(),
            )
        ).json()

        older = (
            await self.client.post(
                f"/api/tools/{tool['id']}/maintenance",
                json=maintenance_payload(
                    performed_at="2026-08-01T08:00:00-04:00",
                ),
            )
        )
        self.assertEqual(older.status_code, 201)

        newer = (
            await self.client.post(
                f"/api/tools/{tool['id']}/maintenance",
                json=maintenance_payload(
                    maintenance_type="service",
                    performed_at="2026-08-02T12:00:00Z",
                ),
            )
        )
        self.assertEqual(newer.status_code, 201)

        older_record = older.json()
        newer_record = newer.json()

        self.assertNotIn("spaceId", older_record)
        self.assertEqual(
            older_record["toolId"],
            tool["id"],
        )
        self.assertEqual(
            older_record["performedAt"],
            "2026-08-01T12:00:00Z",
        )
        self.assertTrue(
            older_record["createdAt"].endswith("Z")
        )

        history = await self.client.get(
            f"/api/tools/{tool['id']}/maintenance"
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            [
                item["id"]
                for item in history.json()
            ],
            [
                newer_record["id"],
                older_record["id"],
            ],
        )

        read = await self.client.get(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{older_record['id']}"
            )
        )
        self.assertEqual(read.status_code, 200)

        updated = await self.client.patch(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{older_record['id']}"
            ),
            json={
                "maintenanceType": "cleaning",
                "notes": "Corrected history note.",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["maintenanceType"],
            "cleaning",
        )

        deleted = await self.client.delete(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{older_record['id']}"
            )
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_maintenance_validation_and_missing_errors(
        self,
    ) -> None:
        tool = (
            await self.client.post(
                "/api/tools",
                json=tool_payload(),
            )
        ).json()

        naive_time = await self.client.post(
            f"/api/tools/{tool['id']}/maintenance",
            json=maintenance_payload(
                performed_at="2026-08-01T12:00:00",
            ),
        )
        self.assertEqual(naive_time.status_code, 422)

        blank_type = await self.client.post(
            f"/api/tools/{tool['id']}/maintenance",
            json=maintenance_payload(
                maintenance_type="   ",
            ),
        )
        self.assertEqual(blank_type.status_code, 422)

        record = (
            await self.client.post(
                f"/api/tools/{tool['id']}/maintenance",
                json=maintenance_payload(),
            )
        ).json()

        empty_update = await self.client.patch(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{record['id']}"
            ),
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

        for field in (
            "maintenanceType",
            "performedAt",
            "notes",
        ):
            with self.subTest(null_field=field):
                response = await self.client.patch(
                    (
                        f"/api/tools/{tool['id']}/maintenance/"
                        f"{record['id']}"
                    ),
                    json={field: None},
                )
                self.assertEqual(
                    response.status_code,
                    422,
                )

        missing_record = await self.client.get(
            f"/api/tools/{tool['id']}/maintenance/missing"
        )
        self.assertEqual(
            missing_record.status_code,
            404,
        )
        self.assertEqual(
            missing_record.json()["detail"]["code"],
            "TOOL_MAINTENANCE_NOT_FOUND",
        )

        missing_tool = await self.client.get(
            "/api/tools/missing/maintenance"
        )
        self.assertEqual(
            missing_tool.status_code,
            404,
        )
        self.assertEqual(
            missing_tool.json()["detail"]["code"],
            "TOOL_NOT_FOUND",
        )

        forbidden_scope = maintenance_payload()
        forbidden_scope["spaceId"] = "client-space"
        response = await self.client.post(
            f"/api/tools/{tool['id']}/maintenance",
            json=forbidden_scope,
        )
        self.assertEqual(response.status_code, 422)

    async def test_maintenance_is_isolated_by_active_space(
        self,
    ) -> None:
        space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Workshop"},
            )
        ).json()
        headers = {
            "X-Foreman-Space-Id": space["id"]
        }

        tool = (
            await self.client.post(
                "/api/tools",
                headers=headers,
                json=tool_payload("Workshop Planer"),
            )
        ).json()

        record = (
            await self.client.post(
                f"/api/tools/{tool['id']}/maintenance",
                headers=headers,
                json=maintenance_payload(),
            )
        ).json()

        default_history = await self.client.get(
            f"/api/tools/{tool['id']}/maintenance"
        )
        self.assertEqual(
            default_history.status_code,
            404,
        )

        default_record = await self.client.get(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{record['id']}"
            )
        )
        self.assertEqual(
            default_record.status_code,
            404,
        )

        selected = await self.client.get(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{record['id']}"
            ),
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)

    async def test_history_blocks_tool_deletion_until_removed(
        self,
    ) -> None:
        tool = (
            await self.client.post(
                "/api/tools",
                json=tool_payload(),
            )
        ).json()

        record = (
            await self.client.post(
                f"/api/tools/{tool['id']}/maintenance",
                json=maintenance_payload(),
            )
        ).json()

        blocked = await self.client.delete(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(
            blocked.json()["detail"]["code"],
            "TOOL_IN_USE",
        )

        removed = await self.client.delete(
            (
                f"/api/tools/{tool['id']}/maintenance/"
                f"{record['id']}"
            )
        )
        self.assertEqual(removed.status_code, 204)

        deleted = await self.client.delete(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
