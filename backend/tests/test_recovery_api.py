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
from app.core.maintenance import DatabaseMaintenanceConflict
from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.schemas.recovery import (
    BackupManifest,
    DatabaseBackupManifest,
    RestorePreflightSummary,
    VerificationIssue,
    VerificationResult,
)
from app.services.recovery import (
    RecoveryContractError,
    RestoreActivationError,
    RestoreActivationResult,
)
from test_support import ApiTestCase


BACKUP_FILENAME = "foreman-backup-20260731T220000Z.zip"
BACKUP_BYTES = b"verified-backup-package"
CURRENT_TABLES = [
    "inventory_items",
    "inventory_migrations",
    "members",
    "module_states",
    "organization_space_relationships",
    "organizations",
    "people",
    "project_material_requirements",
    "project_migrations",
    "projects",
    "spaces",
    "task_migrations",
    "tasks",
    "work_dependencies",
]
CURRENT_RECORD_COUNTS = {
    table_name: 1 if table_name == "projects" else 0
    for table_name in CURRENT_TABLES
}


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
            user_version=CURRENT_DATABASE_SCHEMA_VERSION,
            integrity_check="ok",
            foreign_key_violation_count=0,
            tables=CURRENT_TABLES,
        ),
        record_counts=CURRENT_RECORD_COUNTS,
    )


def valid_verification():
    return SimpleNamespace(
        manifest=verification_manifest(),
        result=VerificationResult(
            is_valid=True,
            issues=[],
        ),
    )


PREFLIGHT_TOKEN = "restore-preflight-token"
CONFIRMATION_PHRASE = "RESTORE THE FOREMAN"


def restore_preflight_summary() -> RestorePreflightSummary:
    manifest = verification_manifest()
    return RestorePreflightSummary(
        token=PREFLIGHT_TOKEN,
        expires_at=datetime(
            2026,
            8,
            1,
            22,
            15,
            tzinfo=timezone.utc,
        ),
        confirmation_phrase=CONFIRMATION_PHRASE,
        manifest=manifest,
        candidate_database=manifest.database,
        record_counts=manifest.record_counts,
        was_upgraded=False,
    )


def restore_preflight_session():
    summary = restore_preflight_summary()
    return SimpleNamespace(
        token=PREFLIGHT_TOKEN,
        staged_candidate=SimpleNamespace(
            path=Path("/private/preflight/foreman.db")
        ),
        summary=lambda: summary,
    )


