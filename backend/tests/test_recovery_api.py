import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    DATABASE_URL,
)
from app.services.recovery import RecoveryContractError
from test_support import ApiTestCase


BACKUP_FILENAME = "foreman-backup-20260731T220000Z.zip"
BACKUP_BYTES = b"verified-backup-package"


class RecoveryApiTests(ApiTestCase):

    async def test_download_returns_verified_package_and_cleans_up(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "download-work"
            temporary_directory.mkdir()
            package_path = temporary_directory / BACKUP_FILENAME

            def create_package(*args, **kwargs):
                package_path.write_bytes(BACKUP_BYTES)
                return SimpleNamespace(path=package_path)

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.create_verified_backup_package",
                    side_effect=create_package,
                ) as create_backup,
            ):
                response = await self.client.post(
                    "/api/recovery/backups"
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, BACKUP_BYTES)
            self.assertEqual(
                response.headers["content-type"],
                "application/zip",
            )
            self.assertIn(
                f'filename="{BACKUP_FILENAME}"',
                response.headers["content-disposition"],
            )
            self.assertEqual(
                response.headers["cache-control"],
                "no-store",
            )
            self.assertEqual(
                response.headers["x-content-type-options"],
                "nosniff",
            )
            self.assertFalse(temporary_directory.exists())
            create_backup.assert_called_once_with(
                DATABASE_URL,
                temporary_directory,
                application_name=APPLICATION_NAME,
                application_version=APPLICATION_VERSION,
                operational_fact_schema_version=1,
            )

    async def test_expected_creation_failure_is_stable_and_cleans_up(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "download-work"
            temporary_directory.mkdir()

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.create_verified_backup_package",
                    side_effect=RecoveryContractError(
                        "SNAPSHOT_CREATION_FAILED",
                        "Private path: /data/foreman.db",
                    ),
                ),
            ):
                response = await self.client.post(
                    "/api/recovery/backups"
                )

            self.assertEqual(response.status_code, 503)
            self.assertEqual(
                response.json(),
                {
                    "detail": {
                        "code": "BACKUP_CREATION_UNAVAILABLE",
                        "message": (
                            "A verified backup could not be created."
                        ),
                    }
                },
            )
            self.assertNotIn("/data/foreman.db", response.text)
            self.assertFalse(temporary_directory.exists())

    async def test_temporary_directory_failure_is_stable(self) -> None:
        with patch(
            "app.api.recovery.tempfile.mkdtemp",
            side_effect=OSError("Private filesystem detail"),
        ):
            response = await self.client.post(
                "/api/recovery/backups"
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "BACKUP_CREATION_UNAVAILABLE",
                "message": "A verified backup could not be created.",
            },
        )
        self.assertNotIn("Private filesystem detail", response.text)

    async def test_programmer_error_propagates_after_cleanup(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "download-work"
            temporary_directory.mkdir()

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.create_verified_backup_package",
                    side_effect=RuntimeError("programmer error"),
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "programmer error",
                ):
                    await self.client.post("/api/recovery/backups")

            self.assertFalse(temporary_directory.exists())
