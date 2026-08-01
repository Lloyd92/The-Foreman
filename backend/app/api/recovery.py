import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from app.core.config import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    DATABASE_URL,
)
from app.core.database import get_database_access
from app.core.maintenance import (
    DatabaseMaintenanceConflict,
    DatabaseMaintenanceDrainTimeout,
    DatabaseMaintenanceEmergencyLatched,
)
from app.schemas.recovery import (
    BackupVerificationResponse,
    RestoreActivationResponse,
    RestorePreflightConfirmation,
    RestorePreflightSummary,
)
from app.services.recovery import (
    MAX_BACKUP_PACKAGE_BYTES,
    RecoveryContractError,
    RestoreActivationError,
    activate_staged_restore,
    create_verified_backup_package,
    verify_backup_package,
)
from app.services.restore_preflight import (
    consume_restore_preflight,
    create_restore_preflight,
    remove_restore_preflight,
)


router = APIRouter(prefix="/api", tags=["recovery"])
logger = logging.getLogger(__name__)

OPERATIONAL_FACT_SCHEMA_VERSION = 1
BACKUP_MEDIA_TYPE = "application/zip"
RESTORE_MAINTENANCE_TIMEOUT_SECONDS = 30.0


def _cleanup_temporary_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _backup_creation_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "BACKUP_CREATION_UNAVAILABLE",
            "message": "A verified backup could not be created.",
        },
    )


def _backup_upload_error(
    status_code: int,
    code: str,
    message: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
        },
        headers={"Cache-Control": "no-store"},
    )


def _restore_error(
    status_code: int,
    code: str,
    message: str,
    **details: object,
) -> HTTPException:
    detail: dict[str, object] = {
        "code": code,
        "message": message,
    }
    detail.update(details)

    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={"Cache-Control": "no-store"},
    )


def _preflight_contract_error(
    error: RecoveryContractError,
) -> HTTPException:
    if error.code == "RESTORE_PREFLIGHT_PACKAGE_INVALID":
        return _restore_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error.code,
            "The backup package is not eligible for restore.",
        )

    return _restore_error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "RESTORE_PREFLIGHT_UNAVAILABLE",
        "The restore preflight could not be prepared.",
    )


def _activation_contract_error(
    error: RecoveryContractError,
) -> HTTPException:
    if error.code == "RESTORE_PREFLIGHT_NOT_FOUND":
        return _restore_error(
            status.HTTP_404_NOT_FOUND,
            error.code,
            "The restore preflight session was not found.",
        )

    if error.code == "RESTORE_PREFLIGHT_EXPIRED":
        return _restore_error(
            status.HTTP_410_GONE,
            error.code,
            "The restore preflight session has expired.",
        )

    if error.code in {
        "RESTORE_PREFLIGHT_CONFIRMATION_REQUIRED",
        "RESTORE_PREFLIGHT_CONSUMED",
        "RESTORE_PREFLIGHT_CHANGED",
        "RESTORE_ACTIVATION_CANDIDATE_CHANGED",
        "RESTORE_ACTIVATION_CANDIDATE_INVALID",
        "RESTORE_ACTIVATION_CANDIDATE_NOT_ISOLATED",
        "RESTORE_ACTIVATION_FILESYSTEM_MISMATCH",
    }:
        messages = {
            "RESTORE_PREFLIGHT_CONFIRMATION_REQUIRED": (
                "Exact restore confirmation is required."
            ),
            "RESTORE_PREFLIGHT_CONSUMED": (
                "The restore preflight session has already been consumed."
            ),
        }
        return _restore_error(
            status.HTTP_409_CONFLICT,
            error.code,
            messages.get(
                error.code,
                "The prepared restore candidate is no longer valid.",
            ),
        )

    return _restore_error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "RESTORE_ACTIVATION_UNAVAILABLE",
        "The restore could not be activated.",
    )


def _activation_failure_error(
    error: RestoreActivationError,
) -> HTTPException:
    if error.emergency_latched:
        return _restore_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error.code,
            (
                "Restore activation and automatic rollback failed. "
                "Database access remains disabled. Use the retained "
                "safety backup for emergency recovery."
            ),
            rollbackSucceeded=False,
            emergencyLatched=True,
        )

    return _restore_error(
        status.HTTP_409_CONFLICT,
        error.code,
        (
            "Restore activation failed, and the original database "
            "was restored successfully."
        ),
        rollbackSucceeded=True,
        emergencyLatched=False,
    )


