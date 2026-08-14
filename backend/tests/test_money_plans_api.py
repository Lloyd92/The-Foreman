from test_support import ApiTestCase


class MoneyPlansApiTests(ApiTestCase):
    async def test_budget_and_obligation_crud(self) -> None:
        account = (
            await self.client.post(
                "/api/money/accounts",
                json={"name": "Checking", "kind": "checking"},
            )
        ).json()
        category = (
            await self.client.post(
                "/api/money/categories",
                json={"kind": "expense", "name": "Utilities"},
            )
        ).json()

        budget = await self.client.post(
            "/api/money/budgets",
            json={
                "categoryId": category["id"],
                "name": "Monthly Utilities",
                "amountMinor": 30000,
                "currencyCode": "USD",
                "startDate": "2026-08-01",
                "endDate": "2026-08-31",
            },
        )
        self.assertEqual(budget.status_code, 201)
        budget = budget.json()
        self.assertNotIn("spaceId", budget)

        updated_budget = await self.client.patch(
            f"/api/money/budgets/{budget['id']}",
            json={"amountMinor": 32500},
        )
        self.assertEqual(updated_budget.status_code, 200)

        obligation = await self.client.post(
            "/api/money/obligations",
            json={
                "accountId": account["id"],
                "categoryId": category["id"],
                "name": "Electric Bill",
                "amountMinor": 18000,
                "currencyCode": "USD",
                "frequency": "monthly",
                "intervalValue": 1,
                "startDate": "2026-08-15",
            },
        )
        self.assertEqual(obligation.status_code, 201)
        obligation = obligation.json()
        self.assertNotIn("spaceId", obligation)

        updated_obligation = await self.client.patch(
            f"/api/money/obligations/{obligation['id']}",
            json={"amountMinor": 19000},
        )
        self.assertEqual(updated_obligation.status_code, 200)

        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/money/budgets/{budget['id']}"
                )
            ).status_code,
            204,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    f"/api/money/obligations/{obligation['id']}"
                )
            ).status_code,
            204,
        )

    async def test_plans_validate_dates_and_space_references(self) -> None:
        bad_budget = await self.client.post(
            "/api/money/budgets",
            json={
                "name": "Invalid Dates",
                "amountMinor": 1000,
                "startDate": "2026-09-01",
                "endDate": "2026-08-01",
            },
        )
        self.assertEqual(bad_budget.status_code, 422)

        other_space = (
            await self.client.post(
                "/api/spaces",
                json={"name": "Other Money Space"},
            )
        ).json()
        headers = {"X-Foreman-Space-Id": other_space["id"]}

        other_account = (
            await self.client.post(
                "/api/money/accounts",
                headers=headers,
                json={"name": "Other Cash", "kind": "cash"},
            )
        ).json()

        rejected = await self.client.post(
            "/api/money/obligations",
            json={
                "accountId": other_account["id"],
                "name": "Cross-space obligation",
                "amountMinor": 1000,
                "frequency": "monthly",
                "startDate": "2026-08-13",
            },
        )
        self.assertEqual(rejected.status_code, 404)
