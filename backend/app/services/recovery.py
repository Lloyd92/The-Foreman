from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import zipfile
from collections.abc import Iterable, Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.database import database_maintenance, prepare_database_schema
from app.core.default_space import (
    DEFAULT_SPACE_DESCRIPTION,
    DEFAULT_SPACE_ID,
    DEFAULT_SPACE_NAME,
    DefaultSpaceConflictError,
)
from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.models.base import Base
from app.models.space import Space
from app.schemas.recovery import (
    BackupCompatibility,
    BackupManifest,
    DatabaseBackupManifest,
    VerificationIssue,
    VerificationResult,
)
from app.services.operations import get_operational_facts


BACKUP_FORMAT_VERSION = 1
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_DATABASE_BYTES = 2 * 1024 * 1024 * 1024
MAX_BACKUP_PACKAGE_BYTES = (
    MAX_DATABASE_BYTES + MAX_MANIFEST_BYTES + 16 * 1024 * 1024
)

EXPECTED_BACKUP_MEMBERS = (
    "manifest.json",
    "foreman.db",
)
CURRENT_REQUIRED_DATABASE_TABLES = frozenset(
    {
        "care_plans",
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
        "task_migrations",
        "tasks",
        "tool_maintenance_records",
        "tools",
        "work_dependencies",
        "work_tool_requirements",
        "spaces",
    }
)

_ISSUE_SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
}


class RecoveryContractError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        location: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.location = location


@dataclass(frozen=True)
class VerifiedSqliteSnapshot:
    path: Path
    database_manifest: DatabaseBackupManifest
    record_counts: tuple[tuple[str, int], ...]

    def record_count_mapping(self) -> dict[str, int]:
        return dict(self.record_counts)


@dataclass(frozen=True)
class BackupPackageVerification:
    package_path: Path
    manifest: BackupManifest | None
    result: VerificationResult


@dataclass(frozen=True)
class VerifiedBackupPackage:
    path: Path
    manifest: BackupManifest
    verification: VerificationResult


@dataclass(frozen=True)
class StagedRestoreCandidate:
    path: Path
    source_manifest: BackupManifest
    database_manifest: DatabaseBackupManifest
    record_counts: tuple[tuple[str, int], ...]
    was_upgraded: bool

    def record_count_mapping(self) -> dict[str, int]:
        return dict(self.record_counts)


class _DuplicateJsonKeyError(ValueError):
    pass


class _NonStandardJsonNumberError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    payload = (
        value.model_dump(mode="json", by_alias=True)
        if isinstance(value, BaseModel)
        else value
    )

    try:
        serialized = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise RecoveryContractError(
            "CANONICAL_JSON_INVALID",
            "Value cannot be serialized as canonical JSON.",
        ) from error

    return serialized.encode("utf-8")


def sha256_hex(data: bytes | bytearray | memoryview) -> str:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("SHA-256 input must be bytes-like.")

    return hashlib.sha256(bytes(data)).hexdigest()


def _validate_member_name(name: object) -> str:
    if not isinstance(name, str) or not name:
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_NAME_INVALID",
            "Backup archive member names must be nonempty strings.",
        )

    if (
        "\x00" in name
        or "\\" in name
        or name.startswith("/")
        or name.startswith("~")
        or ":" in name
    ):
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_NAME_INVALID",
            "Backup archive contains an unsafe member name.",
        )

    parts = name.split("/")

    if (
        len(parts) != 1
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_NAME_INVALID",
            "Backup archive members must use fixed root-level names.",
        )

    return name


def validate_archive_member_names(
    member_names: Iterable[str],
) -> tuple[str, ...]:
    if isinstance(member_names, (str, bytes)):
        raise TypeError("Archive member names must be an iterable of names.")

    names = tuple(
        _validate_member_name(name)
        for name in member_names
    )

    if len(set(names)) != len(names):
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_DUPLICATE",
            "Backup archive contains duplicate member names.",
        )

    if (
        len(names) != len(EXPECTED_BACKUP_MEMBERS)
        or set(names) != set(EXPECTED_BACKUP_MEMBERS)
    ):
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_SET_INVALID",
            "Backup archive must contain exactly the required members.",
        )

    return EXPECTED_BACKUP_MEMBERS


def normalize_table_counts(
    record_counts: Mapping[str, int],
) -> tuple[list[str], dict[str, int]]:
    if not isinstance(record_counts, Mapping):
        raise TypeError("Record counts must be a mapping.")

    copied = list(record_counts.items())
    normalized_names: set[str] = set()

    for table, count in copied:
        if (
            not isinstance(table, str)
            or not table
            or table != table.strip()
            or table.casefold().startswith("sqlite_")
            or "/" in table
            or "\\" in table
            or "\x00" in table
        ):
            raise RecoveryContractError(
                "TABLE_NAME_INVALID",
                "Record-count table names must be safe non-system names.",
            )

        normalized = table.casefold()

        if normalized in normalized_names:
            raise RecoveryContractError(
                "TABLE_NAME_DUPLICATE",
                "Record-count table names must be unique.",
            )

        normalized_names.add(normalized)

        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
        ):
            raise RecoveryContractError(
                "RECORD_COUNT_INVALID",
                "Record counts must be nonnegative integers.",
            )

    ordered = sorted(
        copied,
        key=lambda item: (item[0].casefold(), item[0]),
    )
    tables = [table for table, _ in ordered]
    counts = {
        table: count
        for table, count in ordered
    }

    return tables, counts


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value

    return result


def _reject_nonstandard_number(value: str) -> None:
    raise _NonStandardJsonNumberError(value)


def parse_backup_manifest(
    value: str | bytes,
) -> BackupManifest:
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RecoveryContractError(
                "MANIFEST_ENCODING_INVALID",
                "Backup manifest must use valid UTF-8.",
            ) from error
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError("Backup manifest input must be text or bytes.")

    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_number,
        )
    except _DuplicateJsonKeyError as error:
        raise RecoveryContractError(
            "MANIFEST_DUPLICATE_KEY",
            "Backup manifest contains a duplicate JSON key.",
        ) from error
    except _NonStandardJsonNumberError as error:
        raise RecoveryContractError(
            "MANIFEST_JSON_INVALID",
            "Backup manifest contains a nonstandard JSON number.",
        ) from error
    except json.JSONDecodeError as error:
        raise RecoveryContractError(
            "MANIFEST_JSON_INVALID",
            "Backup manifest is not valid JSON.",
        ) from error

    try:
        return BackupManifest.model_validate(payload)
    except ValidationError as error:
        raise RecoveryContractError(
            "MANIFEST_SCHEMA_INVALID",
            "Backup manifest does not match the supported schema.",
        ) from error


def classify_database_compatibility(
    source_user_version: int,
    current_user_version: int = CURRENT_DATABASE_SCHEMA_VERSION,
) -> BackupCompatibility:
    if isinstance(source_user_version, bool) or not isinstance(
        source_user_version,
        int,
    ):
        raise TypeError("Source database version must be an integer.")

    if isinstance(current_user_version, bool) or not isinstance(
        current_user_version,
        int,
    ):
        raise TypeError("Current database version must be an integer.")

    if current_user_version < 0:
        raise ValueError("Current database version cannot be negative.")

    if source_user_version < 0:
        status = "unsupported-invalid"
        is_supported = False
        requires_upgrade = False
    elif source_user_version > current_user_version:
        status = "unsupported-future"
        is_supported = False
        requires_upgrade = False
    elif source_user_version < current_user_version:
        status = "upgrade-required"
        is_supported = True
        requires_upgrade = True
    else:
        status = "compatible"
        is_supported = True
        requires_upgrade = False

    return BackupCompatibility(
        status=status,
        source_user_version=source_user_version,
        current_user_version=current_user_version,
        is_supported=is_supported,
        requires_upgrade=requires_upgrade,
    )


