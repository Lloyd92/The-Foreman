import threading
import time
import unittest
from unittest.mock import patch

from app.core.database import database_maintenance
from app.core.maintenance import (
    DatabaseMaintenanceActive,
    DatabaseMaintenanceConflict,
    DatabaseMaintenanceCoordinator,
    DatabaseMaintenanceDrainTimeout,
)
from test_support import ApiTestCase


class MaintenanceCoordinatorTests(unittest.TestCase):

    def test_new_database_access_is_rejected_during_maintenance(
        self,
    ) -> None:
        coordinator = DatabaseMaintenanceCoordinator()

        with coordinator.maintenance():
            with self.assertRaises(DatabaseMaintenanceActive):
                with coordinator.database_access():
                    pass

    def test_maintenance_waits_for_active_database_access(
        self,
    ) -> None:
        coordinator = DatabaseMaintenanceCoordinator()
        entered = threading.Event()
        errors: list[BaseException] = []

        coordinator.acquire_database_access()

        def enter_maintenance() -> None:
            try:
                with coordinator.maintenance(timeout_seconds=1):
                    entered.set()
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=enter_maintenance)
        thread.start()

        try:
            deadline = time.monotonic() + 1

            while (
                not coordinator.snapshot().maintenance_active
                and time.monotonic() < deadline
            ):
                time.sleep(0.001)

            self.assertTrue(
                coordinator.snapshot().maintenance_active
            )
            self.assertFalse(entered.is_set())
        finally:
            coordinator.release_database_access()

        self.assertTrue(entered.wait(timeout=1))
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_drain_timeout_restores_normal_access(self) -> None:
        coordinator = DatabaseMaintenanceCoordinator()
        coordinator.acquire_database_access()

        try:
            with self.assertRaises(DatabaseMaintenanceDrainTimeout):
                coordinator.enter_maintenance(timeout_seconds=0)

            state = coordinator.snapshot()
            self.assertFalse(state.maintenance_active)
            self.assertEqual(state.active_database_operations, 1)
        finally:
            coordinator.release_database_access()

        with coordinator.database_access():
            pass

    def test_second_maintenance_owner_is_rejected(self) -> None:
        coordinator = DatabaseMaintenanceCoordinator()

        with coordinator.maintenance():
            with self.assertRaises(DatabaseMaintenanceConflict):
                coordinator.enter_maintenance()


class DatabaseMaintenanceApiTests(ApiTestCase):

    def assert_maintenance_response(self, response) -> None:
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "DATABASE_MAINTENANCE_ACTIVE",
                    "message": (
                        "The Foreman is temporarily unavailable while "
                        "database maintenance is in progress."
                    ),
                }
            },
        )
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["retry-after"], "1")

    async def test_database_route_returns_stable_maintenance_response(
        self,
    ) -> None:
        with database_maintenance():
            response = await self.client.get("/api/projects")

        self.assert_maintenance_response(response)

    async def test_health_does_not_reopen_database_during_maintenance(
        self,
    ) -> None:
        with patch(
            "app.repositories.health.engine.connect"
        ) as connect:
            with database_maintenance():
                response = await self.client.get("/api/health")

        self.assert_maintenance_response(response)
        connect.assert_not_called()

    async def test_status_remains_available_during_maintenance(
        self,
    ) -> None:
        with database_maintenance():
            response = await self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "online")

    async def test_backup_creation_does_not_start_during_maintenance(
        self,
    ) -> None:
        with (
            patch(
                "app.api.recovery.tempfile.mkdtemp"
            ) as create_directory,
            patch(
                "app.api.recovery.create_verified_backup_package"
            ) as create_backup,
        ):
            with database_maintenance():
                response = await self.client.post(
                    "/api/recovery/backups"
                )

        self.assert_maintenance_response(response)
        create_directory.assert_not_called()
        create_backup.assert_not_called()

    async def test_database_routes_resume_after_maintenance(
        self,
    ) -> None:
        with database_maintenance():
            blocked = await self.client.get("/api/projects")

        resumed = await self.client.get("/api/projects")

        self.assert_maintenance_response(blocked)
        self.assertEqual(resumed.status_code, 200)

    async def test_database_maintenance_disposes_connections(
        self,
    ) -> None:
        with patch("app.core.database.engine.dispose") as dispose:
            with database_maintenance():
                pass

        dispose.assert_called_once_with()
