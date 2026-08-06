import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import func, select

from app.core.database import SessionLocal, engine, initialize_database
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.project import Project
from app.models.project_material_requirement import (
    ProjectMaterialRequirement,
)
from app.models.project_migration import ProjectMigration
from app.schemas.project_migration import BrowserProjectMigrationRequest
from app.services.project_migrations import migrate_browser_project
from test_support import ApiTestCase


def migration_payload(
    source_record_id: str,
    *,
    name: str = "Migrated Project",
    materials: list[dict] | None = None,
) -> dict:
    return {
        "sourceRecordId": source_record_id,
        "name": name,
        "type": "build",
        "status": "active",
        "priority": "high",
        "progress": 42.5,
        "startDate": "2026-07-01",
        "targetDate": "2026-08-15",
        "estimatedCost": 125.75,
        "description": "Browser Project",
        "notes": "Preserve this Project",
        "materials": materials or [],
        "createdAt": "2026-07-01T12:00:00Z",
        "updatedAt": "2026-07-02T13:30:00Z",
    }


class ProjectMigrationTests(ApiTestCase):
    async def create_inventory(self, name: str = "Steel") -> dict:
        response = await self.client.post(
            "/api/inventory",
            json={
                "name": name,
                "category": "metal",
                "quantity": 10,
                "unit": "ft",
                "minimum": 1,
                "location": "Rack",
                "cost": 4,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def database_counts(self) -> tuple[int, int, int]:
        with SessionLocal() as session:
            return (
                session.scalar(
                    select(func.count()).select_from(Project)
                ),
                session.scalar(
                    select(func.count()).select_from(
                        ProjectMaterialRequirement
                    )
                ),
                session.scalar(
                    select(func.count()).select_from(ProjectMigration)
                ),
            )

    async def test_valid_project_and_requirements_migrate_atomically(
        self,
    ) -> None:
        inventory = await self.create_inventory()
        payload = migration_payload(
            "legacy-project-1",
            materials=[
                {
                    "inventoryItemId": inventory["id"],
                    "requiredQuantity": 2.5,
                    "note": "Cut to length",
                }
            ],
        )

        response = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertNotIn("spaceId", result)
        self.assertEqual(result["migrationStatus"], "migrated")
        self.assertEqual(
            result["sourceRecordId"],
            payload["sourceRecordId"],
        )
        self.assertNotEqual(result["id"], payload["sourceRecordId"])
        self.assertEqual(len(result["materials"]), 1)
        self.assertEqual(self.database_counts(), (1, 1, 1))

        with SessionLocal() as session:
            provenance = session.scalar(select(ProjectMigration))
            project = session.scalar(select(Project))
            self.assertEqual(provenance.project_id, result["id"])
            self.assertEqual(len(provenance.payload_hash), 64)
            self.assertEqual(project.space_id, DEFAULT_SPACE_ID)
            self.assertEqual(provenance.space_id, DEFAULT_SPACE_ID)
            self.assertEqual(provenance.space_id, project.space_id)

    async def test_space_context_is_not_accepted(self) -> None:
        payload = migration_payload("legacy-scoped-project")
        payload["spaceId"] = "client-space"

        response = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)

    async def test_retry_returns_original_without_duplicates(self) -> None:
        inventory = await self.create_inventory()
        payload = migration_payload(
            "legacy-project-2",
            materials=[
                {
                    "inventoryItemId": inventory["id"],
                    "requiredQuantity": 3,
                }
            ],
        )
        first = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        # Treat the first response as interrupted and retry using only the
        # durable legacy source identity.
        retry = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(
            retry.json()["migrationStatus"],
            "already-migrated",
        )
        self.assertEqual(retry.json()["id"], first.json()["id"])
        self.assertEqual(len(retry.json()["materials"]), 1)
        self.assertEqual(self.database_counts(), (1, 1, 1))

    async def test_different_sources_may_have_identical_projects(self) -> None:
        first_payload = migration_payload("legacy-identical-1")
        second_payload = migration_payload("legacy-identical-2")

        first = await self.client.post(
            "/api/project-migrations/browser",
            json=first_payload,
        )
        second = await self.client.post(
            "/api/project-migrations/browser",
            json=second_payload,
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(self.database_counts(), (2, 0, 2))

    async def test_conflicting_retry_is_rejected(self) -> None:
        payload = migration_payload("legacy-conflict")
        await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )
        conflicting = {
            **payload,
            "name": "Changed after migration",
        }

        response = await self.client.post(
            "/api/project-migrations/browser",
            json=conflicting,
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("different Project data", response.json()["detail"])
        self.assertEqual(self.database_counts(), (1, 0, 1))

    async def test_missing_inventory_rejects_everything(self) -> None:
        payload = migration_payload(
            "legacy-missing-inventory",
            materials=[
                {
                    "inventoryItemId": "missing-inventory",
                    "requiredQuantity": 1,
                }
            ],
        )

        response = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Inventory item not found.",
        )
        self.assertEqual(self.database_counts(), (0, 0, 0))

    async def test_transaction_failure_rolls_back_all_state(self) -> None:
        data = BrowserProjectMigrationRequest.model_validate(
            migration_payload("legacy-rollback")
        )

        with SessionLocal() as session:
            with patch.object(
                session,
                "commit",
                side_effect=RuntimeError("forced migration failure"),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "forced migration failure",
                ):
                    migrate_browser_project(session, data)

        self.assertEqual(self.database_counts(), (0, 0, 0))

    async def test_near_concurrent_retries_create_one_project(self) -> None:
        payload = migration_payload("legacy-concurrent")

        first, second = await asyncio.gather(
            self.client.post(
                "/api/project-migrations/browser",
                json=payload,
            ),
            self.client.post(
                "/api/project-migrations/browser",
                json=payload,
            ),
        )

        self.assertEqual(
            sorted((first.status_code, second.status_code)),
            [200, 201],
        )
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(self.database_counts(), (1, 0, 1))

    async def test_provenance_survives_database_restart(self) -> None:
        payload = migration_payload("legacy-restart")
        first = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        engine.dispose()
        initialize_database()

        retry = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["id"], first.json()["id"])
        self.assertEqual(self.database_counts(), (1, 0, 1))

    async def test_deleted_migration_is_a_permanent_tombstone(self) -> None:
        payload = migration_payload("legacy-deleted")
        migrated = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )
        project_id = migrated.json()["id"]

        deleted = await self.client.delete(f"/api/projects/{project_id}")
        retry = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(retry.status_code, 410)
        self.assertIn("deleted", retry.json()["detail"])
        self.assertEqual(self.database_counts(), (0, 0, 1))

    async def test_archived_migrated_project_remains_compatible(self) -> None:
        payload = migration_payload("legacy-archived")
        migrated = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )
        project_id = migrated.json()["id"]

        archived = await self.client.post(
            f"/api/projects/{project_id}/archive"
        )
        retry = await self.client.post(
            "/api/project-migrations/browser",
            json=payload,
        )

        self.assertEqual(archived.status_code, 200)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["status"], "archived")
        self.assertEqual(
            retry.json()["migrationStatus"],
            "already-migrated",
        )

    async def test_normal_creation_still_generates_backend_id(self) -> None:
        normal = await self.client.post(
            "/api/projects",
            json={"name": "Normal Project"},
        )

        self.assertEqual(normal.status_code, 201)
        self.assertTrue(normal.json()["id"])
        self.assertEqual(self.database_counts(), (1, 0, 0))
