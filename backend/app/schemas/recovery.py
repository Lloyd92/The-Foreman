from datetime import datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel


NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
NonEmptyString = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=255),
]
Sha256Digest = Annotated[
    str,
    Field(strict=True, pattern=r"^[0-9a-f]{64}$"),
]
VerificationCode = Annotated[
    str,
    Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]*$"),
]

CompatibilityStatus = Literal[
    "compatible",
    "upgrade-required",
    "unsupported-future",
    "unsupported-invalid",
]


def _canonical_name(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _validate_table_name(value: str) -> None:
    if (
        value != value.strip()
        or not value
        or value.casefold().startswith("sqlite_")
        or "/" in value
        or "\\" in value
        or "\x00" in value
    ):
        raise ValueError("Table names must be safe non-system names.")


class DatabaseBackupManifest(ApiModel):
    filename: Literal["foreman.db"]
    byte_size: PositiveInt
    sha256: Sha256Digest
    user_version: NonNegativeInt
    integrity_check: Literal["ok"]
    foreign_key_violation_count: Literal[0]
    tables: list[NonEmptyString]

    @field_validator("tables")
    @classmethod
    def validate_tables(
        cls,
        value: list[str],
    ) -> list[str]:
        if not value:
            raise ValueError("At least one database table is required.")

        for table in value:
            _validate_table_name(table)

        normalized = [table.casefold() for table in value]

        if len(set(normalized)) != len(normalized):
            raise ValueError("Database table names must be unique.")

        if value != sorted(value, key=_canonical_name):
            raise ValueError(
                "Database table names must use canonical ordering."
            )

        return value


class BackupManifest(ApiModel):
    backup_format_version: Literal[1]
    application_name: Literal["The Foreman"]
    application_version: NonEmptyString
    created_at: datetime
    operational_fact_schema_version: PositiveInt
    database: DatabaseBackupManifest
    record_counts: dict[NonEmptyString, NonNegativeInt]

    @field_validator("created_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Backup creation time must be timezone-aware.")

        if value.utcoffset() != timedelta(0):
            raise ValueError("Backup creation time must use UTC.")

        return value

    @field_validator("record_counts")
    @classmethod
    def validate_record_count_order(
        cls,
        value: dict[str, int],
    ) -> dict[str, int]:
        if not value:
            raise ValueError("Database record counts are required.")

        for table in value:
            _validate_table_name(table)

        normalized = [table.casefold() for table in value]

        if len(set(normalized)) != len(normalized):
            raise ValueError("Record-count table names must be unique.")

        if list(value) != sorted(value, key=_canonical_name):
            raise ValueError(
                "Record-count keys must use canonical ordering."
            )

        return value

    @model_validator(mode="after")
    def validate_database_record_counts(self) -> Self:
        if list(self.record_counts) != self.database.tables:
            raise ValueError(
                "Record-count keys must match database tables exactly."
            )

        return self


class BackupCompatibility(ApiModel):
    status: CompatibilityStatus
    source_user_version: int = Field(strict=True)
    current_user_version: NonNegativeInt
    is_supported: bool = Field(strict=True)
    requires_upgrade: bool = Field(strict=True)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        expected = {
            "compatible": (
                self.source_user_version
                == self.current_user_version,
                True,
                False,
            ),
            "upgrade-required": (
                0 <= self.source_user_version
                < self.current_user_version,
                True,
                True,
            ),
            "unsupported-future": (
                self.source_user_version
                > self.current_user_version,
                False,
                False,
            ),
            "unsupported-invalid": (
                self.source_user_version < 0,
                False,
                False,
            ),
        }
        condition, supported, upgrade = expected[self.status]

        if not condition:
            raise ValueError(
                "Compatibility status does not match schema versions."
            )

        if (
            self.is_supported is not supported
            or self.requires_upgrade is not upgrade
        ):
            raise ValueError(
                "Compatibility flags do not match compatibility status."
            )

        return self


class VerificationIssue(ApiModel):
    severity: Literal["error", "warning"] = "error"
    code: VerificationCode
    message: NonEmptyString
    location: NonEmptyString | None = None


class VerificationResult(ApiModel):
    is_valid: bool = Field(strict=True)
    issues: list[VerificationIssue] = Field(default_factory=list)
    compatibility: BackupCompatibility | None = None

    @model_validator(mode="after")
    def validate_result_state(self) -> Self:
        has_errors = any(
            issue.severity == "error"
            for issue in self.issues
        )

        if self.is_valid == has_errors:
            raise ValueError(
                "Verification validity must match error issue presence."
            )

        return self


class BackupVerificationResponse(ApiModel):
    manifest: BackupManifest | None = None
    verification: VerificationResult
