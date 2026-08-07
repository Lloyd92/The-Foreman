from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.organization_space_relationship import (
    OrganizationSpaceRelationship,
)
from test_support import ApiTestCase


class OrganizationRelationshipsApiTests(ApiTestCase):
    async def create_organization(self, name: str) -> dict:
        response = await self.client.post(
            "/api/organizations",
            json={"name": name},
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

    async def create_relationship(
        self,
        organization_id: str,
        role: str,
        headers: dict[str, str] | None = None,
    ):
        return await self.client.post(
            "/api/organization-relationships",
            headers=headers,
            json={
                "organizationId": organization_id,
                "role": role,
            },
        )

    async def test_default_space_relationship_crud(self) -> None:
        organization = await self.create_organization("Power Company")
        created = await self.create_relationship(
            organization["id"],
            "  Service   Provider ",
        )
        self.assertEqual(created.status_code, 201)
        relationship = created.json()
        self.assertEqual(relationship["role"], "service provider")
        self.assertEqual(
            relationship["organizationId"],
            organization["id"],
        )
        self.assertNotIn("spaceId", relationship)

        with SessionLocal() as session:
            persisted_relationship = session.get(
                OrganizationSpaceRelationship,
                relationship["id"],
            )
            self.assertIsNotNone(persisted_relationship)
            self.assertEqual(
                persisted_relationship.space_id,
                DEFAULT_SPACE_ID,
            )

        read = await self.client.get(
            f"/api/organization-relationships/{relationship['id']}"
        )
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), relationship)

        updated = await self.client.patch(
            f"/api/organization-relationships/{relationship['id']}",
            json={"role": "  Utility   Provider "},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "utility provider")
        self.assertNotIn("spaceId", updated.json())

        listed = await self.client.get(
            "/api/organization-relationships"
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            [item["id"] for item in listed.json()],
            [relationship["id"]],
        )
        self.assertNotIn("spaceId", listed.json()[0])

        deleted = await self.client.delete(
            f"/api/organization-relationships/{relationship['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        missing = await self.client.get(
            f"/api/organization-relationships/{relationship['id']}"
        )
        self.assertEqual(missing.status_code, 404)

    async def test_explicit_active_space_controls_relationships(
        self,
    ) -> None:
        space = await self.create_space("Workshop")
        organization = await self.create_organization("Tool Supplier")
        headers = {"X-Foreman-Space-Id": space["id"]}
        created = await self.create_relationship(
            organization["id"],
            "supplier",
            headers,
        )
        self.assertEqual(created.status_code, 201)

        explicit_list = await self.client.get(
            "/api/organization-relationships",
            headers=headers,
        )
        self.assertEqual(explicit_list.status_code, 200)
        self.assertEqual(
            [item["id"] for item in explicit_list.json()],
            [created.json()["id"]],
        )

        default_list = await self.client.get(
            "/api/organization-relationships"
        )
        self.assertEqual(default_list.status_code, 200)
        self.assertEqual(default_list.json(), [])

    async def test_cross_space_relationship_access_is_not_found(
        self,
    ) -> None:
        space_a = await self.create_space("Workshop A")
        space_b = await self.create_space("Workshop B")
        organization = await self.create_organization("Shared Supplier")
        headers_a = {"X-Foreman-Space-Id": space_a["id"]}
        headers_b = {"X-Foreman-Space-Id": space_b["id"]}
        created = await self.create_relationship(
            organization["id"],
            "supplier",
            headers_a,
        )
        self.assertEqual(created.status_code, 201)
        relationship_id = created.json()["id"]

        requests = (
            self.client.get(
                f"/api/organization-relationships/{relationship_id}",
                headers=headers_b,
            ),
            self.client.patch(
                f"/api/organization-relationships/{relationship_id}",
                headers=headers_b,
                json={"role": "service provider"},
            ),
            self.client.delete(
                f"/api/organization-relationships/{relationship_id}",
                headers=headers_b,
            ),
        )

        for request in requests:
            with self.subTest():
                response = await request
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json()["detail"]["code"],
                    "ORGANIZATION_RELATIONSHIP_NOT_FOUND",
                )

        still_present = await self.client.get(
            f"/api/organization-relationships/{relationship_id}",
            headers=headers_a,
        )
        self.assertEqual(still_present.status_code, 200)

    async def test_same_organization_and_role_can_exist_across_spaces(
        self,
    ) -> None:
        space = await self.create_space("Workshop")
        organization = await self.create_organization("Shared Utility")
        payload_role = "utility"

        default_relationship = await self.create_relationship(
            organization["id"],
            payload_role,
        )
        explicit_relationship = await self.create_relationship(
            organization["id"],
            payload_role,
            {"X-Foreman-Space-Id": space["id"]},
        )

        self.assertEqual(default_relationship.status_code, 201)
        self.assertEqual(explicit_relationship.status_code, 201)
        self.assertNotEqual(
            default_relationship.json()["id"],
            explicit_relationship.json()["id"],
        )

    async def test_organization_can_have_multiple_roles_in_one_space(
        self,
    ) -> None:
        organization = await self.create_organization("Multi-role Firm")

        supplier = await self.create_relationship(
            organization["id"],
            "supplier",
        )
        employer = await self.create_relationship(
            organization["id"],
            "employer",
        )

        self.assertEqual(supplier.status_code, 201)
        self.assertEqual(employer.status_code, 201)

    async def test_normalized_duplicate_relationship_is_controlled(
        self,
    ) -> None:
        organization = await self.create_organization("Duplicate Firm")
        first = await self.create_relationship(
            organization["id"],
            "service provider",
        )
        self.assertEqual(first.status_code, 201)

        duplicate = await self.create_relationship(
            organization["id"],
            " Service   Provider",
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"]["code"],
            "ORGANIZATION_RELATIONSHIP_ALREADY_EXISTS",
        )

    async def test_update_collision_preserves_relationships(self) -> None:
        organization = await self.create_organization("Collision Firm")
        supplier = await self.create_relationship(
            organization["id"],
            "supplier",
        )
        provider = await self.create_relationship(
            organization["id"],
            "service provider",
        )
        self.assertEqual(supplier.status_code, 201)
        self.assertEqual(provider.status_code, 201)

        collision = await self.client.patch(
            f"/api/organization-relationships/{supplier.json()['id']}",
            json={"role": " Service   Provider "},
        )
        self.assertEqual(collision.status_code, 409)
        self.assertEqual(
            collision.json()["detail"]["code"],
            "ORGANIZATION_RELATIONSHIP_ALREADY_EXISTS",
        )

        supplier_read = await self.client.get(
            f"/api/organization-relationships/{supplier.json()['id']}"
        )
        provider_read = await self.client.get(
            f"/api/organization-relationships/{provider.json()['id']}"
        )
        self.assertEqual(supplier_read.status_code, 200)
        self.assertEqual(provider_read.status_code, 200)
        self.assertEqual(supplier_read.json()["role"], "supplier")
        self.assertEqual(
            provider_read.json()["role"],
            "service provider",
        )

    async def test_missing_dependencies_are_controlled(self) -> None:
        missing_organization = await self.create_relationship(
            "missing-organization",
            "supplier",
        )
        self.assertEqual(missing_organization.status_code, 404)
        self.assertEqual(
            missing_organization.json()["detail"]["code"],
            "ORGANIZATION_NOT_FOUND",
        )

        missing_space = await self.client.get(
            "/api/organization-relationships",
            headers={"X-Foreman-Space-Id": "missing-space"},
        )
        self.assertEqual(missing_space.status_code, 404)
        self.assertEqual(
            missing_space.json()["detail"]["code"],
            "SPACE_NOT_FOUND",
        )

    async def test_relationship_payload_boundaries(self) -> None:
        organization = await self.create_organization("Payload Firm")
        create_payloads = (
            {
                "organizationId": organization["id"],
                "role": "supplier",
                "spaceId": DEFAULT_SPACE_ID,
            },
            {"role": "supplier"},
            {"organizationId": None, "role": "supplier"},
            {"organizationId": organization["id"]},
            {
                "organizationId": organization["id"],
                "role": "supplier/provider",
            },
        )

        for payload in create_payloads:
            with self.subTest(payload=payload):
                response = await self.client.post(
                    "/api/organization-relationships",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)

        created = await self.create_relationship(
            organization["id"],
            "supplier",
        )
        self.assertEqual(created.status_code, 201)
        relationship_id = created.json()["id"]
        update_payloads = (
            {},
            {"role": None},
            {"organizationId": organization["id"]},
            {"spaceId": DEFAULT_SPACE_ID},
        )

        for payload in update_payloads:
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    f"/api/organization-relationships/{relationship_id}",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)
