from unittest.mock import patch

from test_support import ApiTestCase


class SystemApiTests(ApiTestCase):

    async def test_status_preserves_compatibility_contract(self) -> None:
        response = await self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "application": "The Foreman",
                "company": "HardHead Works",
                "status": "online",
                "version": "0.7.5",
            },
        )

    async def test_health_reports_database_availability(self) -> None:
        response = await self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertEqual(response.json()["database"], "online")
        self.assertTrue(response.json()["reason"])

    async def test_health_fails_when_database_is_offline(self) -> None:
        with patch(
            "app.services.system.database_is_available",
            return_value=False,
        ):
            response = await self.client.get("/api/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Application is available but the database is offline.",
        )
