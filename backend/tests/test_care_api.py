from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.care_plan import CarePlan
from test_support import ApiTestCase


def tool_payload(
    name: str = "Table Saw",
) -> dict:
    return {
        "name": name,
        "category": "Power Tools",
        "condition": "good",
        "location": "Workshop",
        "availability": "available",
        "notes": "",
    }


def care_payload(
    *,
    name: str = "Inspect Table Saw",
    care_type: str = "inspection",
    tool_id: str | None = None,
) -> dict:
    return {
        "name": name,
        "careType": care_type,
        "toolId": tool_id,
        "description": "Inspect and document condition.",
        "frequencyValue": 30,
        "frequencyUnit": "days",
        "notes": "Factual upkeep definition",
    }


class CarePlanApiTests(ApiTestCase):
    async def test_care_plan_crud_is_space_authoritative(
        self,
    ) -> None:
        created = await self.client.post(
            "/api/care-plans",
            json=care_payload(),
        )
        self.assertEqual(created.status_code, 201)

        care_plan = created.json()
        self.assertNotIn("spaceId", care_plan)
        self.assertIsNone(care_plan["toolId"])
        self.assertEqual(
            care_plan["frequencyValue"],
            30,
        )
        self.assertTrue(
            care_plan["createdAt"].endswith("Z")
        )
        self.assertTrue(
            care_plan["updatedAt"].endswith("Z")
        )

        with SessionLocal() as session:
            self.assertEqual(
                session.scalar(
                    select(CarePlan.space_id).where(
                        CarePlan.id == care_plan["id"]
                    )
                ),
                DEFAULT_SPACE_ID,
            )

        read = await self.client.get(
            f"/api/care-plans/{care_plan['id']}"
        )
        self.assertEqual(read.status_code, 200)

        updated = await self.client.patch(
            f"/api/care-plans/{care_plan['id']}",
            json={
                "description": "Updated factual definition.",
                "frequencyValue": None,
                "frequencyUnit": None,
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertIsNone(
            updated.json()["frequencyValue"]
        )
        self.assertIsNone(
            updated.json()["frequencyUnit"]
        )

        listed = await self.client.get(
            "/api/care-plans"
        )
        self.assertEqual(
            [item["id"] for item in listed.json()],
            [care_plan["id"]],
        )

        deleted = await self.client.delete(
            f"/api/care-plans/{care_plan['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            (await self.client.get("/api/care-plans")).json(),
            [],
        )

    async def test_tool_reference_is_optional_and_detaches(
        self,
    ) -> None:
        tool = (
            await self.client.post(
                "/api/tools",
                json=tool_payload(),
            )
        ).json()

        care_plan = (
            await self.client.post(
                "/api/care-plans",
                json=care_payload(tool_id=tool["id"]),
            )
        ).json()

        self.assertEqual(
            care_plan["toolId"],
            tool["id"],
        )

        deleted_tool = await self.client.delete(
            f"/api/tools/{tool['id']}"
        )
        self.assertEqual(deleted_tool.status_code, 204)

        detached = (
            await self.client.get(
                f"/api/care-plans/{care_plan['id']}"
            )
        ).json()

        self.assertIsNone(detached["toolId"])

    async def test_search_filter_and_sort(self) -> None:
        await self.client.post(
            "/api/care-plans",
            json=care_payload(
                name="Saw Inspection",
                care_type="inspection",
            ),
        )
        await self.client.post(
            "/api/care-plans",
            json=care_payload(
                name="Air Filter Cleaning",
                care_type="cleaning",
            ),
        )

        search = await self.client.get(
            "/api/care-plans",
            params={"search": "filter"},
        )
        self.assertEqual(
            [item["name"] for item in search.json()],
            ["Air Filter Cleaning"],
        )

        filtered = await self.client.get(
            "/api/care-plans",
            params={"careType": "inspection"},
        )
        self.assertEqual(
            [item["name"] for item in filtered.json()],
            ["Saw Inspection"],
        )

        sorted_response = await self.client.get(
            "/api/care-plans",
            params={
                "sortBy": "careType",
                "sortDirection": "desc",
            },
        )
        self.assertEqual(
            [
                item["careType"]
                for item in sorted_response.json()
            ],
            ["inspection", "cleaning"],
        )

    async def test_validation_and_missing_tool_errors(
        self,
    ) -> None:
        missing_tool = await self.client.post(
            "/api/care-plans",
            json=care_payload(tool_id="missing-tool"),
        )
        self.assertEqual(
            missing_tool.status_code,
            409,
        )
        self.assertEqual(
            missing_tool.json()["detail"]["code"],
            "CARE_PLAN_TOOL_NOT_FOUND",
        )

        for payload in (
            {
                **care_payload(),
                "frequencyUnit": None,
            },
            {
                **care_payload(),
                "frequencyValue": None,
            },
            {
                **care_payload(),
                "frequencyValue": 0,
            },
        ):
            response = await self.client.post(
                "/api/care-plans",
                json=payload,
            )
            self.assertEqual(response.status_code, 422)

        care_plan = (
            await self.client.post(
                "/api/care-plans",
                json=care_payload(),
            )
        ).json()

        empty_update = await self.client.patch(
            f"/api/care-plans/{care_plan['id']}",
            json={},
        )
        self.assertEqual(
            empty_update.status_code,
            422,
        )

        partial_frequency = await self.client.patch(
            f"/api/care-plans/{care_plan['id']}",
            json={"frequencyValue": 60},
        )
        self.assertEqual(
            partial_frequency.status_code,
            422,
        )

        for field in (
            "name",
            "careType",
            "description",
            "notes",
        ):
            with self.subTest(null_field=field):
                response = await self.client.patch(
                    f"/api/care-plans/{care_plan['id']}",
                    json={field: None},
                )
                self.assertEqual(
                    response.status_code,
                    422,
                )

        client_scoped = care_payload()
        client_scoped["spaceId"] = "client-space"
        forbidden_space = await self.client.post(
            "/api/care-plans",
            json=client_scoped,
        )
        self.assertEqual(
            forbidden_space.status_code,
            422,
        )

    async def test_care_plans_are_isolated_by_active_space(
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
                json=tool_payload("Workshop Drill"),
            )
        ).json()

        care_plan = (
            await self.client.post(
                "/api/care-plans",
                headers=headers,
                json=care_payload(
                    name="Workshop Drill Inspection",
                    tool_id=tool["id"],
                ),
            )
        ).json()

        self.assertEqual(
            (await self.client.get("/api/care-plans")).json(),
            [],
        )

        cross_space_read = await self.client.get(
            f"/api/care-plans/{care_plan['id']}"
        )
        self.assertEqual(
            cross_space_read.status_code,
            404,
        )

        cross_space_tool = await self.client.post(
            "/api/care-plans",
            json=care_payload(tool_id=tool["id"]),
        )
        self.assertEqual(
            cross_space_tool.status_code,
            409,
        )

        selected = await self.client.get(
            f"/api/care-plans/{care_plan['id']}",
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)
