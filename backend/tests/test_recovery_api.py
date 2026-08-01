import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    DATABASE_URL,
)
from app.schemas.recovery import (
    BackupManifest,
    DatabaseBackupManifest,
    VerificationIssue,
    VerificationResult,
)
from app.services.recovery import RecoveryContractError
from test_support import ApiTestCase


BACKUP_FILENAME = "foreman-backup-20260731T220000Z.zip"
BACKUP_BYTES = b"verified-backup-package"


def verification_manifest() -> BackupManifest:
    return BackupManifest(
        backup_format_version=1,
        application_name="The Foreman",
        application_version="0.7.3",
        created_at=datetime(
            2026,
            7,
            31,
            22,
            0,
            tzinfo=timezone.utc,
        ),
        operational_fact_schema_version=1,
        database=DatabaseBackupManifest(
            filename="foreman.db",
            byte_size=4096,
            sha256="a" * 64,
            user_version=2,
            integrity_check="ok",
            foreign_key_violation_count=0,
            tables=["projects"],
        ),
        record_counts={"projects": 1},
    )


def valid_verification():
    return SimpleNamespace(
        manifest=verification_manifest(),
        result=VerificationResult(
            is_valid=True,
            issues=[],
        ),
    )


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

    async def test_verification_upload_returns_manifest_and_cleans_up(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "upload-work"
            temporary_directory.mkdir()
            uploaded_path = (
                temporary_directory / "uploaded-backup.zip"
            )

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.verify_backup_package",
                    return_value=valid_verification(),
                ) as verify_backup,
            ):
                response = await self.client.post(
                    "/api/recovery/backups/verify",
                    content=b"backup-package",
                    headers={"Content-Type": "application/zip"},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["verification"]["isValid"])
            self.assertEqual(
                payload["manifest"]["backupFormatVersion"],
                1,
            )
            self.assertEqual(
                response.headers["cache-control"],
                "no-store",
            )
            self.assertFalse(temporary_directory.exists())
            verify_backup.assert_called_once_with(uploaded_path)

    async def test_invalid_package_returns_structured_report(
        self,
    ) -> None:
        invalid_verification = SimpleNamespace(
            manifest=None,
            result=VerificationResult(
                is_valid=False,
                issues=[
                    VerificationIssue(
                        code="BACKUP_ARCHIVE_INVALID",
                        message=(
                            "Backup package is not a readable ZIP archive."
                        ),
                    )
                ],
            ),
        )

        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "upload-work"
            temporary_directory.mkdir()

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.verify_backup_package",
                    return_value=invalid_verification,
                ),
            ):
                response = await self.client.post(
                    "/api/recovery/backups/verify",
                    content=b"not-a-zip",
                    headers={"Content-Type": "application/zip"},
                )

            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.json()["manifest"])
            self.assertFalse(
                response.json()["verification"]["isValid"]
            )
            self.assertEqual(
                response.json()["verification"]["issues"][0]["code"],
                "BACKUP_ARCHIVE_INVALID",
            )
            self.assertFalse(temporary_directory.exists())

    async def test_verification_rejects_unsupported_media_type(
        self,
    ) -> None:
        with patch(
            "app.api.recovery.verify_backup_package"
        ) as verify_backup:
            response = await self.client.post(
                "/api/recovery/backups/verify",
                content=b"backup-package",
                headers={"Content-Type": "application/octet-stream"},
            )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(
            response.json()["detail"]["code"],
            "BACKUP_UPLOAD_MEDIA_TYPE_UNSUPPORTED",
        )
        verify_backup.assert_not_called()

    async def test_verification_rejects_declared_oversize(
        self,
    ) -> None:
        with (
            patch(
                "app.api.recovery.MAX_BACKUP_PACKAGE_BYTES",
                0,
            ),
            patch(
                "app.api.recovery.tempfile.mkdtemp"
            ) as create_directory,
        ):
            response = await self.client.post(
                "/api/recovery/backups/verify",
                content=b"x",
                headers={"Content-Type": "application/zip"},
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json()["detail"]["code"],
            "BACKUP_UPLOAD_TOO_LARGE",
        )
        create_directory.assert_not_called()

    async def test_verification_rejects_streamed_oversize_and_cleans_up(
        self,
    ) -> None:
        async def upload_chunks():
            yield b"123"
            yield b"45"

        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "upload-work"
            temporary_directory.mkdir()

            with (
                patch(
                    "app.api.recovery.MAX_BACKUP_PACKAGE_BYTES",
                    4,
                ),
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
            ):
                response = await self.client.post(
                    "/api/recovery/backups/verify",
                    content=upload_chunks(),
                    headers={"Content-Type": "application/zip"},
                )

            self.assertEqual(response.status_code, 413)
            self.assertEqual(
                response.json()["detail"]["code"],
                "BACKUP_UPLOAD_TOO_LARGE",
            )
            self.assertFalse(temporary_directory.exists())

    async def test_verification_rejects_empty_upload(self) -> None:
        response = await self.client.post(
            "/api/recovery/backups/verify",
            content=b"",
            headers={"Content-Type": "application/zip"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "BACKUP_UPLOAD_EMPTY",
        )

    async def test_verification_storage_failure_is_non_sensitive(
        self,
    ) -> None:
        with patch(
            "app.api.recovery.tempfile.mkdtemp",
            side_effect=OSError("Private storage path"),
        ):
            response = await self.client.post(
                "/api/recovery/backups/verify",
                content=b"backup-package",
                headers={"Content-Type": "application/zip"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "BACKUP_VERIFICATION_UNAVAILABLE",
                "message": "The backup could not be verified.",
            },
        )
        self.assertNotIn("Private storage path", response.text)

    async def test_verification_programmer_error_cleans_up(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "upload-work"
            temporary_directory.mkdir()

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.verify_backup_package",
                    side_effect=RuntimeError("programmer error"),
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "programmer error",
                ):
                    await self.client.post(
                        "/api/recovery/backups/verify",
                        content=b"backup-package",
                        headers={"Content-Type": "application/zip"},
                    )

            self.assertFalse(temporary_directory.exists())
