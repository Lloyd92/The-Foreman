import copy
import json
import sqlite3
import stat
import tempfile
import unittest
import warnings
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.core.database import prepare_database_schema
from app.core.default_space import (
    DEFAULT_SPACE_DESCRIPTION,
    DEFAULT_SPACE_ID,
    DEFAULT_SPACE_NAME,
)
from app.core.maintenance import (
    DatabaseMaintenanceActive,
    maintenance_coordinator,
)
from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.models.base import Base
import app.services.recovery as recovery_service
from app.schemas.recovery import (
    BackupCompatibility,
    BackupManifest,
    DatabaseBackupManifest,
    VerificationIssue,
    VerificationResult,
)
from app.services.recovery import (
    BackupPackageVerification,
    RestoreActivationError,
    RestoreActivationResult,
    StagedRestoreCandidate,
    _verify_activated_database,
    activate_staged_restore,
    EXPECTED_BACKUP_MEMBERS,
    RecoveryContractError,
    backup_package_filename,
    build_verification_result,
    canonical_json_bytes,
    classify_database_compatibility,
    create_pre_restore_safety_backup,
    create_verified_backup_package,
    create_verified_sqlite_snapshot,
    normalize_table_counts,
    parse_backup_manifest,
    resolve_sqlite_database_path,
    sha256_file,
    sha256_hex,
    sort_verification_issues,
    stage_restore_candidate,
    validate_archive_member_names,
    verify_backup_package,
)
from tests.test_support import (
    PRE_V4_TABLE_NAMES,
    create_pre_v4_tables,
)


CREATED_AT = datetime(2026, 7, 31, 16, 0, tzinfo=timezone.utc)
FOUNDATION_TABLE_SCHEMA = """
CREATE TABLE spaces (id TEXT PRIMARY KEY);
CREATE TABLE people (id TEXT PRIMARY KEY);
CREATE TABLE organizations (id TEXT PRIMARY KEY);
CREATE TABLE organization_space_relationships (id TEXT PRIMARY KEY);
CREATE TABLE members (id TEXT PRIMARY KEY);
CREATE TABLE module_states (module_id TEXT PRIMARY KEY);
"""
TABLES = [
    "inventory_items",
    "projects",
    "tasks",
]
COUNTS = {
    "inventory_items": 2,
    "projects": 1,
    "tasks": 3,
}
DIGEST = "a" * 64


def database_manifest(
    **overrides,
) -> DatabaseBackupManifest:
    values = {
        "filename": "foreman.db",
        "byte_size": 4096,
        "sha256": DIGEST,
        "user_version": 2,
        "integrity_check": "ok",
        "foreign_key_violation_count": 0,
        "tables": TABLES.copy(),
    }
    values.update(overrides)
    return DatabaseBackupManifest(**values)


def backup_manifest(**overrides) -> BackupManifest:
    values = {
        "backup_format_version": 1,
        "application_name": "The Foreman",
        "application_version": "0.7.4",
        "created_at": CREATED_AT,
        "operational_fact_schema_version": 1,
        "database": database_manifest(),
        "record_counts": COUNTS.copy(),
    }
    values.update(overrides)
    return BackupManifest(**values)


class RecoverySchemaTests(unittest.TestCase):
    def test_manifest_serializes_with_camel_case(self) -> None:
        serialized = backup_manifest().model_dump(
            mode="json",
            by_alias=True,
        )

        self.assertEqual(serialized["backupFormatVersion"], 1)
        self.assertEqual(serialized["applicationName"], "The Foreman")
        self.assertEqual(
            serialized["operationalFactSchemaVersion"],
            1,
        )
        self.assertEqual(serialized["database"]["byteSize"], 4096)
        self.assertEqual(
            serialized["database"]["foreignKeyViolationCount"],
            0,
        )
        self.assertEqual(serialized["recordCounts"], COUNTS)

    def test_manifest_forbids_unknown_fields(self) -> None:
        with self.assertRaises(ValidationError):
            BackupManifest(
                **backup_manifest().model_dump(),
                unexpected="value",
            )

    def test_manifest_rejects_non_utc_timestamp(self) -> None:
        non_utc = datetime(
            2026,
            7,
            31,
            12,
            0,
            tzinfo=timezone(timedelta(hours=-4)),
        )

        with self.assertRaises(ValidationError):
            backup_manifest(created_at=non_utc)

    def test_manifest_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(ValidationError):
            backup_manifest(
                created_at=datetime(2026, 7, 31, 16, 0)
            )

    def test_database_manifest_rejects_bad_checksum(self) -> None:
        with self.assertRaises(ValidationError):
            database_manifest(sha256="ABC123")

    def test_database_manifest_rejects_unsorted_tables(self) -> None:
        with self.assertRaises(ValidationError):
            database_manifest(
                tables=["tasks", "projects", "inventory_items"]
            )

    def test_database_manifest_rejects_duplicate_tables(self) -> None:
        with self.assertRaises(ValidationError):
            database_manifest(
                tables=[
                    "inventory_items",
                    "projects",
                    "PROJECTS",
                ]
            )

    def test_manifest_rejects_unsorted_record_counts(self) -> None:
        with self.assertRaises(ValidationError):
            backup_manifest(
                record_counts={
                    "tasks": 3,
                    "projects": 1,
                    "inventory_items": 2,
                }
            )

    def test_manifest_rejects_mismatched_record_counts(self) -> None:
        with self.assertRaises(ValidationError):
            backup_manifest(
                record_counts={
                    "inventory_items": 2,
                    "projects": 1,
                }
            )

    def test_manifest_rejects_negative_record_count(self) -> None:
        with self.assertRaises(ValidationError):
            backup_manifest(
                record_counts={
                    "inventory_items": 2,
                    "projects": -1,
                    "tasks": 3,
                }
            )

    def test_verification_result_requires_consistent_validity(self) -> None:
        issue = VerificationIssue(
            code="CHECKSUM_MISMATCH",
            message="Checksum does not match.",
        )

        with self.assertRaises(ValidationError):
            VerificationResult(is_valid=True, issues=[issue])