def _best_effort_remove_preflight(token: str) -> None:
    try:
        remove_restore_preflight(
            token,
            live_database_url=DATABASE_URL,
        )
    except Exception:
        logger.exception(
            "Consumed restore preflight cleanup failed."
        )


def _validate_backup_upload_request(request: Request) -> None:
    content_type = (
        request.headers.get("content-type", "")
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    if content_type != BACKUP_MEDIA_TYPE:
        raise _backup_upload_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "BACKUP_UPLOAD_MEDIA_TYPE_UNSUPPORTED",
            "Backup upload requires an application/zip request.",
        )

    declared_length = request.headers.get("content-length")

    if declared_length is None:
        return

    try:
        length = int(declared_length)
    except ValueError:
        raise _backup_upload_error(
            status.HTTP_400_BAD_REQUEST,
            "BACKUP_UPLOAD_LENGTH_INVALID",
            "Backup upload length is invalid.",
        ) from None

    if length <= 0:
        raise _backup_upload_error(
            status.HTTP_400_BAD_REQUEST,
            "BACKUP_UPLOAD_EMPTY",
            "Backup upload is empty.",
        )

    if length > MAX_BACKUP_PACKAGE_BYTES:
        raise _backup_upload_error(
            413,
            "BACKUP_UPLOAD_TOO_LARGE",
            "Backup upload exceeds supported limits.",
        )


async def _store_backup_upload(
    request: Request,
    destination: Path,
) -> None:
    total_bytes = 0

    with destination.open("xb") as file:
        async for chunk in request.stream():
            if not chunk:
                continue

            total_bytes += len(chunk)

            if total_bytes > MAX_BACKUP_PACKAGE_BYTES:
                raise _backup_upload_error(
                    413,
                    "BACKUP_UPLOAD_TOO_LARGE",
                    "Backup upload exceeds supported limits.",
                )

            file.write(chunk)

    if total_bytes == 0:
        raise _backup_upload_error(
            status.HTTP_400_BAD_REQUEST,
            "BACKUP_UPLOAD_EMPTY",
            "Backup upload is empty.",
        )


@router.post(
    "/recovery/backups",
    response_class=FileResponse,
    dependencies=[Depends(get_database_access)],
)
def create_backup_download() -> FileResponse:
    try:
        temporary_directory = Path(
            tempfile.mkdtemp(prefix="foreman-backup-download-")
        )
    except OSError:
        logger.exception("Backup temporary directory creation failed.")
        raise _backup_creation_unavailable() from None

    try:
        package = create_verified_backup_package(
            DATABASE_URL,
            temporary_directory,
            application_name=APPLICATION_NAME,
            application_version=APPLICATION_VERSION,
            operational_fact_schema_version=(
                OPERATIONAL_FACT_SCHEMA_VERSION
            ),
        )
    except (RecoveryContractError, OSError):
        _cleanup_temporary_directory(temporary_directory)
        logger.exception("Verified backup package creation failed.")
        raise _backup_creation_unavailable() from None
    except Exception:
        _cleanup_temporary_directory(temporary_directory)
        raise

    return FileResponse(
        path=package.path,
        media_type=BACKUP_MEDIA_TYPE,
        filename=package.path.name,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
        background=BackgroundTask(
            _cleanup_temporary_directory,
            temporary_directory,
        ),
    )


@router.post(
    "/recovery/backups/verify",
    response_model=BackupVerificationResponse,
)
async def verify_backup_upload(
    request: Request,
    response: Response,
) -> BackupVerificationResponse:
    _validate_backup_upload_request(request)

    try:
        temporary_directory = Path(
            tempfile.mkdtemp(prefix="foreman-backup-upload-")
        )
    except OSError:
        logger.exception("Backup upload temporary directory failed.")
        raise _backup_upload_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "BACKUP_VERIFICATION_UNAVAILABLE",
            "The backup could not be verified.",
        ) from None

    uploaded_package = temporary_directory / "uploaded-backup.zip"

    try:
        await _store_backup_upload(request, uploaded_package)
        verification = verify_backup_package(uploaded_package)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"

        return BackupVerificationResponse(
            manifest=verification.manifest,
            verification=verification.result,
        )
    except HTTPException:
        raise
    except OSError:
        logger.exception("Backup upload storage failed.")
        raise _backup_upload_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "BACKUP_VERIFICATION_UNAVAILABLE",
            "The backup could not be verified.",
        ) from None
    finally:
        _cleanup_temporary_directory(temporary_directory)


