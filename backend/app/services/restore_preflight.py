from __future__ import annotations

import hmac
import json
import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from app.schemas.recovery import (
    RestorePreflightMetadata,
    RestorePreflightSummary,
)
from app.services.recovery import (
    RECOVERY_DIRECTORY_NAME,
    RecoveryContractError,
    StagedRestoreCandidate,
    _ensure_private_recovery_directory,
    _paths_share_device,
    _validate_staged_candidate_for_activation,
    canonical_json_bytes,
    resolve_sqlite_database_path,
    sha256_file,
    sha256_hex,
    stage_restore_candidate,
    verify_backup_package,
)


PREFLIGHT_DIRECTORY_NAME = "preflight"
PREFLIGHT_METADATA_FILENAME = "preflight.json"
PREFLIGHT_PACKAGE_FILENAME = "uploaded-backup.zip"
PREFLIGHT_CANDIDATE_DIRECTORY_NAME = "candidate"
PREFLIGHT_CLAIM_FILENAME = "consumed"
PREFLIGHT_TTL = timedelta(minutes=15)
RESTORE_CONFIRMATION_PHRASE = "RESTORE THE FOREMAN"
_TOKEN_BYTES = 32
_TOKEN_ATTEMPTS = 8


@dataclass(frozen=True)
class RestorePreflightSession:
    token: str
    workspace_path: Path
    package_path: Path
    staged_candidate: StagedRestoreCandidate
    created_at: datetime
    expires_at: datetime

    def summary(self) -> RestorePreflightSummary:
        return RestorePreflightSummary(
            token=self.token,
            expires_at=self.expires_at,
            confirmation_phrase=RESTORE_CONFIRMATION_PHRASE,
            manifest=self.staged_candidate.source_manifest,
            candidate_database=(
                self.staged_candidate.database_manifest
            ),
            record_counts=(
                self.staged_candidate.record_count_mapping()
            ),
            was_upgraded=self.staged_candidate.was_upgraded,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _validated_now(value: datetime | None) -> datetime:
    current = value if value is not None else _utc_now()

    if (
        current.tzinfo is None
        or current.utcoffset() is None
        or current.utcoffset() != timedelta(0)
        or current.microsecond != 0
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_TIMESTAMP_INVALID",
            "Restore preflight time must be whole-second UTC.",
        )

    return current


def _validate_token(token: str) -> str:
    if (
        not isinstance(token, str)
        or not token
        or len(token) > 255
        or token != token.strip()
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_NOT_FOUND",
            "Restore preflight session was not found.",
        )

    return token


def _token_digest(token: str) -> str:
    return sha256_hex(_validate_token(token).encode("utf-8"))


def _preflight_root(live_database_url: str) -> tuple[Path, Path]:
    live_database_path = resolve_sqlite_database_path(
        live_database_url
    )
    recovery_directory = _ensure_private_recovery_directory(
        live_database_path.parent / RECOVERY_DIRECTORY_NAME,
        error_code="RECOVERY_WORKSPACE_INVALID",
    )
    preflight_directory = _ensure_private_recovery_directory(
        recovery_directory / PREFLIGHT_DIRECTORY_NAME,
        error_code="RESTORE_PREFLIGHT_WORKSPACE_INVALID",
    )

    if not _paths_share_device(
        live_database_path,
        preflight_directory,
    ):
        raise RecoveryContractError(
            "RECOVERY_WORKSPACE_FILESYSTEM_MISMATCH",
            "Restore preflight must use the live database filesystem.",
        )

    return live_database_path, preflight_directory


def _workspace_for_token(
    preflight_directory: Path,
    token: str,
) -> Path:
    return preflight_directory / _token_digest(token)


def _fsync_file(path: Path) -> None:
    try:
        with path.open("rb") as file:
            os.fsync(file.fileno())
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_STORAGE_FAILED",
            "Restore preflight file could not be synchronized.",
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
            "RESTORE_PREFLIGHT_STORAGE_FAILED",
            "Restore preflight directory could not be synchronized.",
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _write_metadata(
    workspace: Path,
    metadata: RestorePreflightMetadata,
) -> Path:
    path = workspace / PREFLIGHT_METADATA_FILENAME
    temporary = workspace / f".{PREFLIGHT_METADATA_FILENAME}.tmp"

    try:
        with temporary.open("xb") as file:
            file.write(canonical_json_bytes(metadata))
            file.write(b"\n")
            file.flush()
            os.fsync(file.fileno())

        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)
        _fsync_directory(workspace)
        return path
    except FileExistsError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_STORAGE_FAILED",
            "Restore preflight metadata already exists.",
        ) from error
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_STORAGE_FAILED",
            "Restore preflight metadata could not be stored.",
        ) from error
    finally:
        temporary.unlink(missing_ok=True)