class RecoveryServiceTests(unittest.TestCase):
    def test_canonical_json_is_stable_and_compact(self) -> None:
        first = canonical_json_bytes({"b": 2, "a": 1})
        second = canonical_json_bytes({"a": 1, "b": 2})

        self.assertEqual(first, b'{"a":1,"b":2}')
        self.assertEqual(first, second)

    def test_canonical_json_serializes_models_by_alias(self) -> None:
        serialized = canonical_json_bytes(backup_manifest())
        parsed = json.loads(serialized)

        self.assertIn("backupFormatVersion", parsed)
        self.assertIn("recordCounts", parsed)
        self.assertNotIn("backup_format_version", parsed)

    def test_canonical_json_rejects_nonfinite_number(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            canonical_json_bytes({"value": float("nan")})

        self.assertEqual(context.exception.code, "CANONICAL_JSON_INVALID")

    def test_sha256_is_deterministic(self) -> None:
        self.assertEqual(
            sha256_hex(b"The Foreman"),
            sha256_hex(memoryview(b"The Foreman")),
        )
        self.assertEqual(len(sha256_hex(b"The Foreman")), 64)

    def test_archive_members_accept_exact_set_in_any_order(self) -> None:
        result = validate_archive_member_names(
            ["foreman.db", "manifest.json"]
        )

        self.assertEqual(result, EXPECTED_BACKUP_MEMBERS)

    def test_archive_members_reject_missing_member(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            validate_archive_member_names(["manifest.json"])

        self.assertEqual(
            context.exception.code,
            "ARCHIVE_MEMBER_SET_INVALID",
        )

    def test_archive_members_reject_extra_member(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            validate_archive_member_names(
                ["manifest.json", "foreman.db", "extra.txt"]
            )

        self.assertEqual(
            context.exception.code,
            "ARCHIVE_MEMBER_SET_INVALID",
        )

    def test_archive_members_reject_duplicate_member(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            validate_archive_member_names(
                ["manifest.json", "foreman.db", "foreman.db"]
            )

        self.assertEqual(
            context.exception.code,
            "ARCHIVE_MEMBER_DUPLICATE",
        )

    def test_archive_members_reject_unsafe_names(self) -> None:
        unsafe_names = (
            "../manifest.json",
            "/manifest.json",
            r"..\manifest.json",
            "nested/manifest.json",
            "C:manifest.json",
        )

        for name in unsafe_names:
            with self.subTest(name=name):
                with self.assertRaises(RecoveryContractError) as context:
                    validate_archive_member_names(
                        [name, "foreman.db"]
                    )
                self.assertEqual(
                    context.exception.code,
                    "ARCHIVE_MEMBER_NAME_INVALID",
                )

    def test_normalize_table_counts_is_canonical(self) -> None:
        source = {
            "tasks": 3,
            "inventory_items": 2,
            "projects": 1,
        }
        original = copy.deepcopy(source)

        tables, counts = normalize_table_counts(source)

        self.assertEqual(tables, TABLES)
        self.assertEqual(counts, COUNTS)
        self.assertEqual(source, original)

    def test_normalize_table_counts_rejects_invalid_count(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            normalize_table_counts({"projects": True})

        self.assertEqual(context.exception.code, "RECORD_COUNT_INVALID")

    def test_parse_manifest_round_trip(self) -> None:
        source = canonical_json_bytes(backup_manifest())
        parsed = parse_backup_manifest(source)

        self.assertEqual(parsed, backup_manifest())

    def test_parse_manifest_rejects_duplicate_json_keys(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            parse_backup_manifest(
                '{"backupFormatVersion":1,'
                '"backupFormatVersion":1}'
            )

        self.assertEqual(
            context.exception.code,
            "MANIFEST_DUPLICATE_KEY",
        )

    def test_parse_manifest_rejects_nonstandard_number(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            parse_backup_manifest('{"value":NaN}')

        self.assertEqual(
            context.exception.code,
            "MANIFEST_JSON_INVALID",
        )

    def test_parse_manifest_rejects_schema_mismatch(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            parse_backup_manifest('{"backupFormatVersion":1}')

        self.assertEqual(
            context.exception.code,
            "MANIFEST_SCHEMA_INVALID",
        )

    def test_database_compatibility_states(self) -> None:
        compatible = classify_database_compatibility(2, 2)
        upgrade = classify_database_compatibility(1, 2)
        future = classify_database_compatibility(3, 2)
        invalid = classify_database_compatibility(-1, 2)

        self.assertEqual(compatible.status, "compatible")
        self.assertTrue(compatible.is_supported)
        self.assertFalse(compatible.requires_upgrade)

        self.assertEqual(upgrade.status, "upgrade-required")
        self.assertTrue(upgrade.is_supported)
        self.assertTrue(upgrade.requires_upgrade)

        self.assertEqual(future.status, "unsupported-future")
        self.assertFalse(future.is_supported)

        self.assertEqual(invalid.status, "unsupported-invalid")
        self.assertFalse(invalid.is_supported)

    def test_issue_order_is_stable_without_input_mutation(self) -> None:
        issues = [
            VerificationIssue(
                severity="warning",
                code="UPGRADE_REQUIRED",
                message="Upgrade required.",
            ),
            VerificationIssue(
                code="CHECKSUM_MISMATCH",
                message="Checksum mismatch.",
                location="foreman.db",
            ),
            VerificationIssue(
                code="ARCHIVE_INVALID",
                message="Archive invalid.",
            ),
        ]
        original = issues.copy()

        ordered = sort_verification_issues(issues)

        self.assertEqual(
            [issue.code for issue in ordered],
            [
                "ARCHIVE_INVALID",
                "CHECKSUM_MISMATCH",
                "UPGRADE_REQUIRED",
            ],
        )
        self.assertEqual(issues, original)

    def test_build_verification_result_derives_validity(self) -> None:
        compatibility = BackupCompatibility(
            status="upgrade-required",
            source_user_version=1,
            current_user_version=2,
            is_supported=True,
            requires_upgrade=True,
        )
        warning = VerificationIssue(
            severity="warning",
            code="UPGRADE_REQUIRED",
            message="Upgrade required.",
        )
        valid = build_verification_result(
            [warning],
            compatibility=compatibility,
        )
        invalid = build_verification_result(
            [
                VerificationIssue(
                    code="CHECKSUM_MISMATCH",
                    message="Checksum mismatch.",
                )
            ]
        )

        self.assertTrue(valid.is_valid)
        self.assertEqual(valid.compatibility, compatibility)
        self.assertFalse(invalid.is_valid)


class SqliteSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_path = self.root / "source.db"
        self.destination_directory = self.root / "snapshot"
        self.destination_directory.mkdir()
        self.destination_path = (
            self.destination_directory / "foreman.db"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_source_database(
        self,
        *,
        foreign_key_violation: bool = False,
    ) -> None:
        connection = sqlite3.connect(self.source_path)

        try:
            connection.executescript(
                """
                PRAGMA foreign_keys = OFF;
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
                CREATE TABLE inventory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                ("project-1", "Backup Project"),
            )
            connection.execute(
                "INSERT INTO tasks (id, project_id, title) "
                "VALUES (?, ?, ?)",
                (
                    "task-1",
                    "missing-project"
                    if foreign_key_violation
                    else "project-1",
                    "Backup Task",
                ),
            )
            connection.executemany(
                "INSERT INTO inventory_items (name) VALUES (?)",
                [("Fastener",), ("Board",)],
            )
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
        finally:
            connection.close()

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.source_path}"

    def test_create_verified_snapshot_preserves_database(self) -> None:
        self.create_source_database()
        source_before = sha256_file(self.source_path)

        result = create_verified_sqlite_snapshot(
            self.database_url,
            self.destination_path,
        )
        manifest = result.database_manifest

        self.assertTrue(self.destination_path.is_file())
        self.assertEqual(result.path, self.destination_path.resolve())
        self.assertEqual(manifest.filename, "foreman.db")
        self.assertEqual(
            manifest.byte_size,
            self.destination_path.stat().st_size,
        )
        self.assertEqual(
            manifest.sha256,
            sha256_file(self.destination_path),
        )
        self.assertEqual(manifest.user_version, 2)
        self.assertEqual(manifest.integrity_check, "ok")
        self.assertEqual(manifest.foreign_key_violation_count, 0)
        self.assertEqual(
            manifest.tables,
            ["inventory_items", "projects", "tasks"],
        )
        self.assertEqual(
            result.record_count_mapping(),
            {
                "inventory_items": 2,
                "projects": 1,
                "tasks": 1,
            },
        )
        self.assertEqual(sha256_file(self.source_path), source_before)

        snapshot = sqlite3.connect(
            f"{self.destination_path.as_uri()}?mode=ro",
            uri=True,
        )

        try:
            counts = {
                table: snapshot.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                for table in result.database_manifest.tables
            }
            project_name = snapshot.execute(
                "SELECT name FROM projects WHERE id = ?",
                ("project-1",),
            ).fetchone()[0]
        finally:
            snapshot.close()

        self.assertEqual(
            counts,
            {
                "inventory_items": 2,
                "projects": 1,
                "tasks": 1,
            },
        )
        self.assertEqual(project_name, "Backup Project")

    def test_snapshot_excludes_sqlite_system_tables(self) -> None:
        self.create_source_database()

        result = create_verified_sqlite_snapshot(
            self.database_url,
            self.destination_path,
        )

        self.assertNotIn(
            "sqlite_sequence",
            result.database_manifest.tables,
        )

    def test_snapshot_includes_committed_wal_state(self) -> None:
        connection = sqlite3.connect(self.source_path)

        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA wal_autocheckpoint = 0")
            connection.execute(
                "CREATE TABLE projects "
                "(id TEXT PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                ("wal-project", "Committed WAL Project"),
            )
            connection.execute("PRAGMA user_version = 2")
            connection.commit()

            result = create_verified_sqlite_snapshot(
                self.database_url,
                self.destination_path,
            )
        finally:
            connection.close()

        snapshot = sqlite3.connect(
            f"{self.destination_path.as_uri()}?mode=ro",
            uri=True,
        )

        try:
            row = snapshot.execute(
                "SELECT name FROM projects WHERE id = ?",
                ("wal-project",),
            ).fetchone()
        finally:
            snapshot.close()

        self.assertEqual(row, ("Committed WAL Project",))
        self.assertEqual(
            result.record_count_mapping(),
            {"projects": 1},
        )

    def test_resolve_sqlite_path_returns_absolute_source(self) -> None:
        self.create_source_database()

        resolved = resolve_sqlite_database_path(self.database_url)

        self.assertEqual(resolved, self.source_path.resolve())

    def test_snapshot_rejects_non_sqlite_database(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                "postgresql://localhost/foreman",
                self.destination_path,
            )

        self.assertEqual(
            context.exception.code,
            "DATABASE_BACKEND_UNSUPPORTED",
        )
        self.assertFalse(self.destination_path.exists())

    def test_snapshot_rejects_memory_database(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                "sqlite:///:memory:",
                self.destination_path,
            )

        self.assertEqual(
            context.exception.code,
            "DATABASE_SOURCE_UNSUPPORTED",
        )

    def test_snapshot_rejects_relative_source_path(self) -> None:
        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                "sqlite:///relative.db",
                self.destination_path,
            )

        self.assertEqual(
            context.exception.code,
            "DATABASE_SOURCE_PATH_INVALID",
        )

    def test_snapshot_rejects_missing_source(self) -> None:
        missing = self.root / "missing.db"

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                f"sqlite:///{missing}",
                self.destination_path,
            )

        self.assertEqual(
            context.exception.code,
            "DATABASE_SOURCE_MISSING",
        )

    def test_snapshot_rejects_existing_destination_without_change(
        self,
    ) -> None:
        self.create_source_database()
        self.destination_path.write_bytes(b"preserve me")

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                self.database_url,
                self.destination_path,
            )

        self.assertEqual(
            context.exception.code,
            "SNAPSHOT_DESTINATION_EXISTS",
        )
        self.assertEqual(
            self.destination_path.read_bytes(),
            b"preserve me",
        )

    def test_snapshot_rejects_source_as_destination(self) -> None:
        self.create_source_database()
        source_before = self.source_path.read_bytes()

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                self.database_url,
                self.source_path,
            )

        self.assertEqual(
            context.exception.code,
            "SNAPSHOT_SOURCE_DESTINATION_CONFLICT",
        )
        self.assertEqual(self.source_path.read_bytes(), source_before)

    def test_snapshot_rejects_relative_destination(self) -> None:
        self.create_source_database()

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                self.database_url,
                Path("foreman.db"),
            )

        self.assertEqual(
            context.exception.code,
            "SNAPSHOT_DESTINATION_INVALID",
        )

    def test_snapshot_rejects_foreign_key_violations_and_cleans_up(
        self,
    ) -> None:
        self.create_source_database(foreign_key_violation=True)

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_sqlite_snapshot(
                self.database_url,
                self.destination_path,
            )

        self.assertEqual(
            context.exception.code,
            "SNAPSHOT_FOREIGN_KEY_VIOLATIONS",
        )
        self.assertFalse(self.destination_path.exists())

    def test_snapshot_cleans_up_failed_copy(self) -> None:
        self.create_source_database()

        with patch(
            "app.services.recovery._copy_sqlite_database",
            side_effect=sqlite3.DatabaseError("copy failed"),
        ):
            with self.assertRaises(RecoveryContractError) as context:
                create_verified_sqlite_snapshot(
                    self.database_url,
                    self.destination_path,
                )

        self.assertEqual(
            context.exception.code,
            "SNAPSHOT_CREATION_FAILED",
        )
        self.assertFalse(self.destination_path.exists())


CURRENT_CALENDAR_TABLE_SCHEMA = """
CREATE TABLE calendar_entries (
    id TEXT PRIMARY KEY
);
CREATE TABLE calendar_series (
    id TEXT PRIMARY KEY
);
CREATE TABLE calendar_series_exclusions (
    id TEXT PRIMARY KEY
);
CREATE TABLE calendar_settings (
    space_id TEXT PRIMARY KEY
);
CREATE TABLE work_calendar_relationships (
    id TEXT PRIMARY KEY
);
"""


class BackupPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_path = self.root / "source.db"
        self.destination_directory = self.root / "backups"
        self.destination_directory.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.source_path}"

    @property
    def package_path(self) -> Path:
        return self.destination_directory / (
            "foreman-backup-20260731T160000Z.zip"
        )

    def create_source_database(
        self,
        *,
        user_version: int = CURRENT_DATABASE_SCHEMA_VERSION,
    ) -> None:
        connection = sqlite3.connect(self.source_path)

        try:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
                CREATE TABLE inventory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                );
                CREATE TABLE inventory_migrations (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE project_material_requirements (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE project_migrations (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE task_migrations (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE work_dependencies (
                    id TEXT PRIMARY KEY
                );
                """
            )
            connection.executescript(FOUNDATION_TABLE_SCHEMA)
            connection.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                ("project-1", "Backup Project"),
            )
            connection.execute(
                "INSERT INTO tasks (id, project_id, title) "
                "VALUES (?, ?, ?)",
                ("task-1", "project-1", "Backup Task"),
            )
            connection.executemany(
                "INSERT INTO inventory_items (name) VALUES (?)",
                [("Fastener",), ("Board",)],
            )
            if user_version == CURRENT_DATABASE_SCHEMA_VERSION:
                connection.executescript(
                    """
                    CREATE TABLE tools (
                        id TEXT PRIMARY KEY
                    );
                    CREATE TABLE care_plans (
                        id TEXT PRIMARY KEY
                    );
                    CREATE TABLE tool_maintenance_records (
                        id TEXT PRIMARY KEY
                    );
                    CREATE TABLE work_tool_requirements (
                        id TEXT PRIMARY KEY
                    );
                    """
                )
            if user_version >= CURRENT_DATABASE_SCHEMA_VERSION:
                connection.executescript(
                    CURRENT_CALENDAR_TABLE_SCHEMA
                )

            connection.execute(
                f"PRAGMA user_version = {user_version}"
            )
            connection.commit()
        finally:
            connection.close()

    def create_package(
        self,
        *,
        user_version: int = CURRENT_DATABASE_SCHEMA_VERSION,
    ):
        self.create_source_database(user_version=user_version)
        return create_verified_backup_package(
            self.database_url,
            self.destination_directory,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            created_at=CREATED_AT,
        )

    def read_package_members(self) -> dict[str, bytes]:
        with zipfile.ZipFile(self.package_path, "r") as archive:
            return {
                member.filename: archive.read(member)
                for member in archive.infolist()
            }

    def rewrite_package(
        self,
        *,
        manifest_bytes: bytes | None = None,
        database_bytes: bytes | None = None,
        extra_members: dict[str, bytes] | None = None,
    ) -> None:
        members = self.read_package_members()
        self.package_path.unlink()

        with zipfile.ZipFile(
            self.package_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "manifest.json",
                manifest_bytes
                if manifest_bytes is not None
                else members["manifest.json"],
            )
            archive.writestr(
                "foreman.db",
                database_bytes
                if database_bytes is not None
                else members["foreman.db"],
            )

            for name, value in (extra_members or {}).items():
                archive.writestr(name, value)

    def modified_manifest_bytes(self, update) -> bytes:
        members = self.read_package_members()
        manifest = json.loads(members["manifest.json"])
        update(manifest)
        return canonical_json_bytes(manifest)

    def issue_codes(self, verification) -> list[str]:
        return [
            issue.code
            for issue in verification.result.issues
        ]

    def test_backup_filename_uses_exact_utc_timestamp(self) -> None:
        self.assertEqual(
            backup_package_filename(CREATED_AT),
            "foreman-backup-20260731T160000Z.zip",
        )

        with self.assertRaises(RecoveryContractError):
            backup_package_filename(
                CREATED_AT.replace(microsecond=1)
            )

        with self.assertRaises(RecoveryContractError):
            backup_package_filename(
                CREATED_AT.astimezone(
                    timezone(timedelta(hours=-4))
                )
            )

    def test_create_package_is_exact_and_independently_verified(
        self,
    ) -> None:
        source_before = None
        self.create_source_database()
        source_before = sha256_file(self.source_path)

        result = create_verified_backup_package(
            self.database_url,
            self.destination_directory,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            created_at=CREATED_AT,
        )

        self.assertEqual(result.path, self.package_path.resolve())
        self.assertTrue(result.verification.is_valid)
        self.assertEqual(result.verification.issues, [])
        self.assertEqual(result.manifest.created_at, CREATED_AT)
        self.assertEqual(result.manifest.application_version, "0.7.3")
        self.assertEqual(sha256_file(self.source_path), source_before)

        with zipfile.ZipFile(self.package_path, "r") as archive:
            self.assertEqual(
                [member.filename for member in archive.infolist()],
                ["manifest.json", "foreman.db"],
            )
            self.assertEqual(
                archive.read("manifest.json"),
                canonical_json_bytes(result.manifest),
            )

        leftovers = [
            path.name
            for path in self.destination_directory.iterdir()
            if path.name.startswith(".foreman-backup-")
        ]
        self.assertEqual(leftovers, [])

    def test_create_package_rejects_existing_destination(self) -> None:
        self.create_source_database()
        self.package_path.write_bytes(b"preserve me")

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_backup_package(
                self.database_url,
                self.destination_directory,
                application_name="The Foreman",
                application_version="0.7.3",
                operational_fact_schema_version=1,
                created_at=CREATED_AT,
            )

        self.assertEqual(
            context.exception.code,
            "BACKUP_DESTINATION_EXISTS",
        )
        self.assertEqual(self.package_path.read_bytes(), b"preserve me")

    def test_create_package_rejects_future_database_and_cleans_up(
        self,
    ) -> None:
        self.create_source_database(
            user_version=CURRENT_DATABASE_SCHEMA_VERSION + 1
        )

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_backup_package(
                self.database_url,
                self.destination_directory,
                application_name="The Foreman",
                application_version="0.7.3",
                operational_fact_schema_version=1,
                created_at=CREATED_AT,
            )

        self.assertEqual(
            context.exception.code,
            "BACKUP_PACKAGE_VERIFICATION_FAILED",
        )
        self.assertFalse(self.package_path.exists())
        self.assertEqual(list(self.destination_directory.iterdir()), [])

    def test_verify_package_accepts_supported_upgrade_warning(self) -> None:
        result = self.create_package(user_version=1)
        verification = verify_backup_package(result.path)

        self.assertTrue(verification.result.is_valid)
        self.assertEqual(
            verification.result.compatibility.status,
            "upgrade-required",
        )
        self.assertEqual(
            self.issue_codes(verification),
            ["DATABASE_UPGRADE_REQUIRED"],
        )

    def test_verify_package_rejects_relative_path(self) -> None:
        verification = verify_backup_package(Path("backup.zip"))

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["BACKUP_PACKAGE_PATH_INVALID"],
        )

    def test_verify_package_rejects_unreadable_archive(self) -> None:
        self.package_path.write_bytes(b"not a zip")
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["BACKUP_ARCHIVE_INVALID"],
        )

    def test_verify_package_rejects_extra_member(self) -> None:
        self.create_package()
        self.rewrite_package(extra_members={"extra.txt": b"extra"})
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["ARCHIVE_MEMBER_SET_INVALID"],
        )

    def test_verify_package_rejects_symbolic_link_member(self) -> None:
        self.create_package()
        members = self.read_package_members()
        self.package_path.unlink()
        link = zipfile.ZipInfo("foreman.db")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16

        with zipfile.ZipFile(self.package_path, "w") as archive:
            archive.writestr("manifest.json", members["manifest.json"])
            archive.writestr(link, b"manifest.json")

        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["ARCHIVE_MEMBER_TYPE_INVALID"],
        )

    def test_verify_package_rejects_noncanonical_manifest(self) -> None:
        self.create_package()
        members = self.read_package_members()
        payload = json.loads(members["manifest.json"])
        noncanonical = json.dumps(payload, indent=2).encode("utf-8")
        self.rewrite_package(manifest_bytes=noncanonical)
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["MANIFEST_NOT_CANONICAL"],
        )

    def test_verify_package_rejects_checksum_tampering(self) -> None:
        self.create_package()
        members = self.read_package_members()
        tampered_database = members["foreman.db"] + b"tamper"
        self.rewrite_package(database_bytes=tampered_database)
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertIn(
            "DATABASE_CHECKSUM_MISMATCH",
            self.issue_codes(verification),
        )
        self.assertIn(
            "DATABASE_SIZE_MISMATCH",
            self.issue_codes(verification),
        )

    def test_verify_package_rejects_manifest_size_mismatch(self) -> None:
        self.create_package()
        manifest_bytes = self.modified_manifest_bytes(
            lambda manifest: manifest["database"].update(
                {"byteSize": manifest["database"]["byteSize"] + 1}
            )
        )
        self.rewrite_package(manifest_bytes=manifest_bytes)
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["DATABASE_SIZE_MISMATCH"],
        )

    def test_verify_package_rejects_manifest_table_mismatch(self) -> None:
        self.create_package()

        def update(manifest) -> None:
            manifest["database"]["tables"].remove("tasks")
            manifest["recordCounts"].pop("tasks")

        self.rewrite_package(
            manifest_bytes=self.modified_manifest_bytes(update)
        )
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertIn(
            "DATABASE_TABLES_MISMATCH",
            self.issue_codes(verification),
        )
        self.assertIn(
            "DATABASE_RECORD_COUNTS_MISMATCH",
            self.issue_codes(verification),
        )

    def test_verify_package_rejects_record_count_mismatch(self) -> None:
        self.create_package()
        manifest_bytes = self.modified_manifest_bytes(
            lambda manifest: manifest["recordCounts"].update(
                {"tasks": 99}
            )
        )
        self.rewrite_package(manifest_bytes=manifest_bytes)
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["DATABASE_RECORD_COUNTS_MISMATCH"],
        )

    def test_verify_package_rejects_manifest_version_mismatch(self) -> None:
        self.create_package()
        manifest_bytes = self.modified_manifest_bytes(
            lambda manifest: manifest["database"].update(
                {"userVersion": 1}
            )
        )
        self.rewrite_package(manifest_bytes=manifest_bytes)
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["DATABASE_VERSION_MISMATCH"],
        )
    def test_verify_package_rejects_duplicate_member(self) -> None:
        self.create_package()
        members = self.read_package_members()
        self.package_path.unlink()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)

            with zipfile.ZipFile(self.package_path, "w") as archive:
                archive.writestr(
                    "manifest.json",
                    members["manifest.json"],
                )
                archive.writestr("foreman.db", members["foreman.db"])
                archive.writestr("foreman.db", members["foreman.db"])

        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["ARCHIVE_MEMBER_DUPLICATE"],
        )

    def test_verify_package_rejects_malformed_manifest(self) -> None:
        self.create_package()
        self.rewrite_package(manifest_bytes=b"{not-json")
        verification = verify_backup_package(self.package_path)

        self.assertFalse(verification.result.is_valid)
        self.assertEqual(
            self.issue_codes(verification),
            ["MANIFEST_JSON_INVALID"],
        )

    def test_create_package_cleans_up_publish_failure(self) -> None:
        self.create_source_database()

        with patch(
            "app.services.recovery.os.replace",
            side_effect=OSError("publish failed"),
        ):
            with self.assertRaises(RecoveryContractError) as context:
                create_verified_backup_package(
                    self.database_url,
                    self.destination_directory,
                    application_name="The Foreman",
                    application_version="0.7.3",
                    operational_fact_schema_version=1,
                    created_at=CREATED_AT,
                )

        self.assertEqual(
            context.exception.code,
            "BACKUP_PUBLISH_FAILED",
        )
        self.assertFalse(self.package_path.exists())
        self.assertEqual(list(self.destination_directory.iterdir()), [])

    def test_create_package_removes_failed_final_verification(
        self,
    ) -> None:
        self.create_source_database()
        original_verify = verify_backup_package
        call_count = 0

        def fail_second_verification(path):
            nonlocal call_count
            call_count += 1
            verification = original_verify(path)

            if call_count == 1:
                return verification

            return BackupPackageVerification(
                package_path=Path(path),
                manifest=verification.manifest,
                result=build_verification_result(
                    [
                        VerificationIssue(
                            code="TEST_FINAL_VERIFICATION_FAILED",
                            message="Final verification failed.",
                        )
                    ]
                ),
            )

        with patch(
            "app.services.recovery.verify_backup_package",
            side_effect=fail_second_verification,
        ):
            with self.assertRaises(RecoveryContractError) as context:
                create_verified_backup_package(
                    self.database_url,
                    self.destination_directory,
                    application_name="The Foreman",
                    application_version="0.7.3",
                    operational_fact_schema_version=1,
                    created_at=CREATED_AT,
                )

        self.assertEqual(
            context.exception.code,
            "BACKUP_PACKAGE_VERIFICATION_FAILED",
        )
        self.assertEqual(call_count, 2)
        self.assertFalse(self.package_path.exists())
        self.assertEqual(list(self.destination_directory.iterdir()), [])

    def test_create_package_rejects_incomplete_current_schema(
        self,
    ) -> None:
        self.create_source_database()
        connection = sqlite3.connect(self.source_path)

        try:
            connection.execute("DROP TABLE task_migrations")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(RecoveryContractError) as context:
            create_verified_backup_package(
                self.database_url,
                self.destination_directory,
                application_name="The Foreman",
                application_version="0.7.3",
                operational_fact_schema_version=1,
                created_at=CREATED_AT,
            )

        self.assertEqual(
            context.exception.code,
            "BACKUP_PACKAGE_VERIFICATION_FAILED",
        )
        self.assertFalse(self.package_path.exists())
        self.assertEqual(list(self.destination_directory.iterdir()), [])

