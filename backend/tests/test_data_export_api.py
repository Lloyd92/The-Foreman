from datetime import datetime, timezone
from unittest.mock import ANY, patch

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.data_export import (
    ExportRecordCounts,
    PortableDataExport,
)
from test_support import ApiTestCase


CREATED_AT = datetime(2026, 8, 1, 21, 15, tzinfo=timezone.utc)
EXPORT_FILENAME = "foreman-data-export-20260801T211500Z.json"


def portable_export() -> PortableDataExport:
    return PortableDataExport(
        application_version="0.7.3",
        created_at=CREATED_AT,
        record_counts=ExportRecordCounts(
            projects=0,
            project_material_requirements=0,
            tasks=0,
            inventory_items=0,
        ),
        projects=[],
        tasks=[],
        inventory_items=[],
    )


def invalid_export_error() -> ValidationError:
    try:
        PortableDataExport.model_validate({})
    except ValidationError as error:
        return error

    raise AssertionError("Expected export validation to fail.")


class PortableDataExportApiTests(ApiTestCase):
    async def test_download_returns_deterministic_json_attachment(
        self,
    ) -> None:
        export = portable_export()
        expected_content = (
            export.model_dump_json(
                by_alias=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

        with (
            patch(
                "app.api.data_export._utc_now",
                return_value=CREATED_AT,
            ),
            patch(
                "app.api.data_export.build_portable_data_export",
                return_value=export,
            ) as build_export,
        ):
            response = await self.client.get(
                "/api/exports/portable-data"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, expected_content)
        self.assertEqual(
            response.headers["content-type"],
            "application/json",
        )
        self.assertEqual(
            response.headers["content-disposition"],
            f'attachment; filename="{EXPORT_FILENAME}"',
        )
        self.assertEqual(
            response.headers["cache-control"],
            "no-store",
        )
        self.assertEqual(
            response.headers["x-content-type-options"],
            "nosniff",
        )
        build_export.assert_called_once_with(
            ANY,
            created_at=CREATED_AT,
        )

    async def test_download_uses_one_timestamp_for_name_and_payload(
        self,
    ) -> None:
        with patch(
            "app.api.data_export._utc_now",
            return_value=CREATED_AT,
        ):
            response = await self.client.get(
                "/api/exports/portable-data"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["createdAt"],
            "2026-08-01T21:15:00Z",
        )
        self.assertIn(
            EXPORT_FILENAME,
            response.headers["content-disposition"],
        )
        self.assertFalse(payload["restorable"])
        self.assertEqual(
            payload["artifactType"],
            "portable-data-export",
        )

    async def test_database_failure_is_stable_and_non_sensitive(
        self,
    ) -> None:
        with patch(
            "app.api.data_export.build_portable_data_export",
            side_effect=SQLAlchemyError(
                "Private database path: /data/foreman.db"
            ),
        ):
            response = await self.client.get(
                "/api/exports/portable-data"
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "DATA_EXPORT_UNAVAILABLE",
                    "message": (
                        "A portable data export could not be created."
                    ),
                }
            },
        )
        self.assertNotIn("/data/foreman.db", response.text)

    async def test_validation_failure_is_stable_and_non_sensitive(
        self,
    ) -> None:
        with patch(
            "app.api.data_export.build_portable_data_export",
            side_effect=invalid_export_error(),
        ):
            response = await self.client.get(
                "/api/exports/portable-data"
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"],
            "DATA_EXPORT_UNAVAILABLE",
        )
        self.assertNotIn("Field required", response.text)

    async def test_programmer_error_propagates(self) -> None:
        with patch(
            "app.api.data_export.build_portable_data_export",
            side_effect=RuntimeError("programmer error"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "programmer error",
            ):
                await self.client.get(
                    "/api/exports/portable-data"
                )
