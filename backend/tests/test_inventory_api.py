from test_support import ApiTestCase


def inventory_payload(
    *,
    name: str = "Birch Plywood",
    category: str = "Lumber",
    quantity: float = 8,
    minimum: float = 2,
) -> dict:
    return {
        "name": name,
        "category": category,
        "quantity": quantity,
        "unit": "sheets",
        "minimum": minimum,
        "location": "Rack A",
        "cost": 48.5,
        "supplier": "Workshop Supply",
        "notes": "Keep dry",
    }


class InventoryApiTests(ApiTestCase):
    async def test_inventory_crud(self) -> None:
        created = await self.client.post(
            "/api/inventory",
            json=inventory_payload(),
        )
        self.assertEqual(created.status_code, 201)
        item = created.json()
        self.assertEqual(item["status"], "in-stock")
        self.assertEqual(
            (await self.client.get(f"/api/inventory/{item['id']}")).status_code,
            200,
        )

        updated = await self.client.patch(
            f"/api/inventory/{item['id']}",
            json={"quantity": 1, "notes": "Order more"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(updated.json()["isLow"])
        self.assertEqual(updated.json()["status"], "low-stock")
        self.assertEqual(len((await self.client.get("/api/inventory")).json()), 1)

        deleted = await self.client.delete(f"/api/inventory/{item['id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual((await self.client.get("/api/inventory")).json(), [])

    async def test_search_filter_and_sort(self) -> None:
        payloads = [
            inventory_payload(
                name="Washers",
                category="Hardware",
                quantity=1,
                minimum=4,
            ),
            inventory_payload(
                name="Plywood",
                category="Lumber",
                quantity=10,
                minimum=2,
            ),
            inventory_payload(
                name="Bolts",
                category="Hardware",
                quantity=20,
                minimum=5,
            ),
        ]
        for payload in payloads:
            response = await self.client.post("/api/inventory", json=payload)
            self.assertEqual(response.status_code, 201)

        search = await self.client.get("/api/inventory?search=plywood")
        self.assertEqual(
            [item["name"] for item in search.json()],
            ["Plywood"],
            str(search.request.url),
        )
        filtered = await self.client.get(
            "/api/inventory?category=Hardware&stock=low"
        )
        self.assertEqual([item["name"] for item in filtered.json()], ["Washers"])
        sorted_response = await self.client.get(
            "/api/inventory?sortBy=quantity&sortDirection=desc"
        )
        self.assertEqual(
            [item["quantity"] for item in sorted_response.json()],
            [20, 10, 1],
        )

    async def test_low_stock_out_of_stock_and_boundaries(self) -> None:
        low = (
            await self.client.post(
                "/api/inventory",
                json=inventory_payload(quantity=2, minimum=2),
            )
        ).json()
        self.assertTrue(low["isLow"])
        self.assertFalse(low["isOutOfStock"])
        self.assertIn("at or below", low["explanation"])

        out = (
            await self.client.post(
                "/api/inventory",
                json=inventory_payload(
                    name="Empty Bin",
                    quantity=0,
                    minimum=0,
                ),
            )
        ).json()
        self.assertTrue(out["isLow"])
        self.assertTrue(out["isOutOfStock"])
        self.assertEqual(out["status"], "out-of-stock")

    async def test_validation_errors_and_missing_item(self) -> None:
        for changes in (
            {"name": "   "},
            {"quantity": -1},
            {"minimum": -1},
            {"cost": -0.01},
        ):
            payload = inventory_payload()
            payload.update(changes)
            response = await self.client.post("/api/inventory", json=payload)
            self.assertEqual(response.status_code, 422)

        invalid_query = await self.client.get(
            "/api/inventory?sortBy=unknown"
        )
        self.assertEqual(invalid_query.status_code, 422)
        self.assertEqual(
            (await self.client.get("/api/inventory/missing")).status_code,
            404,
        )
