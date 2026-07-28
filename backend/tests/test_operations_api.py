from test_support import ApiTestCase


class OperationalFactsApiTests(ApiTestCase):
    async def test_operational_facts_expose_project_and_task_state(
        self,
    ) -> None:
        active_project = await self.create_project(
            name="Active Build",
            status="active",
        )
        await self.create_project(
            name="Planning Build",
            status="planning",
        )

        incomplete_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Open task",
                "priority": "high",
                "projectId": active_project["id"],
            },
        )
        completed_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Finished task",
                "priority": "low",
            },
        )
        await self.client.post(
            f"/api/tasks/{completed_response.json()['id']}/complete"
        )
        inventory_response = await self.client.post(
            "/api/inventory",
            json={
                "name": "Shop Towels",
                "category": "Consumables",
                "quantity": 0,
                "unit": "rolls",
                "minimum": 2,
                "location": "Cabinet",
            },
        )
        self.assertEqual(inventory_response.status_code, 201)

        response = await self.client.get("/api/operational-facts")

        self.assertEqual(response.status_code, 200)
        facts = response.json()
        self.assertEqual(len(facts["activeProjects"]), 1)
        self.assertEqual(len(facts["incompleteTasks"]), 1)
        self.assertEqual(len(facts["completedTasks"]), 1)
        self.assertEqual(facts["taskPriorityCounts"]["high"], 1)
        self.assertEqual(facts["taskPriorityCounts"]["low"], 1)
        self.assertEqual(facts["projectStatusCounts"]["active"], 1)
        self.assertEqual(facts["projectStatusCounts"]["planning"], 1)
        self.assertEqual(
            facts["incompleteTasks"][0]["id"],
            incomplete_response.json()["id"],
        )
        inventory_fact = facts["inventory"][0]
        self.assertEqual(inventory_fact["sourceModule"], "inventory")
        self.assertEqual(
            inventory_fact["recordId"],
            inventory_response.json()["id"],
        )
        self.assertEqual(inventory_fact["currentQuantity"], 0)
        self.assertEqual(inventory_fact["lowStockThreshold"], 2)
        self.assertTrue(inventory_fact["isLow"])
        self.assertTrue(inventory_fact["isOutOfStock"])
        self.assertEqual(inventory_fact["status"], "out-of-stock")
        self.assertTrue(inventory_fact["explanation"])
