from __future__ import annotations

import shutil

from app.core.config import DATABASE_URL
from app.core.database import engine
from app.core.maintenance import maintenance_coordinator
from app.services.recovery import (
    resolve_sqlite_database_path,
    verify_backup_package,
)
from tests.test_support import ApiTestCase


CONFIRMATION_PHRASE = "RESTORE THE FOREMAN"


class RecoveryRoundTripApiTests(ApiTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.live_database_path = resolve_sqlite_database_path(
            DATABASE_URL
        )
        self.recovery_root = (
            self.live_database_path.parent / "recovery"
        )
        engine.dispose()
        shutil.rmtree(self.recovery_root, ignore_errors=True)

    async def asyncTearDown(self) -> None:
        try:
            engine.dispose()
            state = maintenance_coordinator.snapshot()

            if state.emergency_latched:
                maintenance_coordinator.clear_emergency_latch()

            shutil.rmtree(self.recovery_root, ignore_errors=True)
        finally:
            await super().asyncTearDown()

    async def project_ids(self) -> set[str]:
        response = await self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        return {
            str(project["id"])
            for project in response.json()
        }

    async def test_backup_preflight_activation_restores_api_state(
        self,
    ) -> None:
        preserved = await self.create_project(
            name="Preserved Before Backup",
            status="active",
        )

        backup_response = await self.client.post(
            "/api/recovery/backups"
        )

        self.assertEqual(backup_response.status_code, 200)
        self.assertEqual(
            backup_response.headers["content-type"],
            "application/zip",
        )
        self.assertTrue(backup_response.content.startswith(b"PK"))

        transient = await self.create_project(
            name="Created After Backup",
            status="active",
        )
        self.assertEqual(
            await self.project_ids(),
            {preserved["id"], transient["id"]},
        )

        preflight_response = await self.client.post(
            "/api/recovery/restores/preflight",
            content=backup_response.content,
            headers={"Content-Type": "application/zip"},
        )

        self.assertEqual(preflight_response.status_code, 200)
        preflight = preflight_response.json()
        self.assertEqual(
            preflight["confirmationPhrase"],
            CONFIRMATION_PHRASE,
        )
        self.assertEqual(
            preflight["recordCounts"]["projects"],
            1,
        )

        activation_response = await self.client.post(
            "/api/recovery/restores/activate",
            json={
                "token": preflight["token"],
                "confirmationPhrase": CONFIRMATION_PHRASE,
            },
        )

        self.assertEqual(activation_response.status_code, 200)
        activation = activation_response.json()
        self.assertEqual(activation["status"], "restored")
        self.assertTrue(activation["safetyBackupRetained"])
        self.assertTrue(activation["reloadRequired"])
        self.assertEqual(
            activation["recordCounts"]["projects"],
            1,
        )

        self.assertEqual(
            await self.project_ids(),
            {preserved["id"]},
        )

        health_response = await self.client.get("/api/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(
            health_response.json()["database"],
            "online",
        )

        safety_directory = (
            self.recovery_root / "safety-backups"
        )
        safety_packages = sorted(safety_directory.glob("*.zip"))
        self.assertEqual(len(safety_packages), 1)
        self.assertTrue(
            verify_backup_package(
                safety_packages[0]
            ).result.is_valid
        )

        preflight_directory = self.recovery_root / "preflight"
        self.assertTrue(preflight_directory.is_dir())
        self.assertEqual(list(preflight_directory.iterdir()), [])