LEGACY_RESTORE_SCHEMA = """
CREATE TABLE projects (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL,
    progress FLOAT NOT NULL,
    notes TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    archived_at DATETIME
);

CREATE TABLE tasks (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    completed BOOLEAN NOT NULL,
    project_id VARCHAR(36),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
);
"""


class RestoreCandidateStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.live_path = self.root / "live.db"
        self.source_path = self.root / "source.db"
        self.backup_directory = self.root / "backups"
        self.candidate_directory = self.root / "candidate"
        self.backup_directory.mkdir()
        self.candidate_directory.mkdir()
        self.candidate_path = (
            self.candidate_directory / "foreman.db"
        )

        with sqlite3.connect(self.live_path) as connection:
            connection.execute(
                "CREATE TABLE sentinel (value TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO sentinel (value) VALUES ('live')"
            )
            connection.commit()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @property
    def live_database_url(self) -> str:
        return f"sqlite:///{self.live_path}"

    @property
    def source_database_url(self) -> str:
        return f"sqlite:///{self.source_path}"

    def create_current_source_database(self) -> None:
        import app.models  # noqa: F401

        engine = create_engine(self.source_database_url)

        try:
            with engine.connect() as connection:
                prepare_database_schema(connection)

            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, space_id, name, type, status, priority, progress,
                            start_date, target_date, estimated_cost,
                            description, notes, created_at, updated_at,
                            archived_at
                        ) VALUES (
                            :id, :space_id, :name, :type, :status, :priority,
                            :progress, NULL, NULL, :estimated_cost,
                            :description, :notes, :created_at,
                            :updated_at, NULL
                        )
                        """
                    ),
                    {
                        "id": "project-1",
                        "space_id": DEFAULT_SPACE_ID,
                        "name": "Current Project",
                        "type": "other",
                        "status": "active",
                        "priority": "medium",
                        "progress": 25,
                        "estimated_cost": 0,
                        "description": "",
                        "notes": "Preserve current data",
                        "created_at": "2026-07-31 16:00:00",
                        "updated_at": "2026-07-31 16:00:00",
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            id, space_id, title, priority, completed, project_id,
                            created_at, updated_at
                        ) VALUES (
                            :id, :space_id, :title, :priority, :completed,
                            :project_id, :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "id": "task-1",
                        "space_id": DEFAULT_SPACE_ID,
                        "title": "Current Task",
                        "priority": "high",
                        "completed": False,
                        "project_id": "project-1",
                        "created_at": "2026-07-31 16:00:00",
                        "updated_at": "2026-07-31 16:00:00",
                    },
                )
                timestamp = "2026-07-31 16:00:00"
                connection.execute(
                    text(
                        """
                        INSERT INTO spaces (
                            id, name, description, created_at, updated_at
                        ) VALUES (
                            'space-1', 'Household', '', :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO people (
                            id, display_name, given_name, family_name,
                            description, created_at, updated_at
                        ) VALUES (
                            'person-1', 'Amber', 'Amber', '', '',
                            :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO organizations (
                            id, name, description, created_at, updated_at
                        ) VALUES (
                            'organization-1', 'Utility', '',
                            :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO organization_space_relationships (
                            id, space_id, organization_id, role,
                            created_at, updated_at
                        ) VALUES (
                            'relationship-1', 'space-1', 'organization-1',
                            'utility', :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO members (
                            id, space_id, person_id, role, responsibilities,
                            created_at, updated_at
                        ) VALUES (
                            'member-1', 'space-1', 'person-1', 'member', '',
                            :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO module_states (
                            module_id, enabled, created_at, updated_at
                        ) VALUES (
                            'inventory', 1, :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
        finally:
            engine.dispose()

    def create_version_two_source_database(self) -> None:
        engine = create_engine(self.source_database_url)

        try:
            with engine.begin() as connection:
                create_pre_v4_tables(
                    connection,
                    {
                        "inventory_items",
                        "projects",
                        "project_material_requirements",
                        "tasks",
                        "inventory_migrations",
                        "project_migrations",
                        "task_migrations",
                    },
                )
                timestamp = "2026-07-31 16:00:00.123456"
                connection.execute(
                    text(
                        """
                        INSERT INTO inventory_items (
                            id, name, category, quantity, unit, minimum,
                            location, cost, supplier, notes,
                            created_at, updated_at
                        ) VALUES (
                            'inventory-v2', 'Version 2 Fastener', 'Hardware',
                            17.5, 'boxes', 3.25, 'Shelf V2', 4.75,
                            'Supplier V2', 'Preserve inventory v2',
                            :timestamp, :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, name, type, status, priority, progress,
                            start_date, target_date, estimated_cost,
                            description, notes, created_at, updated_at,
                            archived_at
                        ) VALUES (
                            'project-v2', 'Version 2 Project', 'build',
                            'active', 'high', 37.5, '2026-07-01',
                            '2026-09-01', 725.5, 'Preserve description v2',
                            'Preserve notes v2', :timestamp, :timestamp, NULL
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO project_material_requirements (
                            project_id, inventory_item_id,
                            required_quantity, note
                        ) VALUES (
                            'project-v2', 'inventory-v2', 6.5,
                            'Preserve material v2'
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            id, title, priority, completed, project_id,
                            created_at, updated_at
                        ) VALUES
                            (
                                'task-v2', 'Version 2 Task', 'high', 0,
                                'project-v2', :timestamp, :timestamp
                            ),
                            (
                                'task-v2-tombstone-source',
                                'Unmapped Version 2 Task', 'low', 1, NULL,
                                :timestamp, :timestamp
                            )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO inventory_migrations (
                            id, source, source_record_id,
                            inventory_item_id, migrated_at
                        ) VALUES (
                            101, 'browser-local', 'inventory-source-v2',
                            'inventory-v2', :timestamp
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO project_migrations (
                            id, source, source_record_id, project_id,
                            payload_hash, migrated_at
                        ) VALUES (
                            102, 'browser-local', 'project-source-v2',
                            'project-v2', :payload_hash, :timestamp
                        )
                        """
                    ),
                    {
                        "payload_hash": "b" * 64,
                        "timestamp": timestamp,
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO task_migrations (
                            id, source, source_record_id, task_id, migrated_at
                        ) VALUES
                            (
                                103, 'browser-local', 'task-source-v2',
                                'task-v2', :timestamp
                            ),
                            (
                                104, 'browser-local',
                                'task-tombstone-source-v2', NULL, :timestamp
                            )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.exec_driver_sql("PRAGMA user_version = 2")
        finally:
            engine.dispose()

    def create_version_three_source_database(
        self,
        *,
        default_name: str | None = None,
        fixed_default: bool = False,
    ) -> None:
        import app.models  # noqa: F401

        engine = create_engine(self.source_database_url)

        try:
            with engine.begin() as connection:
                create_pre_v4_tables(
                    connection,
                    set(PRE_V4_TABLE_NAMES),
                )
                timestamp = "2026-07-31 16:00:00"
                space_id = DEFAULT_SPACE_ID if fixed_default else "space-1"
                space_name = default_name or (
                    "Edited Default" if fixed_default else "Household"
                )
                connection.execute(
                    text(
                        "INSERT INTO spaces VALUES "
                        "(:id, :name, 'Preserve foundation', "
                        ":timestamp, :timestamp)"
                    ),
                    {
                        "id": space_id,
                        "name": space_name,
                        "timestamp": timestamp,
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, name, type, status, priority, progress,
                            start_date, target_date, estimated_cost,
                            description, notes, created_at, updated_at,
                            archived_at
                        ) VALUES (
                            'project-v3', 'Version 3 Project', 'other',
                            'active', 'medium', 10, NULL, NULL, 0,
                            '', 'Preserve v3', :timestamp, :timestamp, NULL
                        )
                        """
                    ),
                    {"timestamp": timestamp},
                )
                connection.exec_driver_sql("PRAGMA user_version=3")
        finally:
            engine.dispose()

    def create_legacy_source_database(self) -> None:
        with sqlite3.connect(self.source_path) as connection:
            connection.executescript(LEGACY_RESTORE_SCHEMA)
            connection.execute(
                """
                INSERT INTO projects (
                    id, name, status, progress, notes,
                    created_at, updated_at, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-project",
                    "Legacy Project",
                    "active",
                    37.5,
                    "Preserve legacy data",
                    "2026-07-01 10:00:00",
                    "2026-07-02 10:00:00",
                    None,
                ),
            )
            connection.execute(
                """
                INSERT INTO tasks (
                    id, title, priority, completed, project_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-task",
                    "Legacy Task",
                    "high",
                    False,
                    "legacy-project",
                    "2026-07-01 11:00:00",
                    "2026-07-01 11:00:00",
                ),
            )
            connection.execute("PRAGMA user_version = 1")
            connection.commit()

    def create_package(self):
        return create_verified_backup_package(
            self.source_database_url,
            self.backup_directory,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            created_at=CREATED_AT,
        )

    def test_stage_current_package_is_exact_and_non_destructive(
        self,
    ) -> None:
        self.create_current_source_database()
        package = self.create_package()
        package_checksum = sha256_file(package.path)
        live_checksum = sha256_file(self.live_path)

        with zipfile.ZipFile(package.path, "r") as archive:
            packaged_database = archive.read("foreman.db")

        staged = stage_restore_candidate(
            package.path,
            self.candidate_path,
            live_database_url=self.live_database_url,
        )

        self.assertFalse(staged.was_upgraded)
        self.assertEqual(
            self.candidate_path.read_bytes(),
            packaged_database,
        )
        self.assertEqual(
            staged.database_manifest.user_version,
            CURRENT_DATABASE_SCHEMA_VERSION,
        )
        self.assertEqual(
            staged.record_count_mapping()["projects"],
            1,
        )
        self.assertEqual(
            staged.record_count_mapping()["tasks"],
            1,
        )
        self.assertEqual(staged.record_count_mapping()["spaces"], 2)
        self.assertEqual(staged.record_count_mapping()["people"], 1)
        self.assertEqual(staged.record_count_mapping()["organizations"], 1)
        self.assertEqual(staged.record_count_mapping()["members"], 1)
        self.assertEqual(staged.record_count_mapping()["module_states"], 1)

        with sqlite3.connect(self.candidate_path) as connection:
            member = connection.execute(
                "SELECT space_id, person_id, role FROM members"
            ).fetchone()
            self.assertEqual(member, ("space-1", "person-1", "member"))
        self.assertEqual(sha256_file(package.path), package_checksum)
        self.assertEqual(sha256_file(self.live_path), live_checksum)

    def test_stage_legacy_package_upgrades_and_preserves_records(
        self,
    ) -> None:
        self.create_legacy_source_database()
        package = self.create_package()
        package_checksum = sha256_file(package.path)
        live_checksum = sha256_file(self.live_path)

        staged = stage_restore_candidate(
            package.path,
            self.candidate_path,
            live_database_url=self.live_database_url,
        )

        self.assertTrue(staged.was_upgraded)
        self.assertEqual(
            staged.source_manifest.database.user_version,
            1,
        )
        self.assertEqual(
            staged.database_manifest.user_version,
            CURRENT_DATABASE_SCHEMA_VERSION,
        )
        counts = staged.record_count_mapping()
        self.assertEqual(counts["projects"], 1)
        self.assertEqual(counts["tasks"], 1)
        self.assertEqual(counts["tools"], 0)
        self.assertEqual(counts["care_plans"], 0)
        self.assertEqual(counts["tool_maintenance_records"], 0)
        self.assertEqual(counts["work_tool_requirements"], 0)

        for table in set(counts) - {"projects", "tasks", "spaces"}:
            self.assertEqual(counts[table], 0)

        self.assertEqual(counts["spaces"], 1)

        with sqlite3.connect(self.candidate_path) as connection:
            project = connection.execute(
                """
                SELECT name, type, priority, description, notes
                FROM projects
                WHERE id = 'legacy-project'
                """
            ).fetchone()

        self.assertEqual(
            project,
            (
                "Legacy Project",
                "other",
                "medium",
                "",
                "Preserve legacy data",
            ),
        )
        self.assertEqual(sha256_file(package.path), package_checksum)
        self.assertEqual(sha256_file(self.live_path), live_checksum)

    def test_stage_version_two_package_preserves_complete_legacy_state(
        self,
    ) -> None:
        self.create_version_two_source_database()
        package = self.create_package()

        staged = stage_restore_candidate(
            package.path,
            self.candidate_path,
            live_database_url=self.live_database_url,
        )

        self.assertTrue(staged.was_upgraded)
        self.assertEqual(staged.source_manifest.database.user_version, 2)
        self.assertEqual(
            staged.database_manifest.user_version,
            CURRENT_DATABASE_SCHEMA_VERSION,
        )

        counts = staged.record_count_mapping()
        self.assertEqual(
            {
                table_name: counts[table_name]
                for table_name in (
                    "inventory_items",
                    "projects",
                    "project_material_requirements",
                    "tasks",
                    "inventory_migrations",
                    "project_migrations",
                    "task_migrations",
                )
            },
            {
                "inventory_items": 1,
                "projects": 1,
                "project_material_requirements": 1,
                "tasks": 2,
                "inventory_migrations": 1,
                "project_migrations": 1,
                "task_migrations": 2,
            },
        )

        for table_name in (
            "spaces",
            "people",
            "organizations",
            "organization_space_relationships",
            "members",
            "module_states",
        ):
            self.assertEqual(
                counts[table_name],
                1 if table_name == "spaces" else 0,
            )

        with sqlite3.connect(self.candidate_path) as connection:
            default_space = connection.execute(
                "SELECT id, name, description FROM spaces"
            ).fetchall()
            inventory = connection.execute(
                """
                SELECT id, space_id, name, category, quantity, unit, minimum,
                       location, cost, supplier, notes, created_at, updated_at
                FROM inventory_items
                """
            ).fetchone()
            project = connection.execute(
                """
                SELECT id, space_id, name, type, status, priority, progress,
                       start_date, target_date, estimated_cost, description,
                       notes, created_at, updated_at, archived_at
                FROM projects
                """
            ).fetchone()
            material = connection.execute(
                "SELECT * FROM project_material_requirements"
            ).fetchone()
            tasks = connection.execute(
                """
                SELECT id, space_id, title, priority, completed, project_id,
                       created_at, updated_at
                FROM tasks ORDER BY id
                """
            ).fetchall()
            inventory_migration = connection.execute(
                "SELECT * FROM inventory_migrations"
            ).fetchone()
            project_migration = connection.execute(
                "SELECT * FROM project_migrations"
            ).fetchone()
            task_migrations = connection.execute(
                "SELECT * FROM task_migrations ORDER BY id"
            ).fetchall()
            provenance_mismatches = connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT migration.id
                    FROM inventory_migrations AS migration
                    JOIN inventory_items AS target
                      ON target.id = migration.inventory_item_id
                    WHERE migration.space_id != target.space_id
                    UNION ALL
                    SELECT migration.id
                    FROM project_migrations AS migration
                    JOIN projects AS target
                      ON target.id = migration.project_id
                    WHERE migration.space_id != target.space_id
                    UNION ALL
                    SELECT migration.id
                    FROM task_migrations AS migration
                    JOIN tasks AS target ON target.id = migration.task_id
                    WHERE migration.space_id != target.space_id
                )
                """
            ).fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertEqual(
            default_space,
            [
                (
                    DEFAULT_SPACE_ID,
                    DEFAULT_SPACE_NAME,
                    DEFAULT_SPACE_DESCRIPTION,
                )
            ],
        )
        self.assertEqual(
            inventory,
            (
                "inventory-v2",
                DEFAULT_SPACE_ID,
                "Version 2 Fastener",
                "Hardware",
                17.5,
                "boxes",
                3.25,
                "Shelf V2",
                4.75,
                "Supplier V2",
                "Preserve inventory v2",
                "2026-07-31 16:00:00.123456",
                "2026-07-31 16:00:00.123456",
            ),
        )
        self.assertEqual(project[0:2], ("project-v2", DEFAULT_SPACE_ID))
        self.assertEqual(project[2:12], (
            "Version 2 Project",
            "build",
            "active",
            "high",
            37.5,
            "2026-07-01",
            "2026-09-01",
            725.5,
            "Preserve description v2",
            "Preserve notes v2",
        ))
        self.assertEqual(
            project[12:],
            (
                "2026-07-31 16:00:00.123456",
                "2026-07-31 16:00:00.123456",
                None,
            ),
        )
        self.assertEqual(
            material,
            (
                "project-v2",
                "inventory-v2",
                6.5,
                "Preserve material v2",
            ),
        )
        self.assertEqual(
            tasks,
            [
                (
                    "task-v2",
                    DEFAULT_SPACE_ID,
                    "Version 2 Task",
                    "high",
                    0,
                    "project-v2",
                    "2026-07-31 16:00:00.123456",
                    "2026-07-31 16:00:00.123456",
                ),
                (
                    "task-v2-tombstone-source",
                    DEFAULT_SPACE_ID,
                    "Unmapped Version 2 Task",
                    "low",
                    1,
                    None,
                    "2026-07-31 16:00:00.123456",
                    "2026-07-31 16:00:00.123456",
                ),
            ],
        )
        self.assertEqual(inventory_migration[0:2], (101, DEFAULT_SPACE_ID))
        self.assertEqual(inventory_migration[2:], (
            "browser-local",
            "inventory-source-v2",
            "inventory-v2",
            "2026-07-31 16:00:00.123456",
        ))
        self.assertEqual(project_migration[0:2], (102, DEFAULT_SPACE_ID))
        self.assertEqual(project_migration[2:], (
            "browser-local",
            "project-source-v2",
            "project-v2",
            "b" * 64,
            "2026-07-31 16:00:00.123456",
        ))
        self.assertEqual(
            task_migrations,
            [
                (
                    103,
                    DEFAULT_SPACE_ID,
                    "browser-local",
                    "task-source-v2",
                    "task-v2",
                    "2026-07-31 16:00:00.123456",
                ),
                (
                    104,
                    DEFAULT_SPACE_ID,
                    "browser-local",
                    "task-tombstone-source-v2",
                    None,
                    "2026-07-31 16:00:00.123456",
                ),
            ],
        )
        self.assertEqual(provenance_mismatches, 0)
        self.assertNotIn("__foreman_v4_space_scope_journal", tables)

    def test_stage_version_three_preserves_foundation_and_adds_default(
        self,
    ) -> None:
        self.create_version_three_source_database()
        package = self.create_package()

        staged = stage_restore_candidate(
            package.path,
            self.candidate_path,
            live_database_url=self.live_database_url,
        )

        self.assertTrue(staged.was_upgraded)
        self.assertEqual(staged.source_manifest.database.user_version, 3)
        self.assertEqual(staged.record_count_mapping()["spaces"], 2)

        with sqlite3.connect(self.candidate_path) as connection:
            spaces = connection.execute(
                "SELECT id, name, description FROM spaces ORDER BY id"
            ).fetchall()
            project_space_id = connection.execute(
                "SELECT space_id FROM projects WHERE id = 'project-v3'"
            ).fetchone()[0]

        self.assertIn(
            ("space-1", "Household", "Preserve foundation"),
            spaces,
        )
        self.assertIn(
            (
                DEFAULT_SPACE_ID,
                DEFAULT_SPACE_NAME,
                DEFAULT_SPACE_DESCRIPTION,
            ),
            spaces,
        )
        self.assertEqual(project_space_id, DEFAULT_SPACE_ID)

    def test_stage_version_three_preserves_edited_fixed_metadata(
        self,
    ) -> None:
        self.create_version_three_source_database(fixed_default=True)
        package = self.create_package()

        staged = stage_restore_candidate(
            package.path,
            self.candidate_path,
            live_database_url=self.live_database_url,
        )

        self.assertEqual(staged.record_count_mapping()["spaces"], 1)

        with sqlite3.connect(self.candidate_path) as connection:
            fixed = connection.execute(
                "SELECT name, description FROM spaces WHERE id = ?",
                (DEFAULT_SPACE_ID,),
            ).fetchone()

        self.assertEqual(
            fixed,
            ("Edited Default", "Preserve foundation"),
        )

    def test_stage_version_three_name_conflict_cleans_candidate(self) -> None:
        self.create_version_three_source_database(
            default_name="hardhead works"
        )
        package = self.create_package()

        with self.assertRaisesRegex(
            RecoveryContractError,
            "Default Space name conflict",
        ) as context:
            stage_restore_candidate(
                package.path,
                self.candidate_path,
                live_database_url=self.live_database_url,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_CANDIDATE_DEFAULT_SPACE_CONFLICT",
        )
        self.assertFalse(self.candidate_path.exists())

    def test_recovery_count_delta_requires_exact_default_metadata(
        self,
    ) -> None:
        self.create_version_three_source_database()
        package = self.create_package()
        prepare_schema = recovery_service._prepare_restore_candidate_schema

        def corrupt_inserted_default(candidate_path: Path) -> None:
            prepare_schema(candidate_path)

            with sqlite3.connect(candidate_path) as connection:
                connection.execute(
                    "UPDATE spaces SET description = 'Wrong' WHERE id = ?",
                    (DEFAULT_SPACE_ID,),
                )
                connection.commit()

        with patch(
            "app.services.recovery._prepare_restore_candidate_schema",
            side_effect=corrupt_inserted_default,
        ):
            with self.assertRaises(RecoveryContractError) as context:
                stage_restore_candidate(
                    package.path,
                    self.candidate_path,
                    live_database_url=self.live_database_url,
                )

        self.assertEqual(
            context.exception.code,
            "RESTORE_CANDIDATE_DEFAULT_SPACE_INVALID",
        )
        self.assertFalse(self.candidate_path.exists())

    def test_invalid_package_is_rejected_before_destination(
        self,
    ) -> None:
        invalid_package = self.root / "invalid.zip"
        invalid_package.write_bytes(b"not a zip")
        live_checksum = sha256_file(self.live_path)

        with self.assertRaises(RecoveryContractError) as context:
            stage_restore_candidate(
                invalid_package,
                self.candidate_path,
                live_database_url=self.live_database_url,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_CANDIDATE_PACKAGE_INVALID",
        )
        self.assertFalse(self.candidate_path.exists())
        self.assertEqual(sha256_file(self.live_path), live_checksum)

    def test_live_database_destination_is_rejected(self) -> None:
        self.create_current_source_database()
        package = self.create_package()
        live_checksum = sha256_file(self.live_path)

        with self.assertRaises(RecoveryContractError) as context:
            stage_restore_candidate(
                package.path,
                self.live_path,
                live_database_url=self.live_database_url,
            )

        self.assertEqual(
            context.exception.code,
            "RESTORE_CANDIDATE_LIVE_DATABASE_CONFLICT",
        )
        self.assertEqual(sha256_file(self.live_path), live_checksum)

    def test_upgrade_failure_removes_candidate_and_sidecars(
        self,
    ) -> None:
        self.create_legacy_source_database()
        package = self.create_package()

        def fail_upgrade(_connection) -> None:
            Path(f"{self.candidate_path}-journal").write_bytes(
                b"temporary"
            )
            Path(f"{self.candidate_path}-wal").write_bytes(
                b"temporary"
            )
            Path(f"{self.candidate_path}-shm").write_bytes(
                b"temporary"
            )
            raise RuntimeError("simulated upgrade failure")

        with patch(
            "app.core.database.apply_schema_upgrades",
            side_effect=fail_upgrade,
        ):
            with self.assertRaises(RecoveryContractError) as context:
                stage_restore_candidate(
                    package.path,
                    self.candidate_path,
                    live_database_url=self.live_database_url,
                )

        self.assertEqual(
            context.exception.code,
            "RESTORE_CANDIDATE_STAGING_FAILED",
        )
        self.assertFalse(self.candidate_path.exists())

        for sidecar in (
            Path(f"{self.candidate_path}-journal"),
            Path(f"{self.candidate_path}-wal"),
            Path(f"{self.candidate_path}-shm"),
        ):
            self.assertFalse(sidecar.exists())


class PreRestoreSafetyBackupTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_path = self.root / "foreman.db"
        self.database_url = f"sqlite:///{self.source_path}"

        connection = sqlite3.connect(self.source_path)

        try:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
                CREATE TABLE inventory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                );
                CREATE TABLE inventory_migrations (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE project_material_requirements (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE project_migrations (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE task_migrations (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE work_dependencies (
                    id TEXT PRIMARY KEY
                );
                """
            )
            connection.executescript(FOUNDATION_TABLE_SCHEMA)
            connection.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                ("project-1", "Safety Backup Project"),
            )
            connection.execute(
                "INSERT INTO tasks (id, project_id, title) "
                "VALUES (?, ?, ?)",
                ("task-1", "project-1", "Safety Backup Task"),
            )
            connection.execute(
                "INSERT INTO inventory_items (name) VALUES (?)",
                ("Fastener",),
            )
            connection.executescript(
                """
                CREATE TABLE tools (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE care_plans (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE tool_maintenance_records (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE work_tool_requirements (
                    id TEXT PRIMARY KEY
                );
                """
            )
            connection.executescript(
                CURRENT_CALENDAR_TABLE_SCHEMA
            )
            connection.execute(
                f"PRAGMA user_version = {CURRENT_DATABASE_SCHEMA_VERSION}"
            )
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_safety_backup(self):
        return create_pre_restore_safety_backup(
            self.database_url,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            created_at=CREATED_AT,
        )

    def test_safety_backup_is_private_durable_and_verified(
        self,
    ) -> None:
        source_checksum = sha256_file(self.source_path)
        result = self.create_safety_backup()
        recovery_directory = self.root / "recovery"
        safety_directory = recovery_directory / "safety-backups"

        self.assertEqual(
            result.path,
            (
                safety_directory
                / "foreman-backup-20260731T160000Z.zip"
            ).resolve(),
        )
        self.assertTrue(result.verification.is_valid)
        self.assertEqual(
            stat.S_IMODE(recovery_directory.stat().st_mode),
            0o700,
        )
        self.assertEqual(
            stat.S_IMODE(safety_directory.stat().st_mode),
            0o700,
        )
        self.assertEqual(
            stat.S_IMODE(result.path.stat().st_mode),
            0o600,
        )
        self.assertEqual(sha256_file(self.source_path), source_checksum)

        verification = verify_backup_package(result.path)
        self.assertTrue(verification.result.is_valid)
        self.assertEqual(verification.manifest, result.manifest)

    def test_safety_backup_rejects_symbolic_link_workspace(
        self,
    ) -> None:
        external = self.root / "external"
        external.mkdir()
        (self.root / "recovery").symlink_to(
            external,
            target_is_directory=True,
        )

        with self.assertRaises(RecoveryContractError) as context:
            self.create_safety_backup()

        self.assertEqual(
            context.exception.code,
            "RECOVERY_WORKSPACE_INVALID",
        )
        self.assertEqual(list(external.iterdir()), [])

    def test_safety_backup_requires_live_database_filesystem(
        self,
    ) -> None:
        with patch(
            "app.services.recovery._paths_share_device",
            return_value=False,
        ):
            with self.assertRaises(RecoveryContractError) as context:
                self.create_safety_backup()

        self.assertEqual(
            context.exception.code,
            "RECOVERY_WORKSPACE_FILESYSTEM_MISMATCH",
        )
        safety_directory = (
            self.root / "recovery" / "safety-backups"
        )
        self.assertEqual(list(safety_directory.iterdir()), [])

    def test_durability_failure_removes_published_package(
        self,
    ) -> None:
        with patch(
            "app.services.recovery._fsync_file",
            side_effect=RecoveryContractError(
                "SAFETY_BACKUP_DURABILITY_FAILED",
                "simulated durability failure",
            ),
        ):
            with self.assertRaises(RecoveryContractError) as context:
                self.create_safety_backup()

        self.assertEqual(
            context.exception.code,
            "SAFETY_BACKUP_DURABILITY_FAILED",
        )
        safety_directory = (
            self.root / "recovery" / "safety-backups"
        )
        self.assertEqual(list(safety_directory.iterdir()), [])

    def test_failed_durable_verification_removes_package(
        self,
    ) -> None:
        original_verify = verify_backup_package
        call_count = 0

        def fail_third_verification(path):
            nonlocal call_count
            call_count += 1
            verification = original_verify(path)

            if call_count < 3:
                return verification

            return BackupPackageVerification(
                package_path=Path(path),
                manifest=verification.manifest,
                result=build_verification_result(
                    [
                        VerificationIssue(
                            code="TEST_DURABLE_VERIFICATION_FAILED",
                            message="Durable verification failed.",
                        )
                    ]
                ),
            )

        with patch(
            "app.services.recovery.verify_backup_package",
            side_effect=fail_third_verification,
        ):
            with self.assertRaises(RecoveryContractError) as context:
                self.create_safety_backup()

        self.assertEqual(
            context.exception.code,
            "SAFETY_BACKUP_VERIFICATION_FAILED",
        )
        self.assertEqual(call_count, 3)
        safety_directory = (
            self.root / "recovery" / "safety-backups"
        )
        self.assertEqual(list(safety_directory.iterdir()), [])


class RestoreActivationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.live_path = self.root / "foreman.db"
        self.source_path = self.root / "source.db"
        self.package_directory = self.root / "packages"
        self.staging_directory = self.root / "staging"
        self.package_directory.mkdir()
        self.staging_directory.mkdir()
        self._create_database(
            self.live_path,
            project_id="live-project",
            project_name="Live Project",
        )
        self._create_database(
            self.source_path,
            project_id="restored-project",
            project_name="Restored Project",
        )

    def tearDown(self) -> None:
        state = maintenance_coordinator.snapshot()

        if state.emergency_latched:
            maintenance_coordinator.clear_emergency_latch()

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
            with engine.connect() as connection:
                prepare_database_schema(connection)

            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, space_id, name, type, status, priority, progress,
                            start_date, target_date, estimated_cost,
                            description, notes, created_at, updated_at,
                            archived_at
                        ) VALUES (
                            :id, :space_id, :name, 'other', 'active', 'medium', 0,
                            NULL, NULL, 0, '', '', :created_at,
                            :updated_at, NULL
                        )
                        """
                    ),
                    {
                        "id": project_id,
                        "space_id": DEFAULT_SPACE_ID,
                        "name": project_name,
                        "created_at": "2026-08-01 18:00:00",
                        "updated_at": "2026-08-01 18:00:00",
                    },
                )
        finally:
            engine.dispose()

    def _stage_candidate(self) -> StagedRestoreCandidate:
        package = create_verified_backup_package(
            self.source_database_url,
            self.package_directory,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            created_at=CREATED_AT,
        )
        return stage_restore_candidate(
            package.path,
            self.staging_directory / "foreman.db",
            live_database_url=self.live_database_url,
        )

    def _activate(
        self,
        staged: StagedRestoreCandidate,
    ) -> RestoreActivationResult:
        return activate_staged_restore(
            staged,
            live_database_url=self.live_database_url,
            application_name="The Foreman",
            application_version="0.7.3",
            operational_fact_schema_version=1,
            safety_backup_created_at=CREATED_AT,
        )

    def _project_ids(self) -> list[str]:
        with sqlite3.connect(self.live_path) as connection:
            return [
                str(row[0])
                for row in connection.execute(
                    "SELECT id FROM projects ORDER BY id"
                )
            ]

    def test_activation_replaces_and_verifies_live_database(
        self,
    ) -> None:
        staged = self._stage_candidate()
        result = self._activate(staged)

        self.assertEqual(self._project_ids(), ["restored-project"])
        self.assertFalse(staged.path.exists())
        self.assertTrue(result.safety_backup_path.exists())
        self.assertEqual(
            result.record_count_mapping()["projects"],
            1,
        )
        self.assertGreaterEqual(result.operational_fact_count, 1)
        state = maintenance_coordinator.snapshot()
        self.assertFalse(state.maintenance_active)
        self.assertFalse(state.emergency_latched)

    def test_activation_failure_rolls_back_original_database(
        self,
    ) -> None:
        staged = self._stage_candidate()
        original_verify = _verify_activated_database
        call_count = 0

        def fail_first_verification(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise RecoveryContractError(
                    "TEST_ACTIVATION_VERIFICATION_FAILED",
                    "simulated activation verification failure",
                )

            return original_verify(*args, **kwargs)

        with patch(
            "app.services.recovery._verify_activated_database",
            side_effect=fail_first_verification,
        ):
            with self.assertRaises(
                RestoreActivationError
            ) as context:
                self._activate(staged)

        error = context.exception
        self.assertEqual(
            error.code,
            "RESTORE_ACTIVATION_FAILED_ROLLED_BACK",
        )
        self.assertTrue(error.rollback_succeeded)
        self.assertFalse(error.emergency_latched)
        self.assertTrue(error.safety_backup_path.exists())
        self.assertEqual(self._project_ids(), ["live-project"])
        self.assertFalse(
            maintenance_coordinator.snapshot().maintenance_active
        )

    def test_double_failure_latches_emergency_maintenance(
        self,
    ) -> None:
        staged = self._stage_candidate()

        with patch(
            "app.services.recovery._verify_activated_database",
            side_effect=RecoveryContractError(
                "TEST_VERIFICATION_FAILED",
                "simulated verification failure",
            ),
        ):
            with self.assertRaises(
                RestoreActivationError
            ) as context:
                self._activate(staged)

        error = context.exception
        self.assertEqual(
            error.code,
            "RESTORE_ACTIVATION_AND_ROLLBACK_FAILED",
        )
        self.assertFalse(error.rollback_succeeded)
        self.assertTrue(error.emergency_latched)
        self.assertTrue(error.safety_backup_path.exists())

        state = maintenance_coordinator.snapshot()
        self.assertTrue(state.maintenance_active)
        self.assertTrue(state.emergency_latched)

        with self.assertRaises(DatabaseMaintenanceActive):
            maintenance_coordinator.acquire_database_access()

    def test_safety_backup_failure_stops_before_replacement(
        self,
    ) -> None:
        staged = self._stage_candidate()
        live_checksum = sha256_file(self.live_path)

        with patch(
            "app.services.recovery.create_pre_restore_safety_backup",
            side_effect=RecoveryContractError(
                "TEST_SAFETY_BACKUP_FAILED",
                "simulated safety backup failure",
            ),
        ):
            with self.assertRaises(RecoveryContractError) as context:
                self._activate(staged)

        self.assertEqual(
            context.exception.code,
            "TEST_SAFETY_BACKUP_FAILED",
        )
        self.assertEqual(sha256_file(self.live_path), live_checksum)
        self.assertTrue(staged.path.exists())
        self.assertFalse(
            maintenance_coordinator.snapshot().maintenance_active
        )

    def test_changed_candidate_is_rejected_before_safety_backup(
        self,
    ) -> None:
        staged = self._stage_candidate()

        with staged.path.open("ab") as file:
            file.write(b"tampered")

        with patch(
            "app.services.recovery.create_pre_restore_safety_backup"
        ) as create_safety_backup:
            with self.assertRaises(RecoveryContractError) as context:
                self._activate(staged)

        self.assertEqual(
            context.exception.code,
            "RESTORE_ACTIVATION_CANDIDATE_CHANGED",
        )
        create_safety_backup.assert_not_called()
        self.assertEqual(self._project_ids(), ["live-project"])
