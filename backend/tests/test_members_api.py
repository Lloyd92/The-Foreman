from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.member import Member
from test_support import ApiTestCase


class MembersApiTests(ApiTestCase):
    async def create_person(self, display_name: str) -> dict:
        response = await self.client.post(
            "/api/people",
            json={"displayName": display_name},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def create_space(self, name: str) -> dict:
        response = await self.client.post(
            "/api/spaces",
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def test_default_space_member_crud(self) -> None:
        person = await self.create_person("Amber Lloyd")
        created = await self.client.post(
            "/api/members",
            json={
                "personId": person["id"],
                "role": "  Household   Administrator ",
                "responsibilities": "Household coordination",
            },
        )
        self.assertEqual(created.status_code, 201)
        member = created.json()
        self.assertEqual(member["role"], "household administrator")
        self.assertNotIn("spaceId", member)

        with SessionLocal() as session:
            persisted_member = session.get(Member, member["id"])
            self.assertIsNotNone(persisted_member)
            self.assertEqual(
                persisted_member.space_id,
                DEFAULT_SPACE_ID,
            )

        read = await self.client.get(f"/api/members/{member['id']}")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), member)

        updated = await self.client.patch(
            f"/api/members/{member['id']}",
            json={
                "role": "  Project   Lead ",
                "responsibilities": "Project coordination",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "project lead")
        self.assertNotIn("spaceId", updated.json())

        listed = await self.client.get("/api/members")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            [listed_member["id"] for listed_member in listed.json()],
            [member["id"]],
        )
        self.assertNotIn("spaceId", listed.json()[0])

        deleted = await self.client.delete(
            f"/api/members/{member['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        missing = await self.client.get(f"/api/members/{member['id']}")
        self.assertEqual(missing.status_code, 404)

    async def test_explicit_active_space_controls_membership(self) -> None:
        space = await self.create_space("Workshop")
        person = await self.create_person("Tyler Lloyd")
        headers = {"X-Foreman-Space-Id": space["id"]}

        created = await self.client.post(
            "/api/members",
            headers=headers,
            json={
                "personId": person["id"],
                "role": "member",
            },
        )
        self.assertEqual(created.status_code, 201)

        explicit_list = await self.client.get(
            "/api/members",
            headers=headers,
        )
        self.assertEqual(explicit_list.status_code, 200)
        self.assertEqual(
            [member["id"] for member in explicit_list.json()],
            [created.json()["id"]],
        )

        default_list = await self.client.get("/api/members")
        self.assertEqual(default_list.status_code, 200)
        self.assertEqual(default_list.json(), [])

    async def test_cross_space_member_access_is_not_found(self) -> None:
        space_a = await self.create_space("Workshop A")
        space_b = await self.create_space("Workshop B")
        person = await self.create_person("Shared Person")
        headers_a = {"X-Foreman-Space-Id": space_a["id"]}
        headers_b = {"X-Foreman-Space-Id": space_b["id"]}
        created = await self.client.post(
            "/api/members",
            headers=headers_a,
            json={
                "personId": person["id"],
                "role": "member",
            },
        )
        self.assertEqual(created.status_code, 201)
        member_id = created.json()["id"]

        requests = (
            self.client.get(
                f"/api/members/{member_id}",
                headers=headers_b,
            ),
            self.client.patch(
                f"/api/members/{member_id}",
                headers=headers_b,
                json={"role": "administrator"},
            ),
            self.client.delete(
                f"/api/members/{member_id}",
                headers=headers_b,
            ),
        )

        for request in requests:
            with self.subTest():
                response = await request
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json()["detail"]["code"],
                    "MEMBER_NOT_FOUND",
                )

        still_present = await self.client.get(
            f"/api/members/{member_id}",
            headers=headers_a,
        )
        self.assertEqual(still_present.status_code, 200)

    async def test_person_can_be_member_of_multiple_spaces(self) -> None:
        space = await self.create_space("Workshop")
        person = await self.create_person("Multi-space Person")
        payload = {
            "personId": person["id"],
            "role": "member",
        }

        default_member = await self.client.post(
            "/api/members",
            json=payload,
        )
        explicit_member = await self.client.post(
            "/api/members",
            headers={"X-Foreman-Space-Id": space["id"]},
            json=payload,
        )

        self.assertEqual(default_member.status_code, 201)
        self.assertEqual(explicit_member.status_code, 201)
        self.assertNotEqual(
            default_member.json()["id"],
            explicit_member.json()["id"],
        )

    async def test_duplicate_and_missing_dependencies_are_controlled(
        self,
    ) -> None:
        person = await self.create_person("Duplicate Member")
        payload = {
            "personId": person["id"],
            "role": "member",
        }
        first = await self.client.post("/api/members", json=payload)
        self.assertEqual(first.status_code, 201)

        duplicate = await self.client.post("/api/members", json=payload)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"]["code"],
            "MEMBER_ALREADY_EXISTS",
        )

        missing_person = await self.client.post(
            "/api/members",
            json={
                "personId": "missing-person",
                "role": "member",
            },
        )
        self.assertEqual(missing_person.status_code, 404)
        self.assertEqual(
            missing_person.json()["detail"]["code"],
            "PERSON_NOT_FOUND",
        )

        missing_space = await self.client.get(
            "/api/members",
            headers={"X-Foreman-Space-Id": "missing-space"},
        )
        self.assertEqual(missing_space.status_code, 404)
        self.assertEqual(
            missing_space.json()["detail"]["code"],
            "SPACE_NOT_FOUND",
        )

    async def test_member_payload_boundaries(self) -> None:
        person = await self.create_person("Payload Person")
        create_payloads = (
            {
                "personId": person["id"],
                "role": "member",
                "spaceId": DEFAULT_SPACE_ID,
            },
            {"role": "member"},
            {"personId": None, "role": "member"},
            {"personId": person["id"], "role": "member/owner"},
        )

        for payload in create_payloads:
            with self.subTest(payload=payload):
                response = await self.client.post(
                    "/api/members",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)

        created = await self.client.post(
            "/api/members",
            json={
                "personId": person["id"],
                "role": "member",
            },
        )
        self.assertEqual(created.status_code, 201)
        member_id = created.json()["id"]
        update_payloads = (
            {},
            {"role": None},
            {"responsibilities": None},
            {"personId": person["id"]},
            {"spaceId": DEFAULT_SPACE_ID},
        )

        for payload in update_payloads:
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    f"/api/members/{member_id}",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)
