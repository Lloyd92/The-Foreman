from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.organization import Organization
from app.models.organization_space_relationship import (
    OrganizationSpaceRelationship,
)
from test_support import ApiTestCase


class OrganizationsApiTests(ApiTestCase):
    async def test_organization_crud_and_duplicate_names(self) -> None:
        first = await self.client.post(
            "/api/organizations",
            json={
                "name": "  Northwind Cooperative  ",
                "description": "Installation-wide supplier",
            },
        )
        self.assertEqual(first.status_code, 201)
        organization = first.json()
        self.assertEqual(organization["name"], "Northwind Cooperative")

        read = await self.client.get(
            f"/api/organizations/{organization['id']}"
        )
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), organization)

        updated = await self.client.patch(
            f"/api/organizations/{organization['id']}",
            json={
                "name": "  Acme Cooperative  ",
                "description": "Updated installation-wide supplier",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Acme Cooperative")

        duplicate_name = await self.client.post(
            "/api/organizations",
            json={"name": "Acme Cooperative"},
        )
        self.assertEqual(duplicate_name.status_code, 201)

        listed = await self.client.get("/api/organizations")
        self.assertEqual(listed.status_code, 200)
        listed_organizations = listed.json()
        self.assertEqual(len(listed_organizations), 2)
        self.assertEqual(
            [
                (item["name"], item["id"])
                for item in listed_organizations
            ],
            sorted(
                (item["name"], item["id"])
                for item in listed_organizations
            ),
        )

        deleted = await self.client.delete(
            f"/api/organizations/{duplicate_name.json()['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_referenced_organization_cannot_be_deleted(self) -> None:
        with SessionLocal() as session:
            organization = Organization(name="Referenced Organization")
            session.add(organization)
            session.flush()
            session.add(
                OrganizationSpaceRelationship(
                    space_id=DEFAULT_SPACE_ID,
                    organization_id=organization.id,
                    role="supplier",
                )
            )
            session.commit()
            organization_id = organization.id

        response = await self.client.delete(
            f"/api/organizations/{organization_id}"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "ORGANIZATION_IN_USE",
        )

    async def test_missing_organization_and_invalid_updates_are_controlled(
        self,
    ) -> None:
        missing_read = await self.client.get(
            "/api/organizations/missing"
        )
        self.assertEqual(missing_read.status_code, 404)
        self.assertEqual(
            missing_read.json()["detail"]["code"],
            "ORGANIZATION_NOT_FOUND",
        )

        missing_update = await self.client.patch(
            "/api/organizations/missing",
            json={"description": "Missing"},
        )
        self.assertEqual(missing_update.status_code, 404)
        self.assertEqual(
            missing_update.json()["detail"]["code"],
            "ORGANIZATION_NOT_FOUND",
        )

        missing_delete = await self.client.delete(
            "/api/organizations/missing"
        )
        self.assertEqual(missing_delete.status_code, 404)
        self.assertEqual(
            missing_delete.json()["detail"]["code"],
            "ORGANIZATION_NOT_FOUND",
        )

        created = await self.client.post(
            "/api/organizations",
            json={"name": "Test Organization"},
        )
        organization_id = created.json()["id"]

        for payload in (
            {},
            {"name": None},
            {"description": None},
        ):
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    f"/api/organizations/{organization_id}",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)
