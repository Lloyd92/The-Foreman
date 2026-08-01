import sqlite3
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.schema_upgrades import apply_schema_upgrades
from app.models.base import Base
from app.services.recovery import (
    RecoveryContractError,
    create_verified_backup_package,
    sha256_file,
)
from app.services.restore_preflight import (
    PREFLIGHT_TTL,
    RESTORE_CONFIRMATION_PHRASE,
    cleanup_expired_restore_preflights,
    consume_restore_preflight,
    create_restore_preflight,
    load_restore_preflight,
)


NOW = datetime(2026, 8, 1, 22, 0, tzinfo=timezone.utc)
PACKAGE_TIME = datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc)


class RestorePreflightServiceTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.live_path = self.root / "foreman.db"
        self.source_path = self.root / "source.db"
        self.package_directory = self.root / "packages"
        self.package_directory.mkdir()
        self._create_database(
            self.live_path,
            project_id="live-project",
            project_name="Live Project",
        )
        self._create_database(
            self.source_path,
            project_id="restore-project",
            project_name="Restore Project",
        )
        self.package = create_verified_backup_package(
            self.source_database_url,
            self.package_directory,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            created_at=PACKAGE_TIME,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @property
    def live_database_url(self) -> str:
        return f"sqlite:///{self.live_path}"

    @property
    def source_database_url(self) -> str:
        return f"sqlite:///{self.source_path}"

    def _create_database(
        self,
        path: Path,
        *,
        project_id: str,
        project_name: str,
    ) -> None:
        engine = create_engine(f"sqlite:///{path}")

        try:
            with engine.begin() as connection:
                Base.metadata.create_all(bind=connection)
                apply_schema_upgrades(connection)
                connection.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, name, type, status, priority, progress,
                            start_date, target_date, estimated_cost,
                            description, notes, created_at, updated_at,
                            archived_at
                        ) VALUES (
                            :id, :name, 'other', 'active', 'medium', 0,
                            NULL, NULL, 0, '', '', :created_at,
                            :updated_at, NULL
                        )
                        """
                    ),
                    {
                        "id": project_id,
                        "name": project_name,
                        "created_at": "2026-08-01 18:00:00",
                        "updated_at": "2026-08-01 18:00:00",
                    },
                )
        finally:
            engine.dispose()

    def _create_preflight(
        self,
        *,
        token: str = "test-preflight-token",
        now: datetime = NOW,
    ):
        return create_restore_preflight(
            self.package.path,
            live_database_url=self.live_database_url,
            now=now,
            token_factory=lambda _: token,
        )

    def test_preflight_is_private_durable_and_restart_loadable(
        self,
    ) -> None:
        package_checksum = sha256_file(self.package.path)
        session = self._create_preflight()
        summary = session.summary()

        self.assertEqual(session.expires_at, NOW + PREFLIGHT_TTL)
        self.assertEqual(
            summary.confirmation_phrase,
            RESTORE_CONFIRMATION_PHRASE,
        )
        self.assertEqual(
            summary.manifest,
            self.package.manifest,
        )
        self.assertEqual(
            stat.S_IMODE(session.workspace_path.stat().st_mode),
            0o700,
        )
        self.assertEqual(
            stat.S_IMODE(session.package_path.stat().st_mode),
            0o600,
        )
        self.assertEqual(
            stat.S_IMODE(
                session.staged_candidate.path.stat().st_mode
            ),
            0o600,
        )
        self.assertEqual(
            sha256_file(self.package.path),
            package_checksum,
        )
        metadata = (
            session.workspace_path / "preflight.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn(session.token, metadata)

        loaded = load_restore_preflight(
            session.token,
            live_database_url=self.live_database_url,
            now=NOW + timedelta(minutes=1),
        )
        self.assertEqual(
            loaded.staged_candidate.database_manifest,
            session.staged_candidate.database_manifest,
        )

    def test_confirmation_is_exact_and_consumed_once(self) -> None:
        session = self._create_preflight()

        with self.assertRaises(RecoveryContractError) as context:
            consume_restore_preflight(
                session.token,
                "restore the foreman",
                live_database_url=self.live_database_url,
                now=NOW,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_PREFLIGHT_CONFIRMATION_REQUIRED",
        )
        consumed = consume_restore_preflight(
            session.token,
            RESTORE_CONFIRMATION_PHRASE,
            live_database_url=self.live_database_url,
            now=NOW,
        )
        self.assertEqual(consumed.token, session.token)

        with self.assertRaises(RecoveryContractError) as context:
            consume_restore_preflight(
                session.token,
                RESTORE_CONFIRMATION_PHRASE,
                live_database_url=self.live_database_url,
                now=NOW,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_PREFLIGHT_CONSUMED",
        )

    def test_expired_preflight_is_removed(self) -> None:
        session = self._create_preflight()

        with self.assertRaises(RecoveryContractError) as context:
            load_restore_preflight(
                session.token,
                live_database_url=self.live_database_url,
                now=NOW + PREFLIGHT_TTL,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_PREFLIGHT_EXPIRED",
        )
        self.assertFalse(session.workspace_path.exists())

    def test_candidate_tampering_blocks_consumption(self) -> None:
        session = self._create_preflight()

        with session.staged_candidate.path.open("ab") as file:
            file.write(b"tampered")

        with self.assertRaises(RecoveryContractError) as context:
            consume_restore_preflight(
                session.token,
                RESTORE_CONFIRMATION_PHRASE,
                live_database_url=self.live_database_url,
                now=NOW,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_ACTIVATION_CANDIDATE_CHANGED",
        )
        self.assertFalse(
            (
                session.workspace_path / "consumed"
            ).exists()
        )

    def test_invalid_package_cleans_preflight_workspace(self) -> None:
        invalid = self.root / "invalid.zip"
        invalid.write_bytes(b"not a backup")

        with self.assertRaises(RecoveryContractError) as context:
            create_restore_preflight(
                invalid,
                live_database_url=self.live_database_url,
                now=NOW,
                token_factory=lambda _: "invalid-package-token",
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_PREFLIGHT_PACKAGE_INVALID",
        )
        preflight_root = self.root / "recovery" / "preflight"
        self.assertEqual(list(preflight_root.iterdir()), [])

    def test_cleanup_removes_only_expired_sessions(self) -> None:
        current = self._create_preflight(
            token="current-token",
            now=NOW,
        )
        expired = self._create_preflight(
            token="expired-token",
            now=NOW - timedelta(hours=1),
        )
        unknown = (
            self.root
            / "recovery"
            / "preflight"
            / ("f" * 64)
        )
        unknown.mkdir(mode=0o700)

        removed = cleanup_expired_restore_preflights(
            self.live_database_url,
            now=NOW,
        )

        self.assertEqual(removed, 1)
        self.assertFalse(expired.workspace_path.exists())
        self.assertTrue(current.workspace_path.exists())
        self.assertTrue(unknown.exists())
