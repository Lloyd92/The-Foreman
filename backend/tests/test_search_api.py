from test_support import ApiTestCase


class UniversalSearchApiTests(ApiTestCase):
    async def test_search_combines_authoritative_space_records(self) -> None:
        project = (
            await self.client.post(
                "/api/projects",
                json={
                    "name": "Needle Project",
                    "description": "Workshop reference",
                },
            )
        ).json()

        library = (
            await self.client.post(
                "/api/library",
                json={
                    "kind": "note",
                    "title": "Needle Note",
                    "content": "Durable reference",
                },
            )
        ).json()

        person = (
            await self.client.post(
                "/api/people",
                json={
                    "displayName": "Needle Person",
                    "description": "Household contact",
                },
            )
        ).json()
        member = await self.client.post(
            "/api/members",
            json={
                "personId": person["id"],
                "role": "member",
            },
        )
        self.assertEqual(member.status_code, 201)

        organization = (
            await self.client.post(
                "/api/organizations",
                json={
                    "name": "Needle Supplier",
                    "description": "Workshop supplier",
                },
            )
        ).json()
        relationship = await self.client.post(
            "/api/organization-relationships",
            json={
                "organizationId": organization["id"],
                "role": "supplier",
            },
        )
        self.assertEqual(relationship.status_code, 201)

        response = await self.client.get(
            "/api/search",
            params={"q": "needle"},
        )
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["query"], "needle")

        results = body["results"]
        self.assertEqual(
            [
                (item["sourceType"], item["sourceId"])
                for item in results
            ],
            [
                ("project", project["id"]),
                ("library_record", library["id"]),
                ("person", person["id"]),
                ("organization", organization["id"]),
            ],
        )

        for item in results:
            self.assertIn("title", item)
            self.assertIn("summary", item)
            self.assertIn("matchedText", item)

    async def test_unlinked_identity_records_are_not_searchable(self) -> None:
        await self.client.post(
            "/api/people",
            json={"displayName": "Hidden Needle Person"},
        )
        await self.client.post(
            "/api/organizations",
            json={"name": "Hidden Needle Organization"},
        )

        response = await self.client.get(
            "/api/search",
            params={"q": "hidden needle"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    async def test_search_is_active_space_isolated(self) -> None:
        space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Search Space"},
            )
        ).json()
        headers = {"X-Foreman-Space-Id": space["id"]}

        remote = await self.client.post(
            "/api/library",
            headers=headers,
            json={
                "kind": "note",
                "title": "Remote Needle",
            },
        )
        self.assertEqual(remote.status_code, 201)

        default_search = await self.client.get(
            "/api/search",
            params={"q": "remote needle"},
        )
        self.assertEqual(default_search.status_code, 200)
        self.assertEqual(default_search.json()["results"], [])

        selected_search = await self.client.get(
            "/api/search",
            headers=headers,
            params={"q": "remote needle"},
        )
        self.assertEqual(selected_search.status_code, 200)
        self.assertEqual(
            [
                item["sourceId"]
                for item in selected_search.json()["results"]
            ],
            [remote.json()["id"]],
        )

    async def test_search_query_validation(self) -> None:
        missing = await self.client.get("/api/search")
        self.assertEqual(missing.status_code, 422)

        blank = await self.client.get(
            "/api/search",
            params={"q": "   "},
        )
        self.assertEqual(blank.status_code, 422)
        self.assertEqual(
            blank.json()["detail"]["code"],
            "SEARCH_QUERY_REQUIRED",
        )

        too_long = await self.client.get(
            "/api/search",
            params={"q": "x" * 161},
        )
        self.assertEqual(too_long.status_code, 422)
