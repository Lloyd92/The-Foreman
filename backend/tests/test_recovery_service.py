import copy
import json
import unittest
from datetime import datetime, timedelta, timezone

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
    normalize_table_counts,
    parse_backup_manifest,
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
