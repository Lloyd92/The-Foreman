import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app.schemas.recovery import (
    BackupCompatibility,
    BackupManifest,
    DatabaseBackupManifest,
    VerificationIssue,
    VerificationResult,
)
from app.services.recovery import (
    EXPECTED_BACKUP_MEMBERS,
    RecoveryContractError,
    build_verification_result,
    canonical_json_bytes,
    classify_database_compatibility,
    create_verified_sqlite_snapshot,
    normalize_table_counts,
    parse_backup_manifest,
    resolve_sqlite_database_path,
    sha256_file,
    sha256_hex,
    sort_verification_issues,
    validate_archive_member_names,
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
