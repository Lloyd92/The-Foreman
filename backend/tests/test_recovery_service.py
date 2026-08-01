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

from app.core.schema_upgrades import apply_schema_upgrades
from app.models.base import Base
from app.schemas.recovery import (
    BackupCompatibility,
    BackupManifest,
    DatabaseBackupManifest,
    VerificationIssue,
    VerificationResult,
)
from app.services.recovery import (
    BackupPackageVerification,
    EXPECTED_BACKUP_MEMBERS,
    RecoveryContractError,
    backup_package_filename,
    build_verification_result,
    canonical_json_bytes,
    classify_database_compatibility,
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


CREATED_AT = datetime(2026, 7, 31, 16, 0, tzinfo=timezone.utc)
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

    def create_source_database(self, *, user_version: int = 2) -> None:
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
                """
            )
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
            connection.execute(f"PRAGMA user_version = {user_version}")
            connection.commit()
        finally:
            connection.close()

    def create_package(self, *, user_version: int = 2):
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
        self.create_source_database(user_version=3)

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
                            :id, :name, :type, :status, :priority,
                            :progress, NULL, NULL, :estimated_cost,
                            :description, :notes, :created_at,
                            :updated_at, NULL
                        )
                        """
                    ),
                    {
                        "id": "project-1",
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
                            id, title, priority, completed, project_id,
                            created_at, updated_at
                        ) VALUES (
                            :id, :title, :priority, :completed,
                            :project_id, :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "id": "task-1",
                        "title": "Current Task",
                        "priority": "high",
                        "completed": False,
                        "project_id": "project-1",
                        "created_at": "2026-07-31 16:00:00",
                        "updated_at": "2026-07-31 16:00:00",
                    },
                )
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
            2,
        )
        self.assertEqual(
            staged.record_count_mapping()["projects"],
            1,
        )
        self.assertEqual(
            staged.record_count_mapping()["tasks"],
            1,
        )
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
            2,
        )
        counts = staged.record_count_mapping()
        self.assertEqual(counts["projects"], 1)
        self.assertEqual(counts["tasks"], 1)

        for table in set(counts) - {"projects", "tasks"}:
            self.assertEqual(counts[table], 0)

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
            "app.services.recovery.apply_schema_upgrades",
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