def restore_activation_result() -> RestoreActivationResult:
    return RestoreActivationResult(
        database_path=Path("/private/live/foreman.db"),
        safety_backup_path=Path("/private/safety/backup.zip"),
        record_counts=(("projects", 1),),
        operational_fact_count=3,
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
    async def test_restore_preflight_returns_summary_and_cleans_upload(
        self,
    ) -> None:
        session = restore_preflight_session()

        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "preflight-upload"
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
                    "app.api.recovery.create_restore_preflight",
                    return_value=session,
                ) as create_preflight,
            ):
                response = await self.client.post(
                    "/api/recovery/restores/preflight",
                    content=BACKUP_BYTES,
                    headers={"Content-Type": "application/zip"},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["token"], PREFLIGHT_TOKEN)
            self.assertEqual(
                payload["confirmationPhrase"],
                CONFIRMATION_PHRASE,
            )
            self.assertEqual(
                payload["recordCounts"],
                CURRENT_RECORD_COUNTS,
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
            create_preflight.assert_called_once_with(
                uploaded_path,
                live_database_url=DATABASE_URL,
            )

    async def test_restore_preflight_rejects_invalid_package(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as parent:
            temporary_directory = Path(parent) / "preflight-upload"
            temporary_directory.mkdir()

            with (
                patch(
                    "app.api.recovery.tempfile.mkdtemp",
                    return_value=str(temporary_directory),
                ),
                patch(
                    "app.api.recovery.create_restore_preflight",
                    side_effect=RecoveryContractError(
                        "RESTORE_PREFLIGHT_PACKAGE_INVALID",
                        "Private archive detail",
                    ),
                ),
            ):
                response = await self.client.post(
                    "/api/recovery/restores/preflight",
                    content=BACKUP_BYTES,
                    headers={"Content-Type": "application/zip"},
                )

            self.assertEqual(response.status_code, 422)
            self.assertEqual(
                response.json()["detail"],
                {
                    "code": "RESTORE_PREFLIGHT_PACKAGE_INVALID",
                    "message": (
                        "The backup package is not eligible for restore."
                    ),
                },
            )
            self.assertNotIn("Private archive detail", response.text)
            self.assertFalse(temporary_directory.exists())

    async def test_restore_preflight_storage_failure_is_stable(
        self,
    ) -> None:
        with patch(
            "app.api.recovery.tempfile.mkdtemp",
            side_effect=OSError("Private storage path"),
        ):
            response = await self.client.post(
                "/api/recovery/restores/preflight",
                content=BACKUP_BYTES,
                headers={"Content-Type": "application/zip"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "RESTORE_PREFLIGHT_UNAVAILABLE",
                "message": (
                    "The restore preflight could not be prepared."
                ),
            },
        )
        self.assertNotIn("Private storage path", response.text)

    async def test_restore_activation_succeeds_without_paths(
        self,
    ) -> None:
        session = restore_preflight_session()
        result = restore_activation_result()

        with (
            patch(
                "app.api.recovery.consume_restore_preflight",
                return_value=session,
            ) as consume,
            patch(
                "app.api.recovery.activate_staged_restore",
                return_value=result,
            ) as activate,
            patch(
                "app.api.recovery.remove_restore_preflight"
            ) as remove,
        ):
            response = await self.client.post(
                "/api/recovery/restores/activate",
                json={
                    "token": PREFLIGHT_TOKEN,
                    "confirmationPhrase": CONFIRMATION_PHRASE,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "restored",
                "recordCounts": {"projects": 1},
                "operationalFactCount": 3,
                "safetyBackupRetained": True,
                "reloadRequired": True,
            },
        )
        self.assertEqual(
            response.headers["cache-control"],
            "no-store",
        )
        self.assertNotIn("/private", response.text)
        consume.assert_called_once_with(
            PREFLIGHT_TOKEN,
            CONFIRMATION_PHRASE,
            live_database_url=DATABASE_URL,
        )
        activate.assert_called_once_with(
            session.staged_candidate,
            live_database_url=DATABASE_URL,
            application_name=APPLICATION_NAME,
            application_version=APPLICATION_VERSION,
            operational_fact_schema_version=1,
            maintenance_timeout_seconds=30.0,
        )
        remove.assert_called_once_with(
            PREFLIGHT_TOKEN,
            live_database_url=DATABASE_URL,
        )

    async def test_restore_activation_requires_exact_confirmation(
        self,
    ) -> None:
        with (
            patch(
                "app.api.recovery.consume_restore_preflight",
                side_effect=RecoveryContractError(
                    "RESTORE_PREFLIGHT_CONFIRMATION_REQUIRED",
                    "Private confirmation detail",
                ),
            ),
            patch(
                "app.api.recovery.activate_staged_restore"
            ) as activate,
        ):
            response = await self.client.post(
                "/api/recovery/restores/activate",
                json={
                    "token": PREFLIGHT_TOKEN,
                    "confirmationPhrase": "restore the foreman",
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "RESTORE_PREFLIGHT_CONFIRMATION_REQUIRED",
        )
        self.assertNotIn("Private confirmation detail", response.text)
        activate.assert_not_called()

    async def test_restore_activation_rejects_consumed_token(
        self,
    ) -> None:
        with patch(
            "app.api.recovery.consume_restore_preflight",
            side_effect=RecoveryContractError(
                "RESTORE_PREFLIGHT_CONSUMED",
                "Private consumed marker path",
            ),
        ):
            response = await self.client.post(
                "/api/recovery/restores/activate",
                json={
                    "token": PREFLIGHT_TOKEN,
                    "confirmationPhrase": CONFIRMATION_PHRASE,
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "RESTORE_PREFLIGHT_CONSUMED",
        )
        self.assertNotIn("Private consumed marker path", response.text)

    async def test_restore_failure_reports_verified_rollback(
        self,
    ) -> None:
        session = restore_preflight_session()
        error = RestoreActivationError(
            "RESTORE_ACTIVATION_FAILED_ROLLED_BACK",
            "Private activation error",
            safety_backup_path=Path("/private/safety.zip"),
            rollback_succeeded=True,
            emergency_latched=False,
        )

        with (
            patch(
                "app.api.recovery.consume_restore_preflight",
                return_value=session,
            ),
            patch(
                "app.api.recovery.activate_staged_restore",
                side_effect=error,
            ),
            patch(
                "app.api.recovery.remove_restore_preflight"
            ) as remove,
        ):
            response = await self.client.post(
                "/api/recovery/restores/activate",
                json={
                    "token": PREFLIGHT_TOKEN,
                    "confirmationPhrase": CONFIRMATION_PHRASE,
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "RESTORE_ACTIVATION_FAILED_ROLLED_BACK",
                "message": (
                    "Restore activation failed, and the original "
                    "database was restored successfully."
                ),
                "rollbackSucceeded": True,
                "emergencyLatched": False,
            },
        )
        self.assertNotIn("/private", response.text)
        remove.assert_called_once()

    async def test_restore_double_failure_retains_emergency_workspace(
        self,
    ) -> None:
        session = restore_preflight_session()
        error = RestoreActivationError(
            "RESTORE_ACTIVATION_AND_ROLLBACK_FAILED",
            "Private rollback error",
            safety_backup_path=Path("/private/safety.zip"),
            rollback_succeeded=False,
            emergency_latched=True,
        )

        with (
            patch(
                "app.api.recovery.consume_restore_preflight",
                return_value=session,
            ),
            patch(
                "app.api.recovery.activate_staged_restore",
                side_effect=error,
            ),
            patch(
                "app.api.recovery.remove_restore_preflight"
            ) as remove,
        ):
            response = await self.client.post(
                "/api/recovery/restores/activate",
                json={
                    "token": PREFLIGHT_TOKEN,
                    "confirmationPhrase": CONFIRMATION_PHRASE,
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(
            response.json()["detail"]["rollbackSucceeded"]
        )
        self.assertTrue(
            response.json()["detail"]["emergencyLatched"]
        )
        self.assertNotIn("/private", response.text)
        remove.assert_not_called()

    async def test_restore_maintenance_conflict_consumes_and_cleans(
        self,
    ) -> None:
        session = restore_preflight_session()

        with (
            patch(
                "app.api.recovery.consume_restore_preflight",
                return_value=session,
            ),
            patch(
                "app.api.recovery.activate_staged_restore",
                side_effect=DatabaseMaintenanceConflict(
                    "Private coordinator detail"
                ),
            ),
            patch(
                "app.api.recovery.remove_restore_preflight"
            ) as remove,
        ):
            response = await self.client.post(
                "/api/recovery/restores/activate",
                json={
                    "token": PREFLIGHT_TOKEN,
                    "confirmationPhrase": CONFIRMATION_PHRASE,
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "RESTORE_MAINTENANCE_CONFLICT",
        )
        self.assertNotIn("Private coordinator detail", response.text)
        remove.assert_called_once()
