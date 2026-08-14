from test_support import ApiTestCase


class MoneyRelationshipApiTests(ApiTestCase):
    async def test_relationship_retains_evidence_after_records_are_deleted(
        self,
    ) -> None:
        account = (
            await self.client.post(
                "/api/money/accounts",
                json={"name": "Project Cash", "kind": "cash"},
            )
        ).json()
        project = (
            await self.client.post(
                "/api/projects",
                json={"name": "Money-linked Project"},
            )
        ).json()

        payload = {
            "moneyType": "account",
            "moneyId": account["id"],
            "targetType": "project",
            "targetId": project["id"],
            "note": "Funding evidence",
        }

        created = await self.client.post(
            "/api/money/relationships",
            json=payload,
        )
        self.assertEqual(created.status_code, 201)
        relationship = created.json()
        self.assertTrue(relationship["moneyExists"])
        self.assertTrue(relationship["targetExists"])

        duplicate = await self.client.post(
            "/api/money/relationships",
            json=payload,
        )
        self.assertEqual(duplicate.status_code, 409)

        updated = await self.client.patch(
            f"/api/money/relationships/{relationship['id']}",
            json={"note": "Updated evidence"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["note"], "Updated evidence")

        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/money/accounts/{account['id']}"
                )
            ).status_code,
            204,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/projects/{project['id']}"
                )
            ).status_code,
            204,
        )

        retained = await self.client.get(
            f"/api/money/relationships/{relationship['id']}"
        )
        self.assertEqual(retained.status_code, 200)
        self.assertFalse(retained.json()["moneyExists"])
        self.assertFalse(retained.json()["targetExists"])

    async def test_relationships_are_space_isolated(self) -> None:
        space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Relationship Space"},
            )
        ).json()
        headers = {"X-Foreman-Space-Id": space["id"]}

        account = (
            await self.client.post(
                "/api/money/accounts",
                headers=headers,
                json={"name": "Remote Cash", "kind": "cash"},
            )
        ).json()
        project = (
            await self.client.post(
                "/api/projects",
                headers=headers,
                json={"name": "Remote Project"},
            )
        ).json()

        relationship = (
            await self.client.post(
                "/api/money/relationships",
                headers=headers,
                json={
                    "moneyType": "account",
                    "moneyId": account["id"],
                    "targetType": "project",
                    "targetId": project["id"],
                },
            )
        ).json()

        self.assertEqual(
            (await self.client.get("/api/money/relationships")).json(),
            [],
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/money/relationships/{relationship['id']}"
                )
            ).status_code,
            404,
        )

    async def test_relationship_creation_rejects_missing_records(self) -> None:
        rejected_money = await self.client.post(
            "/api/money/relationships",
            json={
                "moneyType": "account",
                "moneyId": "missing-account",
                "targetType": "project",
                "targetId": "missing-project",
            },
        )
        self.assertEqual(rejected_money.status_code, 404)
