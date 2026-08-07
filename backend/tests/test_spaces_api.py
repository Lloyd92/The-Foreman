from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.member import Member
from app.models.person import Person
from app.models.space import Space
from test_support import ApiTestCase


class SpacesApiTests(ApiTestCase):
    async def test_space_crud_and_default_fallback(self) -> None:
        listed = await self.client.get("/api/spaces")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            [space["id"] for space in listed.json()],
            [DEFAULT_SPACE_ID],
        )

        created = await self.client.post(
            "/api/spaces",
            json={
                "name": "Household",
                "description": "Shared household operations",
            },
        )
        self.assertEqual(created.status_code, 201)
        space = created.json()
        self.assertNotEqual(space["id"], DEFAULT_SPACE_ID)

        read = await self.client.get(f"/api/spaces/{space['id']}")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), space)

        updated = await self.client.patch(
            f"/api/spaces/{space['id']}",
            json={
                "name": "Home",
                "description": "Updated household operations",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Home")
        self.assertEqual(
            updated.json()["description"],
            "Updated household operations",
        )

        selected = await self.client.get(
            "/api/spaces/active",
            headers={"X-Foreman-Space-Id": space["id"]},
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["id"], space["id"])

        deleted = await self.client.delete(
            f"/api/spaces/{space['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

        missing_selection = await self.client.get(
            "/api/spaces/active",
            headers={"X-Foreman-Space-Id": space["id"]},
        )
        self.assertEqual(missing_selection.status_code, 404)

        fallback = await self.client.get("/api/spaces/active")
        self.assertEqual(fallback.json()["id"], DEFAULT_SPACE_ID)

    async def test_duplicate_name_is_conflict(self) -> None:
        first = await self.client.post(
            "/api/spaces",
            json={"name": "Household"},
        )
        self.assertEqual(first.status_code, 201)

        duplicate = await self.client.post(
            "/api/spaces",
            json={"name": " household "},
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"]["code"],
            "SPACE_NAME_CONFLICT",
        )

    async def test_default_space_can_be_updated_but_not_deleted(
        self,
    ) -> None:
        updated = await self.client.patch(
            f"/api/spaces/{DEFAULT_SPACE_ID}",
            json={
                "name": "Primary",
                "description": "Primary operational context",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Primary")

        active = await self.client.get("/api/spaces/active")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.json()["id"], DEFAULT_SPACE_ID)
        self.assertEqual(active.json()["name"], "Primary")

        deleted = await self.client.delete(
            f"/api/spaces/{DEFAULT_SPACE_ID}"
        )
        self.assertEqual(deleted.status_code, 409)
        self.assertEqual(
            deleted.json()["detail"]["code"],
            "DEFAULT_SPACE_PROTECTED",
        )

    async def test_referenced_space_cannot_be_deleted(self) -> None:
        with SessionLocal() as session:
            space = Space(name="Workshop")
            person = Person(display_name="Tyler")
            session.add_all([space, person])
            session.flush()
            session.add(
                Member(
                    space_id=space.id,
                    person_id=person.id,
                    role="member",
                )
            )
            session.commit()
            space_id = space.id

        response = await self.client.delete(f"/api/spaces/{space_id}")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "SPACE_IN_USE",
        )

        with SessionLocal() as session:
            self.assertIsNotNone(
                session.scalar(
                    select(Space).where(Space.id == space_id)
                )
            )

    async def test_missing_space_and_invalid_updates_are_controlled(
        self,
    ) -> None:
        self.assertEqual(
            (await self.client.get("/api/spaces/missing")).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    "/api/spaces/missing",
                    json={"description": "No record"},
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.delete("/api/spaces/missing")).status_code,
            404,
        )

        for payload in ({}, {"name": None}, {"description": None}):
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    f"/api/spaces/{DEFAULT_SPACE_ID}",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)
