import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from app.core.config import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    DATABASE_URL,
)
from app.schemas.recovery import BackupVerificationResponse
from app.services.recovery import (
    MAX_BACKUP_PACKAGE_BYTES,
    RecoveryContractError,
    create_verified_backup_package,
    verify_backup_package,
)


router = APIRouter(prefix="/api", tags=["recovery"])
logger = logging.getLogger(__name__)

OPERATIONAL_FACT_SCHEMA_VERSION = 1
BACKUP_MEDIA_TYPE = "application/zip"


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
            "Backup verification requires an application/zip request.",
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


@router.post(
    "/recovery/backups",
    response_class=FileResponse,
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
        total_bytes = 0

        with uploaded_package.open("xb") as destination:
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

                destination.write(chunk)

        if total_bytes == 0:
            raise _backup_upload_error(
                status.HTTP_400_BAD_REQUEST,
                "BACKUP_UPLOAD_EMPTY",
                "Backup upload is empty.",
            )

        verification = verify_backup_package(uploaded_package)
        response.headers["Cache-Control"] = "no-store"

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
