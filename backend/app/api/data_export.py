import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.data_export import build_portable_data_export


router = APIRouter(prefix="/api", tags=["exports"])
logger = logging.getLogger(__name__)
SessionDependency = Annotated[Session, Depends(get_session)]

EXPORT_MEDIA_TYPE = "application/json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _portable_export_filename(created_at: datetime) -> str:
    return created_at.strftime(
        "foreman-data-export-%Y%m%dT%H%M%SZ.json"
    )


def _export_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "DATA_EXPORT_UNAVAILABLE",
            "message": "A portable data export could not be created.",
        },
    )


@router.get(
    "/exports/portable-data",
    response_class=Response,
)
def download_portable_data_export(
    session: SessionDependency,
) -> Response:
    created_at = _utc_now()

    try:
        export = build_portable_data_export(
            session,
            created_at=created_at,
        )
        content = (
            export.model_dump_json(
                by_alias=True,
                indent=2,
            )
            + "\n"
        )
    except (SQLAlchemyError, ValidationError):
        logger.exception("Portable data export creation failed.")
        raise _export_unavailable() from None

    return Response(
        content=content,
        media_type=EXPORT_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                'attachment; filename="'
                f"{_portable_export_filename(created_at)}"
                '"'
            ),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