@router.post(
    "/recovery/restores/preflight",
    response_model=RestorePreflightSummary,
    dependencies=[Depends(get_database_access)],
)
async def prepare_restore_preflight(
    request: Request,
    response: Response,
) -> RestorePreflightSummary:
    _validate_backup_upload_request(request)

    try:
        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix="foreman-restore-preflight-upload-"
            )
        )
    except OSError:
        logger.exception(
            "Restore preflight upload directory creation failed."
        )
        raise _restore_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "RESTORE_PREFLIGHT_UNAVAILABLE",
            "The restore preflight could not be prepared.",
        ) from None

    uploaded_package = temporary_directory / "uploaded-backup.zip"

    try:
        await _store_backup_upload(request, uploaded_package)
        session = create_restore_preflight(
            uploaded_package,
            live_database_url=DATABASE_URL,
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return session.summary()
    except HTTPException:
        raise
    except RecoveryContractError as error:
        logger.info(
            "Restore preflight rejected with code %s.",
            error.code,
        )
        raise _preflight_contract_error(error) from None
    except OSError:
        logger.exception("Restore preflight upload storage failed.")
        raise _restore_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "RESTORE_PREFLIGHT_UNAVAILABLE",
            "The restore preflight could not be prepared.",
        ) from None
    finally:
        _cleanup_temporary_directory(temporary_directory)


@router.post(
    "/recovery/restores/activate",
    response_model=RestoreActivationResponse,
)
def activate_restore(
    confirmation: RestorePreflightConfirmation,
    response: Response,
) -> RestoreActivationResponse:
    session = None

    try:
        session = consume_restore_preflight(
            confirmation.token,
            confirmation.confirmation_phrase,
            live_database_url=DATABASE_URL,
        )
        result = activate_staged_restore(
            session.staged_candidate,
            live_database_url=DATABASE_URL,
            application_name=APPLICATION_NAME,
            application_version=APPLICATION_VERSION,
            operational_fact_schema_version=(
                OPERATIONAL_FACT_SCHEMA_VERSION
            ),
            maintenance_timeout_seconds=(
                RESTORE_MAINTENANCE_TIMEOUT_SECONDS
            ),
        )
    except RestoreActivationError as error:
        if not error.emergency_latched:
            _best_effort_remove_preflight(confirmation.token)

        logger.error(
            "Restore activation failed with code %s; rollback=%s; "
            "emergency=%s.",
            error.code,
            error.rollback_succeeded,
            error.emergency_latched,
        )
        raise _activation_failure_error(error) from None
    except DatabaseMaintenanceEmergencyLatched:
        logger.error(
            "Restore activation blocked by emergency maintenance latch."
        )
        raise _restore_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "RESTORE_EMERGENCY_MAINTENANCE_ACTIVE",
            (
                "Database access remains disabled for emergency "
                "recovery. The prepared restore is retained."
            ),
            rollbackSucceeded=False,
            emergencyLatched=True,
        ) from None
    except DatabaseMaintenanceConflict:
        if session is not None:
            _best_effort_remove_preflight(confirmation.token)

        raise _restore_error(
            status.HTTP_409_CONFLICT,
            "RESTORE_MAINTENANCE_CONFLICT",
            "Another database maintenance operation is active.",
        ) from None
    except DatabaseMaintenanceDrainTimeout:
        if session is not None:
            _best_effort_remove_preflight(confirmation.token)

        raise _restore_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "RESTORE_MAINTENANCE_DRAIN_TIMEOUT",
            "Database activity did not drain in time for restore.",
        ) from None
    except RecoveryContractError as error:
        if session is not None:
            _best_effort_remove_preflight(confirmation.token)

        logger.info(
            "Restore activation rejected with code %s.",
            error.code,
        )
        raise _activation_contract_error(error) from None

    _best_effort_remove_preflight(confirmation.token)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"

    return RestoreActivationResponse(
        status="restored",
        record_counts=result.record_count_mapping(),
        operational_fact_count=result.operational_fact_count,
        safety_backup_retained=True,
        reload_required=True,
    )