def sort_verification_issues(
    issues: Iterable[VerificationIssue],
) -> list[VerificationIssue]:
    copied = list(issues)

    return sorted(
        copied,
        key=lambda issue: (
            _ISSUE_SEVERITY_ORDER[issue.severity],
            issue.code,
            issue.location or "",
            issue.message,
        ),
    )


def build_verification_result(
    issues: Iterable[VerificationIssue],
    *,
    compatibility: BackupCompatibility | None = None,
) -> VerificationResult:
    ordered = sort_verification_issues(issues)
    is_valid = not any(
        issue.severity == "error"
        for issue in ordered
    )

    return VerificationResult(
        is_valid=is_valid,
        issues=ordered,
        compatibility=compatibility,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    try:
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RecoveryContractError(
            "SNAPSHOT_READ_FAILED",
            "Snapshot file could not be read for checksum verification.",
        ) from error

    return digest.hexdigest()


def resolve_sqlite_database_path(database_url: str) -> Path:
    if not isinstance(database_url, str) or not database_url:
        raise TypeError("Database URL must be a nonempty string.")

    try:
        url = make_url(database_url)
    except ArgumentError as error:
        raise RecoveryContractError(
            "DATABASE_URL_INVALID",
            "Configured database URL is invalid.",
        ) from error

    if url.get_backend_name() != "sqlite":
        raise RecoveryContractError(
            "DATABASE_BACKEND_UNSUPPORTED",
            "Backup snapshots currently require a SQLite database.",
        )

    if url.query:
        raise RecoveryContractError(
            "DATABASE_SOURCE_UNSUPPORTED",
            "SQLite database URLs with query parameters are unsupported.",
        )

    database = url.database

    if (
        not database
        or database == ":memory:"
        or database.startswith("file:")
    ):
        raise RecoveryContractError(
            "DATABASE_SOURCE_UNSUPPORTED",
            "Backup snapshots require a filesystem SQLite database.",
        )

    path = Path(database)

    if not path.is_absolute():
        raise RecoveryContractError(
            "DATABASE_SOURCE_PATH_INVALID",
            "SQLite database path must be absolute.",
        )

    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as error:
        raise RecoveryContractError(
            "DATABASE_SOURCE_MISSING",
            "Configured SQLite database file does not exist.",
        ) from error
    except OSError as error:
        raise RecoveryContractError(
            "DATABASE_SOURCE_PATH_INVALID",
            "Configured SQLite database path cannot be resolved.",
        ) from error

    if not resolved.is_file():
        raise RecoveryContractError(
            "DATABASE_SOURCE_PATH_INVALID",
            "Configured SQLite database path is not a regular file.",
        )

    return resolved


def _validate_snapshot_destination(
    source_path: Path,
    destination_path: Path,
) -> Path:
    destination = Path(destination_path)

    if not destination.is_absolute():
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_INVALID",
            "Snapshot destination path must be absolute.",
        )

    try:
        resolved_destination = destination.resolve(strict=False)
    except OSError as error:
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_INVALID",
            "Snapshot destination path cannot be resolved.",
        ) from error

    if resolved_destination == source_path:
        raise RecoveryContractError(
            "SNAPSHOT_SOURCE_DESTINATION_CONFLICT",
            "Snapshot destination cannot be the source database.",
        )

    if destination.name != "foreman.db":
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_INVALID",
            "Snapshot destination filename must be foreman.db.",
        )

    parent = destination.parent

    if not parent.exists() or not parent.is_dir():
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_INVALID",
            "Snapshot destination directory must already exist.",
        )

    if destination.exists() or destination.is_symlink():
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_EXISTS",
            "Snapshot destination must not already exist.",
        )

    return destination


def _copy_sqlite_database(
    source_path: Path,
    destination_path: Path,
) -> None:
    source_uri = f"{source_path.as_uri()}?mode=ro"

    with closing(
        sqlite3.connect(source_uri, uri=True)
    ) as source_connection:
        with closing(
            sqlite3.connect(destination_path)
        ) as destination_connection:
            source_connection.backup(destination_connection)


