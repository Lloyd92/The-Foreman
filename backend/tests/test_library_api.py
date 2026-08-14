from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.library_record import LibraryRecord
from test_support import ApiTestCase


def library_payload(
    *,
    kind: str = "manual",
    title: str = "CNC Router Manual",
    content: str = "Commissioning and maintenance reference.",
    reference_location: str = "Workshop binder",
) -> dict:
    return {
        "kind": kind,
        "title": title,
        "content": content,
        "referenceLocation": reference_location,
    }


class LibraryApiTests(ApiTestCase):
    async def test_library_crud_is_backend_and_space_authoritative(
        self,
    ) -> None:
        created = await self.client.post(
            "/api/library",
            json=library_payload(),
        )
        self.assertEqual(created.status_code, 201)

        record = created.json()
        self.assertNotIn("spaceId", record)
        self.assertEqual(record["title"], "CNC Router Manual")

        with SessionLocal() as session:
            self.assertEqual(
                session.scalar(
                    select(LibraryRecord.space_id).where(
                        LibraryRecord.id == record["id"]
                    )
                ),
                DEFAULT_SPACE_ID,
            )

        read = await self.client.get(
            f"/api/library/{record['id']}"
        )
        self.assertEqual(read.status_code, 200)

        updated = await self.client.patch(
            f"/api/library/{record['id']}",
            json={
                "kind": "document",
                "content": "Updated durable reference.",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["kind"], "document")

        listed = await self.client.get("/api/library")
        self.assertEqual(
            [item["id"] for item in listed.json()],
            [record["id"]],
        )

        deleted = await self.client.delete(
            f"/api/library/{record['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            (await self.client.get("/api/library")).json(),
            [],
        )

    async def test_library_search_filter_and_sort(self) -> None:
        payloads = [
            library_payload(
                kind="note",
                title="Shed Measurements",
                content="Door opening measurements.",
            ),
            library_payload(
                kind="manual",
                title="Mower Manual",
                content="Deck maintenance reference.",
            ),
            library_payload(
                kind="decision",
                title="Workshop Roof Decision",
                content="Use a gable roof.",
            ),
        ]

        for payload in payloads:
            response = await self.client.post(
                "/api/library",
                json=payload,
            )
            self.assertEqual(response.status_code, 201)

        search = await self.client.get(
            "/api/library",
            params={"search": "gable"},
        )
        self.assertEqual(
            [item["title"] for item in search.json()],
            ["Workshop Roof Decision"],
        )

        filtered = await self.client.get(
            "/api/library",
            params={"kind": "manual"},
        )
        self.assertEqual(
            [item["title"] for item in filtered.json()],
            ["Mower Manual"],
        )

        sorted_response = await self.client.get(
            "/api/library",
            params={
                "sortBy": "title",
                "sortDirection": "desc",
            },
        )
        self.assertEqual(
            [item["title"] for item in sorted_response.json()],
            [
                "Workshop Roof Decision",
                "Shed Measurements",
                "Mower Manual",
            ],
        )

    async def test_library_validation_and_missing_errors(
        self,
    ) -> None:
        blank = library_payload(title="   ")
        response = await self.client.post(
            "/api/library",
            json=blank,
        )
        self.assertEqual(response.status_code, 422)

        invalid_kind = library_payload(kind="unknown")
        response = await self.client.post(
            "/api/library",
            json=invalid_kind,
        )
        self.assertEqual(response.status_code, 422)

        invalid_query = await self.client.get(
            "/api/library?sortBy=unknown"
        )
        self.assertEqual(invalid_query.status_code, 422)

        missing = await self.client.get(
            "/api/library/missing"
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "LIBRARY_RECORD_NOT_FOUND",
        )

        empty_update = await self.client.patch(
            "/api/library/missing",
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

        created = (
            await self.client.post(
                "/api/library",
                json=library_payload(title="Null Boundary"),
            )
        ).json()

        for field in (
            "kind",
            "title",
            "content",
            "referenceLocation",
        ):
            with self.subTest(null_field=field):
                response = await self.client.patch(
                    f"/api/library/{created['id']}",
                    json={field: None},
                )
                self.assertEqual(response.status_code, 422)

        payload = library_payload()
        payload["spaceId"] = "client-space"
        forbidden_space = await self.client.post(
            "/api/library",
            json=payload,
        )
        self.assertEqual(forbidden_space.status_code, 422)

    async def test_library_records_are_isolated_by_active_space(
        self,
    ) -> None:
        created_space = await self.client.post(
            "/api/spaces",
            json={"name": "Workshop"},
        )
        self.assertEqual(created_space.status_code, 201)

        space_id = created_space.json()["id"]
        headers = {"X-Foreman-Space-Id": space_id}

        workshop_record = (
            await self.client.post(
                "/api/library",
                headers=headers,
                json=library_payload(
                    title="Workshop Reference"
                ),
            )
        ).json()

        self.assertEqual(
            (await self.client.get("/api/library")).json(),
            [],
        )

        for method in ("get", "patch", "delete"):
            kwargs = {}
            if method == "patch":
                kwargs["json"] = {"title": "Leaked Update"}

            response = await getattr(self.client, method)(
                f"/api/library/{workshop_record['id']}",
                **kwargs,
            )
            self.assertEqual(response.status_code, 404)

        selected = await self.client.get(
            f"/api/library/{workshop_record['id']}",
            headers=headers,
        )
        self.assertEqual(selected.status_code, 200)
