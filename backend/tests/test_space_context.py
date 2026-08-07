from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.space import Space
from test_support import ApiTestCase


class SpaceContextTests(ApiTestCase):
    async def test_missing_header_uses_default_space(self) -> None:
        response = await self.client.get("/api/spaces/active")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], DEFAULT_SPACE_ID)

    async def test_valid_header_selects_existing_space(self) -> None:
        with SessionLocal() as session:
            space = Space(
                name="Household",
                description="Household operations",
            )
            session.add(space)
            session.commit()
            session.refresh(space)
            space_id = space.id

        response = await self.client.get(
            "/api/spaces/active",
            headers={"X-Foreman-Space-Id": space_id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], space_id)
        self.assertEqual(response.json()["name"], "Household")

    async def test_unknown_header_returns_controlled_not_found(self) -> None:
        response = await self.client.get(
            "/api/spaces/active",
            headers={"X-Foreman-Space-Id": "missing-space"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "SPACE_NOT_FOUND",
                    "message": "The requested Space does not exist.",
                }
            },
        )
