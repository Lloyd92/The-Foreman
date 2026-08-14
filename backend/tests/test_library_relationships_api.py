from test_support import ApiTestCase


async def create_library_record(client, *, headers=None, title="Reference"):
    response = await client.post(
        "/api/library",
        headers=headers,
        json={
            "kind": "note",
            "title": title,
            "content": "Relationship evidence.",
        },
    )
    assert response.status_code == 201
    return response.json()


async def create_project(client, *, headers=None, name="Linked Project"):
    response = await client.post(
        "/api/projects",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()


class LibraryRelationshipApiTests(ApiTestCase):
    async def test_relationship_lifecycle_retains_target_evidence(
        self,
    ) -> None:
        record = await create_library_record(self.client)
        project = await create_project(self.client)

        payload = {
            "targetType": "project",
            "targetId": project["id"],
            "note": "Reference evidence",
        }

        created = await self.client.post(
            f"/api/library/{record['id']}/relationships",
            json=payload,
        )
        self.assertEqual(created.status_code, 201)

        relationship = created.json()
        self.assertEqual(
            relationship["libraryRecordId"],
            record["id"],
        )
        self.assertTrue(relationship["targetExists"])

        duplicate = await self.client.post(
            f"/api/library/{record['id']}/relationships",
            json=payload,
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.json()["detail"]["code"],
            "LIBRARY_RELATIONSHIP_CONFLICT",
        )

        updated = await self.client.patch(
            (
                f"/api/library/{record['id']}/relationships/"
                f"{relationship['id']}"
            ),
            json={"note": "Updated evidence"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["note"],
            "Updated evidence",
        )

        deleted_target = await self.client.delete(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(deleted_target.status_code, 204)

        retained = await self.client.get(
            f"/api/library/{record['id']}/relationships"
        )
        self.assertEqual(retained.status_code, 200)
        self.assertEqual(len(retained.json()), 1)
        self.assertFalse(retained.json()[0]["targetExists"])

        deleted_relationship = await self.client.delete(
            (
                f"/api/library/{record['id']}/relationships/"
                f"{relationship['id']}"
            )
        )
        self.assertEqual(deleted_relationship.status_code, 204)
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/library/{record['id']}/relationships"
                )
            ).json(),
            [],
        )

    async def test_relationships_are_space_isolated(self) -> None:
        space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Library Relationship Space"},
            )
        ).json()
        headers = {"X-Foreman-Space-Id": space["id"]}

        record = await create_library_record(
            self.client,
            headers=headers,
            title="Remote Reference",
        )
        project = await create_project(
            self.client,
            headers=headers,
            name="Remote Project",
        )

        relationship = (
            await self.client.post(
                f"/api/library/{record['id']}/relationships",
                headers=headers,
                json={
                    "targetType": "project",
                    "targetId": project["id"],
                },
            )
        ).json()

        self.assertEqual(
            (
                await self.client.get(
                    f"/api/library/{record['id']}/relationships"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    (
                        f"/api/library/{record['id']}/relationships/"
                        f"{relationship['id']}"
                    ),
                    json={"note": "Leaked update"},
                )
            ).status_code,
            404,
        )

        selected = await self.client.get(
            f"/api/library/{record['id']}/relationships",
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(
            selected.json()[0]["id"],
            relationship["id"],
        )

    async def test_relationship_creation_rejects_missing_or_cross_space_target(
        self,
    ) -> None:
        record = await create_library_record(self.client)

        missing = await self.client.post(
            f"/api/library/{record['id']}/relationships",
            json={
                "targetType": "project",
                "targetId": "missing-project",
            },
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "LIBRARY_RELATIONSHIP_TARGET_NOT_FOUND",
        )

        space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Other Space"},
            )
        ).json()
        headers = {"X-Foreman-Space-Id": space["id"]}
        remote_project = await create_project(
            self.client,
            headers=headers,
            name="Other Space Project",
        )

        cross_space = await self.client.post(
            f"/api/library/{record['id']}/relationships",
            json={
                "targetType": "project",
                "targetId": remote_project["id"],
            },
        )
        self.assertEqual(cross_space.status_code, 404)

    async def test_relationship_validation_and_missing_record_errors(
        self,
    ) -> None:
        record = await create_library_record(self.client)
        project = await create_project(self.client)

        invalid_type = await self.client.post(
            f"/api/library/{record['id']}/relationships",
            json={
                "targetType": "unknown",
                "targetId": project["id"],
            },
        )
        self.assertEqual(invalid_type.status_code, 422)

        missing_record = await self.client.get(
            "/api/library/missing/relationships"
        )
        self.assertEqual(missing_record.status_code, 404)
        self.assertEqual(
            missing_record.json()["detail"]["code"],
            "LIBRARY_RECORD_NOT_FOUND",
        )

        relationship = (
            await self.client.post(
                f"/api/library/{record['id']}/relationships",
                json={
                    "targetType": "project",
                    "targetId": project["id"],
                },
            )
        ).json()

        empty_update = await self.client.patch(
            (
                f"/api/library/{record['id']}/relationships/"
                f"{relationship['id']}"
            ),
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

        null_update = await self.client.patch(
            (
                f"/api/library/{record['id']}/relationships/"
                f"{relationship['id']}"
            ),
            json={"note": None},
        )
        self.assertEqual(null_update.status_code, 422)
