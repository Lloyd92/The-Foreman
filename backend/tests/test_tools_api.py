from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.tool import Tool
from app.models.tool_maintenance_record import ToolMaintenanceRecord
from test_support import ApiTestCase


def tool_payload(
    *,
    name: str = "Table Saw",
    category: str = "Power Tools",
    condition: str = "good",
    location: str = "Workshop",
    availability: str = "available",
) -> dict:
    return {
        "name": name,
        "category": category,
        "condition": condition,
        "location": location,
        "availability": availability,
        "notes": "Durable shop equipment",
    }


class ToolApiTests(ApiTestCase):
    async def test_tool_crud_is_backend_and_space_authoritative(
        self,
    ) -> None:
        created = await self.client.post(
            "/api/tools",
            json=tool_payload(),
        )
        self.assertEqual(created.status_code, 201)

        tool = created.json()
        self.assertNotIn("spaceId", tool)
        self.assertEqual(tool["name"], "Table Saw")

        with SessionLocal() as session:
            self.assertEqual(
                session.scalar(
                    select(Tool.space_id).where(
                        Tool.id == tool["id"]
                    )
                ),
                DEFAULT_SPACE_ID,
            )

        read = await self.client.get(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(read.status_code, 200)

        updated = await self.client.patch(
            f"/api/tools/{tool['id']}",
            json={
                "condition": "needs service",
                "availability": "unavailable",
                "notes": "Blade alignment inspection required",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["condition"],
            "needs service",
        )
        self.assertEqual(
            updated.json()["availability"],
            "unavailable",
        )

        listed = await self.client.get("/api/tools")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            [item["id"] for item in listed.json()],
            [tool["id"]],
        )

        deleted = await self.client.delete(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            (await self.client.get("/api/tools")).json(),
            [],
        )

    async def test_tool_search_filter_and_sort(self) -> None:
        payloads = [
            tool_payload(
                name="Circular Saw",
                category="Power Tools",
                condition="good",
                location="Shelf B",
                availability="available",
            ),
            tool_payload(
                name="Claw Hammer",
                category="Hand Tools",
                condition="worn",
                location="Toolbox",
                availability="available",
            ),
            tool_payload(
                name="Drill Press",
                category="Power Tools",
                condition="service due",
                location="Bench",
                availability="unavailable",
            ),
        ]

        for payload in payloads:
            response = await self.client.post(
                "/api/tools",
                json=payload,
            )
            self.assertEqual(response.status_code, 201)

        search = await self.client.get(
            "/api/tools",
            params={"search": "drill"},
        )
        self.assertEqual(
            [item["name"] for item in search.json()],
            ["Drill Press"],
        )

        filtered = await self.client.get(
            "/api/tools",
            params={
                "category": "Power Tools",
                "availability": "available",
            },
        )
        self.assertEqual(
            [item["name"] for item in filtered.json()],
            ["Circular Saw"],
        )

        sorted_response = await self.client.get(
            "/api/tools",
            params={
                "sortBy": "location",
                "sortDirection": "desc",
            },
        )
        self.assertEqual(
            [item["location"] for item in sorted_response.json()],
            ["Toolbox", "Shelf B", "Bench"],
        )

    async def test_tool_validation_and_missing_record_errors(
        self,
    ) -> None:
        for changes in (
            {"name": "   "},
            {"category": "   "},
            {"condition": "   "},
            {"location": "   "},
            {"availability": "   "},
        ):
            payload = tool_payload()
            payload.update(changes)
            response = await self.client.post(
                "/api/tools",
                json=payload,
            )
            self.assertEqual(response.status_code, 422)

        invalid_query = await self.client.get(
            "/api/tools?sortBy=unknown"
        )
        self.assertEqual(invalid_query.status_code, 422)

        missing = await self.client.get(
            "/api/tools/missing"
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "TOOL_NOT_FOUND",
        )

        empty_update = await self.client.patch(
            "/api/tools/missing",
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

        created = (
            await self.client.post(
                "/api/tools",
                json=tool_payload(name="Null Boundary Tool"),
            )
        ).json()

        for field in (
            "name",
            "category",
            "condition",
            "location",
            "availability",
            "notes",
        ):
            with self.subTest(null_field=field):
                null_update = await self.client.patch(
                    f"/api/tools/{created['id']}",
                    json={field: None},
                )
                self.assertEqual(
                    null_update.status_code,
                    422,
                )

        payload = tool_payload()
        payload["spaceId"] = "client-space"
        forbidden_space = await self.client.post(
            "/api/tools",
            json=payload,
        )
        self.assertEqual(forbidden_space.status_code, 422)

    async def test_tools_are_isolated_by_active_space(self) -> None:
        created_space = await self.client.post(
            "/api/spaces",
            json={"name": "Workshop"},
        )
        self.assertEqual(created_space.status_code, 201)
        space_id = created_space.json()["id"]
        headers = {"X-Foreman-Space-Id": space_id}

        workshop_tool = (
            await self.client.post(
                "/api/tools",
                headers=headers,
                json=tool_payload(name="Workshop Lathe"),
            )
        ).json()

        self.assertEqual(
            (await self.client.get("/api/tools")).json(),
            [],
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/tools/{workshop_tool['id']}"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    f"/api/tools/{workshop_tool['id']}",
                    json={"condition": "leaked update"},
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/tools/{workshop_tool['id']}"
                )
            ).status_code,
            404,
        )

        selected = await self.client.get(
            f"/api/tools/{workshop_tool['id']}",
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(
            selected.json()["name"],
            "Workshop Lathe",
        )

    async def test_maintenance_history_blocks_tool_deletion(
        self,
    ) -> None:
        tool = (
            await self.client.post(
                "/api/tools",
                json=tool_payload(name="Planer"),
            )
        ).json()

        with SessionLocal() as session:
            record = ToolMaintenanceRecord(
                space_id=DEFAULT_SPACE_ID,
                tool_id=tool["id"],
                maintenance_type="inspection",
                performed_at=datetime.now(timezone.utc),
                notes="Baseline inspection",
            )
            session.add(record)
            session.commit()
            record_id = record.id

        blocked = await self.client.delete(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(
            blocked.json()["detail"]["code"],
            "TOOL_IN_USE",
        )

        self.assertEqual(
            (
                await self.client.get(
                    f"/api/tools/{tool['id']}"
                )
            ).status_code,
            200,
        )

        with SessionLocal() as session:
            record = session.get(
                ToolMaintenanceRecord,
                record_id,
            )
            session.delete(record)
            session.commit()

        deleted = await self.client.delete(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