def _quote_sqlite_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _inspect_sqlite_snapshot(
    snapshot_path: Path,
) -> tuple[int, list[str], dict[str, int]]:
    snapshot_uri = f"{snapshot_path.as_uri()}?mode=ro"

    with closing(
        sqlite3.connect(snapshot_uri, uri=True)
    ) as connection:
        integrity_results = [
            str(row[0])
            for row in connection.execute("PRAGMA integrity_check")
        ]

        if integrity_results != ["ok"]:
            raise RecoveryContractError(
                "SNAPSHOT_INTEGRITY_FAILED",
                "SQLite snapshot failed its integrity check.",
            )

        foreign_key_violations = list(
            connection.execute("PRAGMA foreign_key_check")
        )

        if foreign_key_violations:
            raise RecoveryContractError(
                "SNAPSHOT_FOREIGN_KEY_VIOLATIONS",
                "SQLite snapshot contains foreign-key violations.",
            )

        user_version = int(
            connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
        )
        tables = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT GLOB 'sqlite_*'
                ORDER BY name COLLATE NOCASE, name
                """
            )
        ]

        if not tables:
            raise RecoveryContractError(
                "SNAPSHOT_SCHEMA_EMPTY",
                "SQLite snapshot contains no application tables.",
            )

        raw_counts: dict[str, int] = {}

        for table in tables:
            identifier = _quote_sqlite_identifier(table)
            count = connection.execute(
                f"SELECT COUNT(*) FROM {identifier}"
            ).fetchone()[0]
            raw_counts[table] = int(count)

    normalized_tables, record_counts = normalize_table_counts(
        raw_counts
    )
    return user_version, normalized_tables, record_counts


def create_verified_sqlite_snapshot(
    database_url: str,
    destination_path: Path,
) -> VerifiedSqliteSnapshot:
    source_path = resolve_sqlite_database_path(database_url)
    destination = _validate_snapshot_destination(
        source_path,
        Path(destination_path),
    )

    try:
        destination.touch(exist_ok=False)
    except FileExistsError as error:
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_EXISTS",
            "Snapshot destination must not already exist.",
        ) from error
    except OSError as error:
        raise RecoveryContractError(
            "SNAPSHOT_DESTINATION_INVALID",
            "Snapshot destination could not be created.",
        ) from error

    try:
        _copy_sqlite_database(source_path, destination)
        user_version, tables, record_counts = _inspect_sqlite_snapshot(
            destination
        )
        byte_size = destination.stat().st_size

        database_manifest = DatabaseBackupManifest(
            filename="foreman.db",
            byte_size=byte_size,
            sha256=sha256_file(destination),
            user_version=user_version,
            integrity_check="ok",
            foreign_key_violation_count=0,
            tables=tables,
        )

        return VerifiedSqliteSnapshot(
            path=destination.resolve(strict=True),
            database_manifest=database_manifest,
            record_counts=tuple(record_counts.items()),
        )
    except RecoveryContractError:
        destination.unlink(missing_ok=True)
        raise
    except (OSError, sqlite3.Error) as error:
        destination.unlink(missing_ok=True)
        raise RecoveryContractError(
            "SNAPSHOT_CREATION_FAILED",
            "Verified SQLite snapshot could not be created.",
        ) from error
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def backup_package_filename(created_at: datetime) -> str:
    if not isinstance(created_at, datetime):
        raise TypeError("Backup creation time must be a datetime.")

    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise RecoveryContractError(
            "BACKUP_TIMESTAMP_INVALID",
            "Backup creation time must be timezone-aware.",
        )

    if created_at.utcoffset() != timezone.utc.utcoffset(created_at):
        raise RecoveryContractError(
            "BACKUP_TIMESTAMP_INVALID",
            "Backup creation time must use UTC.",
        )

    if created_at.microsecond != 0:
        raise RecoveryContractError(
            "BACKUP_TIMESTAMP_INVALID",
            "Backup creation time must use whole-second precision.",
        )

    if not 1980 <= created_at.year <= 2107:
        raise RecoveryContractError(
            "BACKUP_TIMESTAMP_INVALID",
            "Backup creation time is outside the ZIP timestamp range.",
        )

    return created_at.strftime("foreman-backup-%Y%m%dT%H%M%SZ.zip")


def _resolve_destination_directory(destination_directory: Path) -> Path:
    destination = Path(destination_directory)

    if not destination.is_absolute():
        raise RecoveryContractError(
            "BACKUP_DESTINATION_INVALID",
            "Backup destination directory must be absolute.",
        )

    if destination.is_symlink():
        raise RecoveryContractError(
            "BACKUP_DESTINATION_INVALID",
            "Backup destination directory cannot be a symbolic link.",
        )

    try:
        resolved = destination.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise RecoveryContractError(
            "BACKUP_DESTINATION_INVALID",
            "Backup destination directory cannot be resolved.",
        ) from error

    if not resolved.is_dir():
        raise RecoveryContractError(
            "BACKUP_DESTINATION_INVALID",
            "Backup destination must be an existing directory.",
        )

    return resolved


def _resolve_backup_package_path(package_path: Path) -> Path:
    package = Path(package_path)

    if not package.is_absolute():
        raise RecoveryContractError(
            "BACKUP_PACKAGE_PATH_INVALID",
            "Backup package path must be absolute.",
        )

    if package.is_symlink():
        raise RecoveryContractError(
            "BACKUP_PACKAGE_PATH_INVALID",
            "Backup package cannot be a symbolic link.",
        )

    try:
        resolved = package.resolve(strict=True)
    except FileNotFoundError as error:
        raise RecoveryContractError(
            "BACKUP_PACKAGE_MISSING",
            "Backup package does not exist.",
        ) from error
    except OSError as error:
        raise RecoveryContractError(
            "BACKUP_PACKAGE_PATH_INVALID",
            "Backup package path cannot be resolved.",
        ) from error

    if not resolved.is_file():
        raise RecoveryContractError(
            "BACKUP_PACKAGE_PATH_INVALID",
            "Backup package path is not a regular file.",
        )

    try:
        package_size = resolved.stat().st_size
    except OSError as error:
        raise RecoveryContractError(
            "BACKUP_PACKAGE_READ_FAILED",
            "Backup package metadata could not be read.",
        ) from error

    if package_size <= 0 or package_size > MAX_BACKUP_PACKAGE_BYTES:
        raise RecoveryContractError(
            "BACKUP_PACKAGE_SIZE_INVALID",
            "Backup package size is outside supported limits.",
        )

    return resolved


def _zip_member_file_type(member: zipfile.ZipInfo) -> int:
    mode = member.external_attr >> 16
    return stat.S_IFMT(mode)


def _validate_zip_member(member: zipfile.ZipInfo) -> None:
    _validate_member_name(member.filename)
    file_type = _zip_member_file_type(member)

    if (
        member.is_dir()
        or file_type not in {0, stat.S_IFREG}
    ):
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_TYPE_INVALID",
            "Backup archive members must be regular files.",
            location=member.filename,
        )

    if member.flag_bits & 0x1:
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_ENCRYPTED",
            "Encrypted backup archive members are unsupported.",
            location=member.filename,
        )

    if member.compress_type not in {
        zipfile.ZIP_STORED,
        zipfile.ZIP_DEFLATED,
    }:
        raise RecoveryContractError(
            "ARCHIVE_COMPRESSION_UNSUPPORTED",
            "Backup archive uses an unsupported compression method.",
            location=member.filename,
        )

    maximum_size = (
        MAX_MANIFEST_BYTES
        if member.filename == "manifest.json"
        else MAX_DATABASE_BYTES
    )

    if member.file_size <= 0 or member.file_size > maximum_size:
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_SIZE_INVALID",
            "Backup archive member size is outside supported limits.",
            location=member.filename,
        )


def _read_zip_member_limited(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    maximum_size: int,
) -> bytes:
    try:
        with archive.open(member, "r") as source:
            data = source.read(maximum_size + 1)
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_READ_FAILED",
            "Backup archive member could not be read.",
            location=member.filename,
        ) from error

    if len(data) > maximum_size:
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_SIZE_INVALID",
            "Backup archive member exceeds supported limits.",
            location=member.filename,
        )

    return data


def _extract_database_member(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    destination_path: Path,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0

    try:
        with archive.open(member, "r") as source:
            with destination_path.open("xb") as destination:
                while True:
                    chunk = source.read(1024 * 1024)

                    if not chunk:
                        break

                    total += len(chunk)

                    if total > MAX_DATABASE_BYTES:
                        raise RecoveryContractError(
                            "ARCHIVE_MEMBER_SIZE_INVALID",
                            "Backup database exceeds supported limits.",
                            location="foreman.db",
                        )

                    destination.write(chunk)
                    digest.update(chunk)
    except RecoveryContractError:
        destination_path.unlink(missing_ok=True)
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        destination_path.unlink(missing_ok=True)
        raise RecoveryContractError(
            "ARCHIVE_MEMBER_READ_FAILED",
            "Backup database could not be extracted for verification.",
            location="foreman.db",
        ) from error

    return total, digest.hexdigest()


def _issue_from_contract_error(
    error: RecoveryContractError,
) -> VerificationIssue:
    return VerificationIssue(
        code=error.code,
        message=str(error),
        location=error.location,
    )


def verify_backup_package(
    package_path: Path,
) -> BackupPackageVerification:
    input_path = Path(package_path)
    manifest: BackupManifest | None = None
    compatibility: BackupCompatibility | None = None

    try:
        resolved_package = _resolve_backup_package_path(input_path)

        try:
            archive_context = zipfile.ZipFile(resolved_package, "r")
        except (OSError, zipfile.BadZipFile) as error:
            raise RecoveryContractError(
                "BACKUP_ARCHIVE_INVALID",
                "Backup package is not a readable ZIP archive.",
            ) from error

        with archive_context as archive:
            members = archive.infolist()
            validate_archive_member_names(
                member.filename
                for member in members
            )

            for member in members:
                _validate_zip_member(member)

            members_by_name = {
                member.filename: member
                for member in members
            }
            manifest_member = members_by_name["manifest.json"]
            database_member = members_by_name["foreman.db"]
            manifest_bytes = _read_zip_member_limited(
                archive,
                manifest_member,
                MAX_MANIFEST_BYTES,
            )
            manifest = parse_backup_manifest(manifest_bytes)

            if canonical_json_bytes(manifest) != manifest_bytes:
                raise RecoveryContractError(
                    "MANIFEST_NOT_CANONICAL",
                    "Backup manifest is not canonical JSON.",
                    location="manifest.json",
                )

            issues: list[VerificationIssue] = []

            with TemporaryDirectory(
                prefix="foreman-backup-verification-"
            ) as temporary_directory:
                extracted_database = (
                    Path(temporary_directory) / "foreman.db"
                )
                actual_size, actual_checksum = (
                    _extract_database_member(
                        archive,
                        database_member,
                        extracted_database,
                    )
                )

                if actual_size != database_member.file_size:
                    issues.append(
                        VerificationIssue(
                            code="ARCHIVE_MEMBER_SIZE_MISMATCH",
                            message=(
                                "Extracted database size does not match "
                                "the ZIP member metadata."
                            ),
                            location="foreman.db",
                        )
                    )

                if actual_size != manifest.database.byte_size:
                    issues.append(
                        VerificationIssue(
                            code="DATABASE_SIZE_MISMATCH",
                            message=(
                                "Extracted database size does not match "
                                "the manifest."
                            ),
                            location="foreman.db",
                        )
                    )

                if actual_checksum != manifest.database.sha256:
                    issues.append(
                        VerificationIssue(
                            code="DATABASE_CHECKSUM_MISMATCH",
                            message=(
                                "Backup database checksum does not match "
                                "the manifest."
                            ),
                            location="foreman.db",
                        )
                    )

                try:
                    (
                        actual_user_version,
                        actual_tables,
                        actual_record_counts,
                    ) = _inspect_sqlite_snapshot(extracted_database)
                except RecoveryContractError as error:
                    issues.append(_issue_from_contract_error(error))
                except sqlite3.Error:
                    issues.append(
                        VerificationIssue(
                            code="BACKUP_DATABASE_INVALID",
                            message=(
                                "Backup database could not be opened "
                                "as SQLite."
                            ),
                            location="foreman.db",
                        )
                    )
                else:
                    if actual_user_version != manifest.database.user_version:
                        issues.append(
                            VerificationIssue(
                                code="DATABASE_VERSION_MISMATCH",
                                message=(
                                    "Backup database schema version does "
                                    "not match the manifest."
                                ),
                                location="foreman.db",
                            )
                        )

                    if actual_tables != manifest.database.tables:
                        issues.append(
                            VerificationIssue(
                                code="DATABASE_TABLES_MISMATCH",
                                message=(
                                    "Backup database table inventory does "
                                    "not match the manifest."
                                ),
                                location="foreman.db",
                            )
                        )

                    if actual_record_counts != manifest.record_counts:
                        issues.append(
                            VerificationIssue(
                                code="DATABASE_RECORD_COUNTS_MISMATCH",
                                message=(
                                    "Backup database record counts do not "
                                    "match the manifest."
                                ),
                                location="foreman.db",
                            )
                        )

                    if (
                        actual_user_version
                        == CURRENT_DATABASE_SCHEMA_VERSION
                        and not CURRENT_REQUIRED_DATABASE_TABLES.issubset(
                            actual_tables
                        )
                    ):
                        issues.append(
                            VerificationIssue(
                                code="DATABASE_REQUIRED_TABLES_MISSING",
                                message=(
                                    "Backup database is missing required "
                                    "application tables."
                                ),
                                location="foreman.db",
                            )
                        )

                    compatibility = classify_database_compatibility(
                        actual_user_version
                    )

                    if compatibility.status == "unsupported-future":
                        issues.append(
                            VerificationIssue(
                                code="DATABASE_VERSION_UNSUPPORTED",
                                message=(
                                    "Backup database is newer than this "
                                    "application supports."
                                ),
                                location="foreman.db",
                            )
                        )
                    elif compatibility.status == "unsupported-invalid":
                        issues.append(
                            VerificationIssue(
                                code="DATABASE_VERSION_INVALID",
                                message=(
                                    "Backup database schema version is "
                                    "invalid."
                                ),
                                location="foreman.db",
                            )
                        )
                    elif compatibility.status == "upgrade-required":
                        issues.append(
                            VerificationIssue(
                                severity="warning",
                                code="DATABASE_UPGRADE_REQUIRED",
                                message=(
                                    "Backup database requires a supported "
                                    "schema upgrade before activation."
                                ),
                                location="foreman.db",
                            )
                        )

        return BackupPackageVerification(
            package_path=resolved_package,
            manifest=manifest,
            result=build_verification_result(
                issues,
                compatibility=compatibility,
            ),
        )
    except RecoveryContractError as error:
        return BackupPackageVerification(
            package_path=input_path,
            manifest=manifest,
            result=build_verification_result(
                [_issue_from_contract_error(error)],
                compatibility=compatibility,
            ),
        )
    except (OSError, sqlite3.Error, zipfile.BadZipFile):
        issue = VerificationIssue(
            code="BACKUP_PACKAGE_READ_FAILED",
            message="Backup package could not be verified.",
        )
        return BackupPackageVerification(
            package_path=input_path,
            manifest=manifest,
            result=build_verification_result(
                [issue],
                compatibility=compatibility,
            ),
        )


def _sqlite_sidecar_paths(database_path: Path) -> tuple[Path, ...]:
    return tuple(
        Path(f"{database_path}{suffix}")
        for suffix in ("-journal", "-wal", "-shm")
    )


def _remove_restore_candidate_artifacts(
    candidate_path: Path,
) -> None:
    candidate_path.unlink(missing_ok=True)

    for sidecar in _sqlite_sidecar_paths(candidate_path):
        sidecar.unlink(missing_ok=True)


def _validate_restore_candidate_destination(
    destination_path: Path,
    live_database_url: str,
) -> Path:
    destination = Path(destination_path)

    if not destination.is_absolute():
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate destination must be absolute.",
        )

    if destination.is_symlink():
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate cannot be a symbolic link.",
        )

    parent = destination.parent

    if parent.is_symlink():
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate directory cannot be a symbolic link.",
        )

    try:
        resolved_parent = parent.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate directory cannot be resolved.",
        ) from error

    if not resolved_parent.is_dir():
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate directory must already exist.",
        )

    resolved_destination = resolved_parent / destination.name
    live_database_path = resolve_sqlite_database_path(
        live_database_url
    )

    if resolved_destination == live_database_path:
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_LIVE_DATABASE_CONFLICT",
            "Restore candidate cannot use the live database path.",
        )

    if destination.name != "foreman.db":
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate filename must be foreman.db.",
        )

    if (
        resolved_destination.exists()
        or resolved_destination.is_symlink()
    ):
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_EXISTS",
            "Restore candidate destination must not already exist.",
        )

    return resolved_destination


def _extract_restore_candidate(
    package_path: Path,
    destination_path: Path,
) -> tuple[int, str]:
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            members = archive.infolist()
            validate_archive_member_names(
                member.filename
                for member in members
            )

            for member in members:
                _validate_zip_member(member)

            member = {
                item.filename: item
                for item in members
            }["foreman.db"]
            size, checksum = _extract_database_member(
                archive,
                member,
                destination_path,
            )
    except RecoveryContractError:
        raise
    except (
        KeyError,
        OSError,
        RuntimeError,
        zipfile.BadZipFile,
    ) as error:
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_EXTRACTION_FAILED",
            "Restore candidate database could not be extracted.",
        ) from error

    try:
        destination_path.chmod(0o600)
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DESTINATION_INVALID",
            "Restore candidate permissions could not be secured.",
        ) from error

    return size, checksum


def _normalize_restore_candidate_journal(
    candidate_path: Path,
) -> None:
    try:
        with closing(sqlite3.connect(candidate_path)) as connection:
            mode = connection.execute(
                "PRAGMA journal_mode=DELETE"
            ).fetchone()

            if (
                mode is None
                or str(mode[0]).lower() != "delete"
            ):
                raise RecoveryContractError(
                    "RESTORE_CANDIDATE_JOURNAL_INVALID",
                    "Restore candidate journal mode could not be normalized.",
                )
    except RecoveryContractError:
        raise
    except sqlite3.Error as error:
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_JOURNAL_INVALID",
            "Restore candidate journal mode could not be normalized.",
        ) from error


def _prepare_restore_candidate_schema(
    candidate_path: Path,
) -> None:
    import app.models  # noqa: F401

    engine = create_engine(
        f"sqlite:///{candidate_path}",
        connect_args={"check_same_thread": False},
    )

    try:
        with engine.connect() as connection:
            prepare_database_schema(connection)
    finally:
        engine.dispose()


def _verify_restore_candidate_model_schema(
    candidate_path: Path,
) -> None:
    import app.models  # noqa: F401

    engine = create_engine(
        f"sqlite:///{candidate_path}",
        connect_args={"check_same_thread": False},
    )

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            database_inspector = inspect(connection)
            actual_tables = set(
                database_inspector.get_table_names()
            )
            expected_tables = set(Base.metadata.tables)

            if actual_tables != expected_tables:
                raise RecoveryContractError(
                    "RESTORE_CANDIDATE_SCHEMA_INVALID",
                    "Restore candidate table inventory does not match "
                    "the application schema.",
                )

            for table_name in sorted(expected_tables):
                model_table = Base.metadata.tables[table_name]
                expected_columns = {
                    column.name
                    for column in model_table.columns
                }
                actual_columns = {
                    column["name"]
                    for column in (
                        database_inspector.get_columns(table_name)
                    )
                }

                if actual_columns != expected_columns:
                    raise RecoveryContractError(
                        "RESTORE_CANDIDATE_SCHEMA_INVALID",
                        "Restore candidate columns do not match "
                        "the application schema.",
                        location=table_name,
                    )

                expected_primary_key = {
                    column.name
                    for column in model_table.primary_key.columns
                }
                actual_primary_key = set(
                    database_inspector.get_pk_constraint(
                        table_name
                    ).get("constrained_columns")
                    or []
                )

                if actual_primary_key != expected_primary_key:
                    raise RecoveryContractError(
                        "RESTORE_CANDIDATE_SCHEMA_INVALID",
                        "Restore candidate primary key does not match "
                        "the application schema.",
                        location=table_name,
                    )
    finally:
        engine.dispose()


def _validate_staged_record_counts(
    source_manifest: BackupManifest,
    staged_tables: list[str],
    staged_record_counts: dict[str, int],
    *,
    candidate_path: Path,
    source_had_default_space: bool,
) -> None:
    source_counts = source_manifest.record_counts
    default_space_delta = 0 if source_had_default_space else 1

    for table, expected_count in source_counts.items():
        if table == "spaces":
            expected_count += default_space_delta

        if staged_record_counts.get(table) != expected_count:
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_RECORD_COUNT_MISMATCH",
                "Restore candidate did not preserve source records.",
                location=table,
            )

    new_tables = set(staged_tables) - set(source_counts)

    for table in sorted(new_tables):
        expected_count = (
            default_space_delta if table == "spaces" else 0
        )

        if staged_record_counts[table] != expected_count:
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_NEW_TABLE_NOT_EMPTY",
                "New restore candidate tables contain unexpected records.",
                location=table,
            )

    if default_space_delta:
        with closing(sqlite3.connect(candidate_path)) as connection:
            default_space = connection.execute(
                "SELECT name, description FROM spaces WHERE id = ?",
                (DEFAULT_SPACE_ID,),
            ).fetchone()

        if default_space != (
            DEFAULT_SPACE_NAME,
            DEFAULT_SPACE_DESCRIPTION,
        ):
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_DEFAULT_SPACE_INVALID",
                "Restore candidate did not add the exact default Space.",
                location="spaces",
            )


def _database_has_default_space(database_path: Path) -> bool:
    with closing(sqlite3.connect(database_path)) as connection:
        spaces_table = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'spaces'"
        ).fetchone()

        if spaces_table is None:
            return False

        return connection.execute(
            "SELECT 1 FROM spaces WHERE id = ?",
            (DEFAULT_SPACE_ID,),
        ).fetchone() is not None


def stage_restore_candidate(
    package_path: Path,
    destination_path: Path,
    *,
    live_database_url: str,
) -> StagedRestoreCandidate:
    verification = verify_backup_package(Path(package_path))

    if (
        not verification.result.is_valid
        or verification.manifest is None
        or verification.result.compatibility is None
        or not verification.result.compatibility.is_supported
    ):
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_PACKAGE_INVALID",
            "Backup package is not eligible for restore staging.",
        )

    source_manifest = verification.manifest
    compatibility = verification.result.compatibility
    destination = _validate_restore_candidate_destination(
        Path(destination_path),
        live_database_url,
    )

    try:
        extracted_size, extracted_checksum = (
            _extract_restore_candidate(
                verification.package_path,
                destination,
            )
        )
        source_version, source_tables, source_counts = (
            _inspect_sqlite_snapshot(destination)
        )

        if (
            extracted_size
            != source_manifest.database.byte_size
            or extracted_checksum
            != source_manifest.database.sha256
            or source_version
            != source_manifest.database.user_version
            or source_tables
            != source_manifest.database.tables
            or source_counts
            != source_manifest.record_counts
        ):
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_SOURCE_MISMATCH",
                "Extracted restore candidate does not match "
                "the verified package manifest.",
            )

        source_database_checksum = sha256_file(destination)
        source_had_default_space = _database_has_default_space(
            destination
        )
        _normalize_restore_candidate_journal(destination)
        _prepare_restore_candidate_schema(destination)

        if (
            not compatibility.requires_upgrade
            and sha256_file(destination)
            != source_database_checksum
        ):
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_CURRENT_SCHEMA_CHANGED",
                "A current-schema backup required unexpected changes.",
            )

        for sidecar in _sqlite_sidecar_paths(destination):
            if sidecar.exists():
                raise RecoveryContractError(
                    "RESTORE_CANDIDATE_SIDECAR_PRESENT",
                    "Restore candidate has uncommitted SQLite sidecar data.",
                )

        (
            staged_user_version,
            staged_tables,
            staged_record_counts,
        ) = _inspect_sqlite_snapshot(destination)

        if staged_user_version != CURRENT_DATABASE_SCHEMA_VERSION:
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_VERSION_INVALID",
                "Restore candidate did not reach the current schema version.",
            )

        if not CURRENT_REQUIRED_DATABASE_TABLES.issubset(
            staged_tables
        ):
            raise RecoveryContractError(
                "RESTORE_CANDIDATE_REQUIRED_TABLES_MISSING",
                "Restore candidate is missing required application tables.",
            )

        _verify_restore_candidate_model_schema(destination)
        _validate_staged_record_counts(
            source_manifest,
            staged_tables,
            staged_record_counts,
            candidate_path=destination,
            source_had_default_space=source_had_default_space,
        )

        byte_size = destination.stat().st_size
        database_manifest = DatabaseBackupManifest(
            filename="foreman.db",
            byte_size=byte_size,
            sha256=sha256_file(destination),
            user_version=staged_user_version,
            integrity_check="ok",
            foreign_key_violation_count=0,
            tables=staged_tables,
        )

        return StagedRestoreCandidate(
            path=destination.resolve(strict=True),
            source_manifest=source_manifest,
            database_manifest=database_manifest,
            record_counts=tuple(
                staged_record_counts.items()
            ),
            was_upgraded=compatibility.requires_upgrade,
        )
    except RecoveryContractError:
        _remove_restore_candidate_artifacts(destination)
        raise
    except DefaultSpaceConflictError as error:
        _remove_restore_candidate_artifacts(destination)
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_DEFAULT_SPACE_CONFLICT",
            str(error),
            location="spaces",
        ) from error
    except (
        OSError,
        RuntimeError,
        sqlite3.Error,
        SQLAlchemyError,
        zipfile.BadZipFile,
    ) as error:
        _remove_restore_candidate_artifacts(destination)
        raise RecoveryContractError(
            "RESTORE_CANDIDATE_STAGING_FAILED",
            "Restore candidate could not be prepared.",
        ) from error
    except Exception:
        _remove_restore_candidate_artifacts(destination)
        raise

def _zip_info(name: str, created_at: datetime) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(
        filename=name,
        date_time=(
            created_at.year,
            created_at.month,
            created_at.day,
            created_at.hour,
            created_at.minute,
            created_at.second,
        ),
    )
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    return info


def _write_backup_archive(
    package_path: Path,
    manifest_bytes: bytes,
    snapshot_path: Path,
    created_at: datetime,
) -> None:
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise RecoveryContractError(
            "MANIFEST_SIZE_INVALID",
            "Backup manifest exceeds supported limits.",
        )

    try:
        with zipfile.ZipFile(
            package_path,
            mode="x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.writestr(
                _zip_info("manifest.json", created_at),
                manifest_bytes,
            )

            database_info = _zip_info("foreman.db", created_at)

            with snapshot_path.open("rb") as source:
                with archive.open(database_info, "w") as destination:
                    while True:
                        chunk = source.read(1024 * 1024)

                        if not chunk:
                            break

                        destination.write(chunk)
    except FileExistsError as error:
        raise RecoveryContractError(
            "BACKUP_TEMPORARY_PACKAGE_EXISTS",
            "Temporary backup package already exists.",
        ) from error
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        package_path.unlink(missing_ok=True)
        raise RecoveryContractError(
            "BACKUP_PACKAGE_CREATION_FAILED",
            "Backup ZIP package could not be created.",
        ) from error


def _publish_verified_package(
    temporary_package: Path,
    destination_path: Path,
) -> None:
    reserved = False

    try:
        destination_path.touch(mode=0o600, exist_ok=False)
        reserved = True
        os.replace(temporary_package, destination_path)
    except FileExistsError as error:
        raise RecoveryContractError(
            "BACKUP_DESTINATION_EXISTS",
            "Backup destination already exists.",
        ) from error
    except OSError as error:
        if reserved:
            destination_path.unlink(missing_ok=True)
        raise RecoveryContractError(
            "BACKUP_PUBLISH_FAILED",
            "Verified backup package could not be published.",
        ) from error


def create_verified_backup_package(
    database_url: str,
    destination_directory: Path,
    *,
    application_name: str,
    application_version: str,
    operational_fact_schema_version: int,
    created_at: datetime | None = None,
) -> VerifiedBackupPackage:
    creation_time = (
        created_at
        if created_at is not None
        else datetime.now(timezone.utc).replace(microsecond=0)
    )
    filename = backup_package_filename(creation_time)
    destination = _resolve_destination_directory(
        Path(destination_directory)
    )
    final_path = destination / filename

    if final_path.exists() or final_path.is_symlink():
        raise RecoveryContractError(
            "BACKUP_DESTINATION_EXISTS",
            "Backup destination already exists.",
        )

    published = False

    try:
        with TemporaryDirectory(
            prefix=".foreman-backup-",
            dir=destination,
        ) as temporary_directory:
            work_directory = Path(temporary_directory)
            snapshot = create_verified_sqlite_snapshot(
                database_url,
                work_directory / "foreman.db",
            )
            manifest = BackupManifest(
                backup_format_version=BACKUP_FORMAT_VERSION,
                application_name=application_name,
                application_version=application_version,
                created_at=creation_time,
                operational_fact_schema_version=(
                    operational_fact_schema_version
                ),
                database=snapshot.database_manifest,
                record_counts=snapshot.record_count_mapping(),
            )
            manifest_bytes = canonical_json_bytes(manifest)
            temporary_package = work_directory / filename
            _write_backup_archive(
                temporary_package,
                manifest_bytes,
                snapshot.path,
                creation_time,
            )
            temporary_verification = verify_backup_package(
                temporary_package
            )

            if not temporary_verification.result.is_valid:
                raise RecoveryContractError(
                    "BACKUP_PACKAGE_VERIFICATION_FAILED",
                    "New backup package failed independent verification.",
                )

            _publish_verified_package(
                temporary_package,
                final_path,
            )
            published = True

        final_verification = verify_backup_package(final_path)

        if not final_verification.result.is_valid:
            final_path.unlink(missing_ok=True)
            published = False
            raise RecoveryContractError(
                "BACKUP_PACKAGE_VERIFICATION_FAILED",
                "Published backup package failed final verification.",
            )

        if final_verification.manifest != manifest:
            final_path.unlink(missing_ok=True)
            published = False
            raise RecoveryContractError(
                "BACKUP_MANIFEST_MISMATCH",
                "Published backup manifest changed during creation.",
            )

        return VerifiedBackupPackage(
            path=final_path.resolve(strict=True),
            manifest=manifest,
            verification=final_verification.result,
        )
    except RecoveryContractError:
        if published:
            final_path.unlink(missing_ok=True)
        raise
    except Exception:
        if published:
            final_path.unlink(missing_ok=True)
        raise

RECOVERY_DIRECTORY_NAME = "recovery"
SAFETY_BACKUP_DIRECTORY_NAME = "safety-backups"


def _ensure_private_recovery_directory(
    path: Path,
    *,
    error_code: str,
) -> Path:
    directory = Path(path)

    if directory.is_symlink():
        raise RecoveryContractError(
            error_code,
            "Recovery directory cannot be a symbolic link.",
        )

    try:
        directory.mkdir(mode=0o700, exist_ok=True)

        if directory.is_symlink() or not directory.is_dir():
            raise RecoveryContractError(
                error_code,
                "Recovery path must be a private directory.",
            )

        directory.chmod(0o700)
        return directory.resolve(strict=True)
    except RecoveryContractError:
        raise
    except (FileNotFoundError, OSError) as error:
        raise RecoveryContractError(
            error_code,
            "Recovery directory could not be prepared.",
        ) from error


def _paths_share_device(first: Path, second: Path) -> bool:
    try:
        return first.stat().st_dev == second.stat().st_dev
    except OSError as error:
        raise RecoveryContractError(
            "RECOVERY_WORKSPACE_INVALID",
            "Recovery filesystem could not be inspected.",
        ) from error


def _fsync_file(path: Path) -> None:
    try:
        with path.open("rb") as file:
            os.fsync(file.fileno())
    except OSError as error:
        raise RecoveryContractError(
            "SAFETY_BACKUP_DURABILITY_FAILED",
            "Safety backup file could not be synchronized.",
        ) from error


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY

    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    descriptor: int | None = None

    try:
        descriptor = os.open(path, flags)
        os.fsync(descriptor)
    except OSError as error:
        raise RecoveryContractError(
            "SAFETY_BACKUP_DURABILITY_FAILED",
            "Safety backup directory could not be synchronized.",
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def create_pre_restore_safety_backup(
    database_url: str,
    *,
    application_name: str,
    application_version: str,
    operational_fact_schema_version: int,
    created_at: datetime | None = None,
) -> VerifiedBackupPackage:
    live_database_path = resolve_sqlite_database_path(database_url)
    recovery_directory = _ensure_private_recovery_directory(
        live_database_path.parent / RECOVERY_DIRECTORY_NAME,
        error_code="RECOVERY_WORKSPACE_INVALID",
    )
    safety_backup_directory = _ensure_private_recovery_directory(
        recovery_directory / SAFETY_BACKUP_DIRECTORY_NAME,
        error_code="SAFETY_BACKUP_DIRECTORY_INVALID",
    )

    if not _paths_share_device(
        live_database_path,
        safety_backup_directory,
    ):
        raise RecoveryContractError(
            "RECOVERY_WORKSPACE_FILESYSTEM_MISMATCH",
            "Safety backup must use the live database filesystem.",
        )

    package: VerifiedBackupPackage | None = None

    try:
        package = create_verified_backup_package(
            database_url,
            safety_backup_directory,
            application_name=application_name,
            application_version=application_version,
            operational_fact_schema_version=(
                operational_fact_schema_version
            ),
            created_at=created_at,
        )
        package.path.chmod(0o600)
        _fsync_file(package.path)
        _fsync_directory(safety_backup_directory)
        _fsync_directory(recovery_directory)

        durable_verification = verify_backup_package(package.path)

        if (
            not durable_verification.result.is_valid
            or durable_verification.manifest != package.manifest
        ):
            raise RecoveryContractError(
                "SAFETY_BACKUP_VERIFICATION_FAILED",
                "Durable safety backup failed final verification.",
            )

        return VerifiedBackupPackage(
            path=package.path,
            manifest=package.manifest,
            verification=durable_verification.result,
        )
    except RecoveryContractError:
        if package is not None:
            package.path.unlink(missing_ok=True)
        raise
    except OSError as error:
        if package is not None:
            package.path.unlink(missing_ok=True)
        raise RecoveryContractError(
            "SAFETY_BACKUP_DURABILITY_FAILED",
            "Safety backup could not be made durable.",
        ) from error
    except Exception:
        if package is not None:
            package.path.unlink(missing_ok=True)
        raise

ACTIVATION_DIRECTORY_NAME = "activation"


class RestoreActivationError(RecoveryContractError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        safety_backup_path: Path,
        rollback_succeeded: bool,
        emergency_latched: bool,
    ) -> None:
        super().__init__(code, message)
        self.safety_backup_path = Path(safety_backup_path)
        self.rollback_succeeded = rollback_succeeded
        self.emergency_latched = emergency_latched


@dataclass(frozen=True)
class RestoreActivationResult:
    database_path: Path
    safety_backup_path: Path
    record_counts: tuple[tuple[str, int], ...]
    operational_fact_count: int

    def record_count_mapping(self) -> dict[str, int]:
        return dict(self.record_counts)


def _assert_no_sqlite_sidecars(
    database_path: Path,
    *,
    code: str,
    message: str,
) -> None:
    if any(path.exists() for path in _sqlite_sidecar_paths(database_path)):
        raise RecoveryContractError(code, message)


def _validate_staged_candidate_for_activation(
    staged_candidate: StagedRestoreCandidate,
    live_database_path: Path,
) -> Path:
    candidate_path = Path(staged_candidate.path)

    if candidate_path.is_symlink():
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_CANDIDATE_INVALID",
            "Restore activation candidate cannot be a symbolic link.",
        )

    try:
        candidate = candidate_path.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_CANDIDATE_INVALID",
            "Restore activation candidate cannot be resolved.",
        ) from error

    if not candidate.is_file() or candidate == live_database_path:
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_CANDIDATE_INVALID",
            "Restore activation candidate must be an isolated database.",
        )

    try:
        same_device = (
            candidate.stat().st_dev
            == live_database_path.parent.stat().st_dev
        )
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_CANDIDATE_INVALID",
            "Restore activation filesystem could not be inspected.",
        ) from error

    if not same_device:
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_FILESYSTEM_MISMATCH",
            "Restore candidate must use the live database filesystem.",
        )

    _assert_no_sqlite_sidecars(
        candidate,
        code="RESTORE_ACTIVATION_CANDIDATE_SIDECAR_PRESENT",
        message="Restore activation candidate has SQLite sidecars.",
    )
    user_version, tables, record_counts = _inspect_sqlite_snapshot(
        candidate
    )
    manifest = staged_candidate.database_manifest

    if (
        candidate.stat().st_size != manifest.byte_size
        or sha256_file(candidate) != manifest.sha256
        or user_version != manifest.user_version
        or tables != manifest.tables
        or record_counts != staged_candidate.record_count_mapping()
    ):
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_CANDIDATE_CHANGED",
            "Restore activation candidate changed after staging.",
        )

    _verify_restore_candidate_model_schema(candidate)
    return candidate


def _prepare_activation_workspace(live_database_path: Path) -> Path:
    recovery_directory = _ensure_private_recovery_directory(
        live_database_path.parent / RECOVERY_DIRECTORY_NAME,
        error_code="RECOVERY_WORKSPACE_INVALID",
    )
    activation_root = _ensure_private_recovery_directory(
        recovery_directory / ACTIVATION_DIRECTORY_NAME,
        error_code="RESTORE_ACTIVATION_WORKSPACE_INVALID",
    )

    try:
        workspace = Path(
            mkdtemp(
                prefix=".restore-",
                dir=activation_root,
            )
        )
        workspace.chmod(0o700)
        return workspace.resolve(strict=True)
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_WORKSPACE_INVALID",
            "Restore activation workspace could not be prepared.",
        ) from error


def _remove_live_database_sidecars(database_path: Path) -> None:
    try:
        for sidecar in _sqlite_sidecar_paths(database_path):
            sidecar.unlink(missing_ok=True)
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_DATABASE_SIDECAR_CLEANUP_FAILED",
            "SQLite sidecars could not be removed during recovery.",
        ) from error


def _synchronize_database_replacement(
    database_path: Path,
    *,
    code: str,
    message: str,
) -> None:
    try:
        database_path.chmod(0o600)

        with database_path.open("rb") as file:
            os.fsync(file.fileno())

        flags = os.O_RDONLY

        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY

        descriptor = os.open(database_path.parent, flags)

        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise RecoveryContractError(code, message) from error


def _verify_activated_database(
    database_path: Path,
    *,
    expected_manifest: DatabaseBackupManifest,
    expected_record_counts: Mapping[str, int],
) -> int:
    checksum_before = sha256_file(database_path)
    verification_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    operational_fact_count = 0

    try:
        with verification_engine.connect() as connection:
            prepare_database_schema(connection)

        with verification_engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")

            if connection.execute(text("SELECT 1")).scalar_one() != 1:
                raise RecoveryContractError(
                    "RESTORE_ACTIVATION_HEALTH_FAILED",
                    "Activated database failed its health probe.",
                )

        session_factory = sessionmaker(
            bind=verification_engine,
            autoflush=False,
            autocommit=False,
        )

        with session_factory() as session:
            default_space = session.get(
                Space,
                DEFAULT_SPACE_ID,
            )

            if default_space is None:
                raise RecoveryContractError(
                    "RESTORE_ACTIVATION_HEALTH_FAILED",
                    "Activated database is missing the default Space.",
                )

            operational_fact_count = len(
                get_operational_facts(
                    session,
                    default_space,
                ).facts
            )
    finally:
        verification_engine.dispose()

    _assert_no_sqlite_sidecars(
        database_path,
        code="RESTORE_ACTIVATION_SIDECAR_PRESENT",
        message="Activated database retained SQLite sidecars.",
    )
    checksum_after = sha256_file(database_path)

    if checksum_after != checksum_before:
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_UNEXPECTED_CHANGE",
            "Activated current-schema database changed during verification.",
        )

    user_version, tables, record_counts = _inspect_sqlite_snapshot(
        database_path
    )

    if (
        user_version != expected_manifest.user_version
        or tables != expected_manifest.tables
        or record_counts != dict(expected_record_counts)
        or database_path.stat().st_size != expected_manifest.byte_size
        or checksum_after != expected_manifest.sha256
    ):
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_VERIFICATION_FAILED",
            "Activated database does not match the staged candidate.",
        )

    if not CURRENT_REQUIRED_DATABASE_TABLES.issubset(tables):
        raise RecoveryContractError(
            "RESTORE_ACTIVATION_REQUIRED_TABLES_MISSING",
            "Activated database is missing required application tables.",
        )

    _verify_restore_candidate_model_schema(database_path)
    return operational_fact_count


def activate_staged_restore(
    staged_candidate: StagedRestoreCandidate,
    *,
    live_database_url: str,
    application_name: str,
    application_version: str,
    operational_fact_schema_version: int,
    maintenance_timeout_seconds: float | None = None,
    safety_backup_created_at: datetime | None = None,
) -> RestoreActivationResult:
    live_database_path = resolve_sqlite_database_path(
        live_database_url
    )
    candidate_path = _validate_staged_candidate_for_activation(
        staged_candidate,
        live_database_path,
    )
    safety_backup: VerifiedBackupPackage | None = None
    activation_workspace: Path | None = None
    rollback_candidate: StagedRestoreCandidate | None = None

    with database_maintenance(
        timeout_seconds=maintenance_timeout_seconds,
    ) as maintenance:
        candidate_path = _validate_staged_candidate_for_activation(
            staged_candidate,
            live_database_path,
        )
        _assert_no_sqlite_sidecars(
            live_database_path,
            code="RESTORE_LIVE_DATABASE_SIDECAR_PRESENT",
            message=(
                "Live database has SQLite sidecars after maintenance drain."
            ),
        )
        safety_backup = create_pre_restore_safety_backup(
            live_database_url,
            application_name=application_name,
            application_version=application_version,
            operational_fact_schema_version=(
                operational_fact_schema_version
            ),
            created_at=safety_backup_created_at,
        )
        activation_workspace = _prepare_activation_workspace(
            live_database_path
        )

        try:
            rollback_candidate = stage_restore_candidate(
                safety_backup.path,
                activation_workspace / "foreman.db",
                live_database_url=live_database_url,
            )
            activation_applied = False

            try:
                try:
                    os.replace(candidate_path, live_database_path)
                except OSError as error:
                    raise RecoveryContractError(
                        "RESTORE_ACTIVATION_REPLACEMENT_FAILED",
                        "Restore candidate could not replace the live database.",
                    ) from error

                activation_applied = True
                _synchronize_database_replacement(
                    live_database_path,
                    code="RESTORE_ACTIVATION_DURABILITY_FAILED",
                    message=(
                        "Activated database could not be synchronized."
                    ),
                )
                operational_fact_count = _verify_activated_database(
                    live_database_path,
                    expected_manifest=(
                        staged_candidate.database_manifest
                    ),
                    expected_record_counts=(
                        staged_candidate.record_count_mapping()
                    ),
                )
            except Exception as activation_error:
                if not activation_applied:
                    raise

                try:
                    _remove_live_database_sidecars(live_database_path)
                    os.replace(
                        rollback_candidate.path,
                        live_database_path,
                    )
                    _synchronize_database_replacement(
                        live_database_path,
                        code="RESTORE_ROLLBACK_DURABILITY_FAILED",
                        message=(
                            "Rollback database could not be synchronized."
                        ),
                    )
                    _verify_activated_database(
                        live_database_path,
                        expected_manifest=(
                            rollback_candidate.database_manifest
                        ),
                        expected_record_counts=(
                            rollback_candidate.record_count_mapping()
                        ),
                    )
                except Exception as rollback_error:
                    maintenance.latch_emergency()
                    raise RestoreActivationError(
                        "RESTORE_ACTIVATION_AND_ROLLBACK_FAILED",
                        (
                            "Restore activation and automatic rollback "
                            "both failed. Database access remains disabled. "
                            "Use the retained safety backup for emergency "
                            "recovery."
                        ),
                        safety_backup_path=safety_backup.path,
                        rollback_succeeded=False,
                        emergency_latched=True,
                    ) from rollback_error

                raise RestoreActivationError(
                    "RESTORE_ACTIVATION_FAILED_ROLLED_BACK",
                    (
                        "Restore activation failed and the original "
                        "database was restored successfully."
                    ),
                    safety_backup_path=safety_backup.path,
                    rollback_succeeded=True,
                    emergency_latched=False,
                ) from activation_error

            return RestoreActivationResult(
                database_path=live_database_path,
                safety_backup_path=safety_backup.path,
                record_counts=tuple(
                    staged_candidate.record_count_mapping().items()
                ),
                operational_fact_count=operational_fact_count,
            )
        finally:
            state = maintenance.snapshot()

            if (
                activation_workspace is not None
                and not state.emergency_latched
            ):
                shutil.rmtree(
                    activation_workspace,
                    ignore_errors=True,
                )
