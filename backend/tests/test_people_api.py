from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.member import Member
from app.models.person import Person
from test_support import ApiTestCase


class PeopleApiTests(ApiTestCase):
    async def test_person_crud_and_duplicate_names(self) -> None:
        first = await self.client.post(
            "/api/people",
            json={
                "displayName": "Amber",
                "givenName": "Amber",
                "familyName": "Lloyd",
                "description": "Household contact",
            },
        )
        self.assertEqual(first.status_code, 201)
        person = first.json()

        read = await self.client.get(f"/api/people/{person['id']}")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), person)

        updated = await self.client.patch(
            f"/api/people/{person['id']}",
            json={
                "displayName": "Amber Lloyd",
                "description": "Updated household contact",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["displayName"], "Amber Lloyd")

        duplicate_name = await self.client.post(
            "/api/people",
            json={"displayName": "Amber Lloyd"},
        )
        self.assertEqual(duplicate_name.status_code, 201)

        listed = await self.client.get("/api/people")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 2)

        deleted = await self.client.delete(
            f"/api/people/{duplicate_name.json()['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_referenced_person_cannot_be_deleted(self) -> None:
        with SessionLocal() as session:
            person = Person(display_name="Tyler")
            session.add(person)
            session.flush()
            session.add(
                Member(
                    space_id=DEFAULT_SPACE_ID,
                    person_id=person.id,
                    role="member",
                )
            )
            session.commit()
            person_id = person.id

        response = await self.client.delete(
            f"/api/people/{person_id}"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "PERSON_IN_USE",
        )

    async def test_missing_person_and_invalid_updates_are_controlled(
        self,
    ) -> None:
        self.assertEqual(
            (await self.client.get("/api/people/missing")).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    "/api/people/missing",
                    json={"description": "Missing"},
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.delete("/api/people/missing")).status_code,
            404,
        )

        created = await self.client.post(
            "/api/people",
            json={"displayName": "Test Person"},
        )
        person_id = created.json()["id"]

        for payload in (
            {},
            {"displayName": None},
            {"givenName": None},
            {"familyName": None},
            {"description": None},
        ):
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    f"/api/people/{person_id}",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)
