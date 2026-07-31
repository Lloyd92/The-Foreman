from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.schemas.recovery import (
    BackupCompatibility,
    BackupManifest,
    VerificationIssue,
    VerificationResult,
)


EXPECTED_BACKUP_MEMBERS = (
    "manifest.json",
    "foreman.db",
)

_ISSUE_SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
}


class RecoveryContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


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