def _read_metadata(workspace: Path) -> RestorePreflightMetadata:
    path = workspace / PREFLIGHT_METADATA_FILENAME

    if path.is_symlink():
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_INVALID",
            "Restore preflight metadata is invalid.",
        )

    try:
        raw = path.read_bytes()
        metadata = RestorePreflightMetadata.model_validate_json(raw)
    except FileNotFoundError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_NOT_FOUND",
            "Restore preflight session was not found.",
        ) from error
    except (OSError, ValidationError, ValueError, json.JSONDecodeError) as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_INVALID",
            "Restore preflight metadata is invalid.",
        ) from error

    if canonical_json_bytes(metadata) + b"\n" != raw:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_INVALID",
            "Restore preflight metadata is not canonical.",
        )

    return metadata


def _staged_candidate_from_metadata(
    workspace: Path,
    metadata: RestorePreflightMetadata,
) -> StagedRestoreCandidate:
    candidate_path = (
        workspace
        / PREFLIGHT_CANDIDATE_DIRECTORY_NAME
        / "foreman.db"
    )
    return StagedRestoreCandidate(
        path=candidate_path,
        source_manifest=metadata.source_manifest,
        database_manifest=metadata.candidate_database,
        record_counts=tuple(metadata.record_counts.items()),
        was_upgraded=metadata.was_upgraded,
    )


def _validate_workspace(
    workspace: Path,
    preflight_directory: Path,
) -> Path:
    if workspace.is_symlink():
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_INVALID",
            "Restore preflight workspace is invalid.",
        )

    try:
        resolved = workspace.resolve(strict=True)
        root = preflight_directory.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_NOT_FOUND",
            "Restore preflight session was not found.",
        ) from error

    if (
        not resolved.is_dir()
        or resolved.parent != root
        or len(resolved.name) != 64
        or any(character not in "0123456789abcdef" for character in resolved.name)
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_INVALID",
            "Restore preflight workspace is invalid.",
        )

    return resolved


def cleanup_expired_restore_preflights(
    live_database_url: str,
    *,
    now: datetime | None = None,
) -> int:
    current = _validated_now(now)
    _, preflight_directory = _preflight_root(live_database_url)
    removed = 0

    for entry in preflight_directory.iterdir():
        if (
            entry.is_symlink()
            or not entry.is_dir()
            or len(entry.name) != 64
            or any(
                character not in "0123456789abcdef"
                for character in entry.name
            )
        ):
            continue

        try:
            metadata = _read_metadata(entry)
        except RecoveryContractError:
            continue

        if current >= metadata.expires_at:
            shutil.rmtree(entry, ignore_errors=False)
            removed += 1

    if removed:
        _fsync_directory(preflight_directory)

    return removed


def create_restore_preflight(
    package_path: Path,
    *,
    live_database_url: str,
    now: datetime | None = None,
    token_factory: Callable[[int], str] = secrets.token_urlsafe,
) -> RestorePreflightSession:
    current = _validated_now(now)
    live_database_path, preflight_directory = _preflight_root(
        live_database_url
    )
    cleanup_expired_restore_preflights(
        live_database_url,
        now=current,
    )
    source_package = Path(package_path)

    if (
        not source_package.is_absolute()
        or source_package.is_symlink()
        or not source_package.is_file()
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_PACKAGE_INVALID",
            "Restore preflight requires a regular backup package.",
        )

    workspace: Path | None = None
    token = ""

    for _ in range(_TOKEN_ATTEMPTS):
        candidate_token = token_factory(_TOKEN_BYTES)
        digest = _token_digest(candidate_token)
        candidate_workspace = preflight_directory / digest

        try:
            candidate_workspace.mkdir(mode=0o700, exist_ok=False)
        except FileExistsError:
            continue
        except OSError as error:
            raise RecoveryContractError(
                "RESTORE_PREFLIGHT_STORAGE_FAILED",
                "Restore preflight workspace could not be created.",
            ) from error

        workspace = candidate_workspace
        token = candidate_token
        break

    if workspace is None:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_TOKEN_UNAVAILABLE",
            "A unique restore preflight token could not be created.",
        )

    try:
        workspace.chmod(0o700)

        if not _paths_share_device(
            live_database_path,
            workspace,
        ):
            raise RecoveryContractError(
                "RECOVERY_WORKSPACE_FILESYSTEM_MISMATCH",
                "Restore preflight must use the live database filesystem.",
            )

        copied_package = workspace / PREFLIGHT_PACKAGE_FILENAME
        shutil.copyfile(source_package, copied_package)
        copied_package.chmod(0o600)
        _fsync_file(copied_package)

        verification = verify_backup_package(copied_package)

        if (
            not verification.result.is_valid
            or verification.manifest is None
            or verification.result.compatibility is None
            or not verification.result.compatibility.is_supported
        ):
            raise RecoveryContractError(
                "RESTORE_PREFLIGHT_PACKAGE_INVALID",
                "Backup package is not eligible for restore preflight.",
            )

        candidate_directory = (
            workspace / PREFLIGHT_CANDIDATE_DIRECTORY_NAME
        )
        candidate_directory.mkdir(mode=0o700, exist_ok=False)
        candidate_directory.chmod(0o700)
        staged_candidate = stage_restore_candidate(
            copied_package,
            candidate_directory / "foreman.db",
            live_database_url=live_database_url,
        )
        expires_at = current + PREFLIGHT_TTL
        metadata = RestorePreflightMetadata(
            schema_version=1,
            created_at=current,
            expires_at=expires_at,
            source_manifest=staged_candidate.source_manifest,
            candidate_database=(
                staged_candidate.database_manifest
            ),
            record_counts=(
                staged_candidate.record_count_mapping()
            ),
            was_upgraded=staged_candidate.was_upgraded,
            package_sha256=sha256_file(copied_package),
            candidate_sha256=sha256_file(
                staged_candidate.path
            ),
        )
        _write_metadata(workspace, metadata)
        _fsync_directory(candidate_directory)
        _fsync_directory(workspace)
        _fsync_directory(preflight_directory)

        return RestorePreflightSession(
            token=token,
            workspace_path=workspace.resolve(strict=True),
            package_path=copied_package.resolve(strict=True),
            staged_candidate=staged_candidate,
            created_at=current,
            expires_at=expires_at,
        )
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise


def load_restore_preflight(
    token: str,
    *,
    live_database_url: str,
    now: datetime | None = None,
    require_unconsumed: bool = True,
) -> RestorePreflightSession:
    current = _validated_now(now)
    live_database_path, preflight_directory = _preflight_root(
        live_database_url
    )
    workspace = _validate_workspace(
        _workspace_for_token(preflight_directory, token),
        preflight_directory,
    )
    metadata = _read_metadata(workspace)

    if current >= metadata.expires_at:
        shutil.rmtree(workspace, ignore_errors=True)
        _fsync_directory(preflight_directory)
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_EXPIRED",
            "Restore preflight session has expired.",
        )

    claim_path = workspace / PREFLIGHT_CLAIM_FILENAME

    if require_unconsumed and claim_path.exists():
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_CONSUMED",
            "Restore preflight session has already been consumed.",
        )

    package_path = workspace / PREFLIGHT_PACKAGE_FILENAME

    if (
        package_path.is_symlink()
        or not package_path.is_file()
        or sha256_file(package_path) != metadata.package_sha256
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_CHANGED",
            "Restore preflight package changed after preparation.",
        )

    verification = verify_backup_package(package_path)

    if (
        not verification.result.is_valid
        or verification.manifest != metadata.source_manifest
        or verification.result.compatibility is None
        or not verification.result.compatibility.is_supported
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_CHANGED",
            "Restore preflight package changed after preparation.",
        )

    staged_candidate = _staged_candidate_from_metadata(
        workspace,
        metadata,
    )
    _validate_staged_candidate_for_activation(
        staged_candidate,
        live_database_path,
    )

    return RestorePreflightSession(
        token=_validate_token(token),
        workspace_path=workspace,
        package_path=package_path,
        staged_candidate=staged_candidate,
        created_at=metadata.created_at,
        expires_at=metadata.expires_at,
    )


def consume_restore_preflight(
    token: str,
    confirmation_phrase: str,
    *,
    live_database_url: str,
    now: datetime | None = None,
) -> RestorePreflightSession:
    if (
        not isinstance(confirmation_phrase, str)
        or not hmac.compare_digest(
            confirmation_phrase,
            RESTORE_CONFIRMATION_PHRASE,
        )
    ):
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_CONFIRMATION_REQUIRED",
            "Exact restore confirmation is required.",
        )

    current = _validated_now(now)
    session = load_restore_preflight(
        token,
        live_database_url=live_database_url,
        now=current,
        require_unconsumed=True,
    )
    claim_path = (
        session.workspace_path / PREFLIGHT_CLAIM_FILENAME
    )
    descriptor: int | None = None

    try:
        descriptor = os.open(
            claim_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        payload = (
            current.isoformat().replace("+00:00", "Z") + "\n"
        ).encode("ascii")
        os.write(descriptor, payload)
        os.fsync(descriptor)
    except FileExistsError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_CONSUMED",
            "Restore preflight session has already been consumed.",
        ) from error
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_STORAGE_FAILED",
            "Restore preflight consumption could not be recorded.",
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)

    _fsync_directory(session.workspace_path)
    return session


def remove_restore_preflight(
    token: str,
    *,
    live_database_url: str,
) -> None:
    _, preflight_directory = _preflight_root(live_database_url)
    workspace = _workspace_for_token(preflight_directory, token)

    try:
        resolved_parent = workspace.parent.resolve(strict=True)
        root = preflight_directory.resolve(strict=True)
    except OSError as error:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_STORAGE_FAILED",
            "Restore preflight workspace could not be resolved.",
        ) from error

    if resolved_parent != root:
        raise RecoveryContractError(
            "RESTORE_PREFLIGHT_INVALID",
            "Restore preflight workspace is invalid.",
        )

    shutil.rmtree(workspace, ignore_errors=True)
    _fsync_directory(preflight_directory)
