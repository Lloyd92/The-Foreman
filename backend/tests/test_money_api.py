from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.money_account import MoneyAccount
from test_support import ApiTestCase


class MoneyApiTests(ApiTestCase):
    async def test_account_crud_uses_minor_units(self) -> None:
        created_response = await self.client.post(
            "/api/money/accounts",
            json={
                "name": "Household Checking",
                "kind": "checking",
                "currencyCode": "USD",
                "openingBalanceMinor": 123456,
                "isActive": True,
                "notes": "Primary account",
            },
        )
        self.assertEqual(created_response.status_code, 201)
        account = created_response.json()

        self.assertNotIn("spaceId", account)
        self.assertEqual(account["name"], "Household Checking")
        self.assertEqual(account["kind"], "checking")
        self.assertEqual(account["currencyCode"], "USD")
        self.assertEqual(account["openingBalanceMinor"], 123456)

        with SessionLocal() as session:
            self.assertEqual(
                session.scalar(
                    select(MoneyAccount.space_id).where(
                        MoneyAccount.id == account["id"]
                    )
                ),
                DEFAULT_SPACE_ID,
            )

        updated = await self.client.patch(
            f"/api/money/accounts/{account['id']}",
            json={
                "name": "Main Checking",
                "openingBalanceMinor": -2500,
                "isActive": False,
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Main Checking")
        self.assertEqual(updated.json()["openingBalanceMinor"], -2500)
        self.assertFalse(updated.json()["isActive"])

        read = await self.client.get(
            f"/api/money/accounts/{account['id']}"
        )
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["name"], "Main Checking")

        deleted = await self.client.delete(
            f"/api/money/accounts/{account['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            (await self.client.get("/api/money/accounts")).json(),
            [],
        )

    async def test_account_validation(self) -> None:
        invalid_currency = await self.client.post(
            "/api/money/accounts",
            json={
                "name": "Bad Currency",
                "currencyCode": "US",
            },
        )
        self.assertEqual(invalid_currency.status_code, 422)

        forbidden_space = await self.client.post(
            "/api/money/accounts",
            json={
                "name": "Injected Space",
                "spaceId": "client-space",
            },
        )
        self.assertEqual(forbidden_space.status_code, 422)

        created = (
            await self.client.post(
                "/api/money/accounts",
                json={"name": "Valid Account"},
            )
        ).json()

        empty_update = await self.client.patch(
            f"/api/money/accounts/{created['id']}",
            json={},
        )
        self.assertEqual(empty_update.status_code, 422)

        null_update = await self.client.patch(
            f"/api/money/accounts/{created['id']}",
            json={"name": None},
        )
        self.assertEqual(null_update.status_code, 422)

    async def test_category_crud_and_duplicate_protection(self) -> None:
        created_response = await self.client.post(
            "/api/money/categories",
            json={
                "kind": "expense",
                "name": "Utilities",
            },
        )
        self.assertEqual(created_response.status_code, 201)
        category = created_response.json()

        self.assertNotIn("spaceId", category)
        self.assertEqual(category["kind"], "expense")
        self.assertEqual(category["name"], "Utilities")

        duplicate = await self.client.post(
            "/api/money/categories",
            json={
                "kind": "expense",
                "name": "Utilities",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        other_kind = await self.client.post(
            "/api/money/categories",
            json={
                "kind": "income",
                "name": "Utilities",
            },
        )
        self.assertEqual(other_kind.status_code, 201)

        updated = await self.client.patch(
            f"/api/money/categories/{category['id']}",
            json={"name": "Household Utilities"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.json()["name"],
            "Household Utilities",
        )

        read = await self.client.get(
            f"/api/money/categories/{category['id']}"
        )
        self.assertEqual(read.status_code, 200)

        deleted = await self.client.delete(
            f"/api/money/categories/{category['id']}"
        )
        self.assertEqual(deleted.status_code, 204)

    async def test_category_validation(self) -> None:
        invalid_kind = await self.client.post(
            "/api/money/categories",
            json={
                "kind": "asset",
                "name": "Invalid",
            },
        )
        self.assertEqual(invalid_kind.status_code, 422)

        forbidden_space = await self.client.post(
            "/api/money/categories",
            json={
                "kind": "expense",
                "name": "Injected Space",
                "spaceId": "client-space",
            },
        )
        self.assertEqual(forbidden_space.status_code, 422)

    async def test_money_records_are_isolated_by_active_space(self) -> None:
        created_space = await self.client.post(
            "/api/spaces",
            json={"name": "Workshop"},
        )
        self.assertEqual(created_space.status_code, 201)
        space_id = created_space.json()["id"]
        headers = {"X-Foreman-Space-Id": space_id}

        workshop_account = (
            await self.client.post(
                "/api/money/accounts",
                headers=headers,
                json={
                    "name": "Workshop Cash",
                    "kind": "cash",
                },
            )
        ).json()

        workshop_category = (
            await self.client.post(
                "/api/money/categories",
                headers=headers,
                json={
                    "kind": "expense",
                    "name": "Shop Supplies",
                },
            )
        ).json()

        self.assertEqual(
            (await self.client.get("/api/money/accounts")).json(),
            [],
        )
        self.assertEqual(
            (await self.client.get("/api/money/categories")).json(),
            [],
        )

        for path in (
            f"/api/money/accounts/{workshop_account['id']}",
            f"/api/money/categories/{workshop_category['id']}",
        ):
            self.assertEqual(
                (await self.client.get(path)).status_code,
                404,
            )
            self.assertEqual(
                (
                    await self.client.patch(
                        path,
                        json={"name": "Leaked Update"},
                    )
                ).status_code,
                404,
            )
            self.assertEqual(
                (await self.client.delete(path)).status_code,
                404,
            )
