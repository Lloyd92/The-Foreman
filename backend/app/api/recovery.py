import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from app.core.config import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    DATABASE_URL,
)
from app.services.recovery import (
    RecoveryContractError,
    create_verified_backup_package,
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
