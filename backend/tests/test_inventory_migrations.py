from datetime import datetime, timezone

from test_inventory_api import inventory_payload
from test_support import ApiTestCase


def browser_inventory(
    inventory_id: str,
    *,
    name: str = "Migrated inventory",
) -> dict:
    return {
        "id": inventory_id,
        **inventory_payload(name=name),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


class InventoryMigrationTests(ApiTestCase):
    async def test_migration_succeeds_and_retains_browser_data(self) -> None:
        record = browser_inventory("10000000-0000-4000-8000-000000000001")
        response = await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [record]},
        )
        result = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["migrated"], 1)
        self.assertTrue(result["browserDataRetained"])
        self.assertEqual(result["confirmedSourceIds"], [record["id"]])

    async def test_retry_is_idempotent(self) -> None:
        record = browser_inventory("10000000-0000-4000-8000-000000000002")
        await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [record]},
        )
        retry = await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [record]},
        )
        self.assertEqual(retry.json()["migrated"], 0)
        self.assertEqual(retry.json()["alreadyMigrated"], 1)
        self.assertEqual(len((await self.client.get("/api/inventory")).json()), 1)

    async def test_duplicate_is_not_overwritten(self) -> None:
        created = (
            await self.client.post(
                "/api/inventory",
                json=inventory_payload(name="Backend item"),
            )
        ).json()
        record = browser_inventory(created["id"], name="Browser item")
        response = await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [record]},
        )
        result = response.json()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["duplicates"], 1)
        self.assertIn("not overwritten", result["errors"][0]["reason"])
        stored = (
            await self.client.get(f"/api/inventory/{created['id']}")
        ).json()
        self.assertEqual(stored["name"], "Backend item")

    async def test_malformed_record_is_reported(self) -> None:
        malformed = browser_inventory(
            "10000000-0000-4000-8000-000000000003",
            name="",
        )
        response = await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [malformed]},
        )
        result = response.json()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["malformed"], 1)
        self.assertEqual(
            result["errors"][0]["sourceRecordId"],
            malformed["id"],
        )

    async def test_deleted_migrated_record_is_not_reimported(self) -> None:
        record = browser_inventory("10000000-0000-4000-8000-000000000004")
        await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [record]},
        )
        await self.client.delete(f"/api/inventory/{record['id']}")
        retry = await self.client.post(
            "/api/inventory-migrations/browser",
            json={"records": [record]},
        )
        self.assertEqual(retry.json()["alreadyMigrated"], 1)
        self.assertEqual((await self.client.get("/api/inventory")).json(), [])
