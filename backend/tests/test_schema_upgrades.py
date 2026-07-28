import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

from app.core.schema_upgrades import (
    CURRENT_DATABASE_SCHEMA_VERSION,
    apply_schema_upgrades,
    get_database_schema_version,
)
from app.models.base import Base


LEGACY_SCHEMA = """
CREATE TABLE projects (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL,
    progress FLOAT NOT NULL,
    notes TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    archived_at DATETIME
);

CREATE TABLE tasks (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    completed BOOLEAN NOT NULL,
    project_id VARCHAR(36),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
);
"""


class SchemaUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = (
            Path(self.temporary_directory.name) / "schema-upgrade.db"
        )
        self.engine = create_engine(f"sqlite:///{database_path}")

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def create_legacy_database(self) -> None:
        raw_connection = self.engine.raw_connection()

        try:
            raw_connection.executescript(LEGACY_SCHEMA)
            raw_connection.execute(
                """
                INSERT INTO projects (
                    id, name, status, progress, notes,
                    created_at, updated_at, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-project",
                    "Legacy Project",
                    "active",
                    37.5,
                    "Preserve this",
                    "2026-07-01 10:00:00",
                    "2026-07-02 10:00:00",
                    None,
                ),
            )
            raw_connection.execute(
                """
                INSERT INTO projects (
                    id, name, status, progress, notes,
                    created_at, updated_at, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "archived-project",
                    "Archived Project",
                    "archived",
                    100,
                    "Legacy archive",
                    "2026-06-01 10:00:00",
                    "2026-06-02 10:00:00",
                    "2026-06-03 10:00:00",
                ),
            )
            raw_connection.execute(
                """
                INSERT INTO tasks (
                    id, title, priority, completed, project_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-task",
                    "Legacy Task",
                    "high",
                    False,
                    "legacy-project",
                    "2026-07-01 11:00:00",
                    "2026-07-01 11:00:00",
                ),
            )
            raw_connection.commit()
        finally:
            raw_connection.close()

    def run_upgrade(self) -> None:
        import app.models  # noqa: F401

        with self.engine.begin() as connection:
            Base.metadata.create_all(bind=connection)
            apply_schema_upgrades(connection)

    def test_legacy_database_is_preserved_and_upgrade_is_idempotent(
        self,
    ) -> None:
        self.create_legacy_database()
        self.run_upgrade()
        self.run_upgrade()

        with self.engine.connect() as connection:
            project = connection.execute(
                text(
                    """
                    SELECT name, type, status, priority, progress,
                           estimated_cost, description, notes,
                           created_at, updated_at, archived_at
                    FROM projects
                    WHERE id = 'legacy-project'
                    """
                )
            ).mappings().one()
            archived = connection.execute(
                text(
                    """
                    SELECT status, archived_at
                    FROM projects
                    WHERE id = 'archived-project'
                    """
                )
            ).mappings().one()
            task_project_id = connection.execute(
                text(
                    """
                    SELECT project_id FROM tasks
                    WHERE id = 'legacy-task'
                    """
                )
            ).scalar_one()

            self.assertEqual(project["name"], "Legacy Project")
            self.assertEqual(project["type"], "other")
            self.assertEqual(project["status"], "active")
            self.assertEqual(project["priority"], "medium")
            self.assertAlmostEqual(project["progress"], 37.5)
            self.assertEqual(project["estimated_cost"], 0)
            self.assertEqual(project["description"], "")
            self.assertEqual(project["notes"], "Preserve this")
            self.assertEqual(
                str(project["created_at"]),
                "2026-07-01 10:00:00",
            )
            self.assertEqual(
                str(project["updated_at"]),
                "2026-07-02 10:00:00",
            )
            self.assertEqual(archived["status"], "archived")
            self.assertIsNotNone(archived["archived_at"])
            self.assertEqual(task_project_id, "legacy-project")
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

        table_names = set(inspect(self.engine).get_table_names())
        self.assertIn("project_material_requirements", table_names)
        index_names = {
            index["name"]
            for index in inspect(self.engine).get_indexes("projects")
        }
        self.assertIn("ix_projects_type", index_names)
        self.assertIn("ix_projects_priority", index_names)

    def test_fresh_database_reaches_current_schema(self) -> None:
        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

        columns = {
            column["name"]
            for column in inspect(self.engine).get_columns("projects")
        }
        self.assertIn("type", columns)
        self.assertIn("priority", columns)
        self.assertIn("estimated_cost", columns)

    def test_failed_upgrade_retains_version_and_can_resume(self) -> None:
        self.create_legacy_database()

        with self.assertRaises(Exception):
            with self.engine.begin() as connection:
                with patch(
                    "app.core.schema_upgrades.PROJECT_INDEX_UPGRADES",
                    ("THIS IS NOT VALID SQL",),
                ):
                    apply_schema_upgrades(connection)

        columns = {
            column["name"]
            for column in inspect(self.engine).get_columns("projects")
        }

        with self.engine.connect() as connection:
            self.assertEqual(get_database_schema_version(connection), 0)

        # SQLite may retain successful ALTER TABLE statements even when a
        # later DDL statement fails. The schema version must remain unchanged
        # so the idempotent upgrade can safely resume at the next startup.
        self.assertIn("type", columns)
        self.assertIn("priority", columns)

        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
