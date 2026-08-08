import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import prepare_database_schema
from app.core.default_space import DEFAULT_SPACE_ID
from app.core.schema_upgrades import (
    CURRENT_DATABASE_SCHEMA_VERSION,
    UNIVERSAL_WORK_COLUMN_UPGRADES,
    apply_schema_upgrades,
    get_database_schema_version,
)
from app.models.base import Base
from app.models.member import Member
from app.models.person import Person
from app.models.space import Space
from tests.test_support import create_pre_v4_tables


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

VERSION_TWO_TABLES = (
    "inventory_items",
    "inventory_migrations",
    "projects",
    "project_material_requirements",
    "project_migrations",
    "tasks",
    "task_migrations",
)


VERSION_FOUR_PROJECTS_DDL = """
CREATE TABLE projects (
    id VARCHAR(36) NOT NULL,
    space_id VARCHAR(36) NOT NULL,
    name VARCHAR(120) NOT NULL,
    type VARCHAR(30) DEFAULT 'other' NOT NULL,
    status VARCHAR(20) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium' NOT NULL,
    progress FLOAT NOT NULL,
    start_date DATE,
    target_date DATE,
    estimated_cost FLOAT DEFAULT '0' NOT NULL,
    description TEXT DEFAULT '' NOT NULL,
    notes TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    archived_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT fk_projects_space_id
        FOREIGN KEY(space_id)
        REFERENCES spaces (id)
        ON DELETE RESTRICT
)
"""

VERSION_FOUR_TASKS_DDL = """
CREATE TABLE tasks (
    id VARCHAR(36) NOT NULL,
    space_id VARCHAR(36) NOT NULL,
    title VARCHAR(120) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    completed BOOLEAN NOT NULL,
    project_id VARCHAR(36),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_tasks_space_id
        FOREIGN KEY(space_id)
        REFERENCES spaces (id)
        ON DELETE RESTRICT,
    FOREIGN KEY(project_id)
        REFERENCES projects (id)
        ON DELETE SET NULL
)
"""

VERSION_FOUR_PROJECT_INDEX_DDL = (
    "CREATE INDEX ix_projects_priority ON projects (priority)",
    "CREATE INDEX ix_projects_space_id ON projects (space_id)",
    "CREATE INDEX ix_projects_status ON projects (status)",
    "CREATE INDEX ix_projects_type ON projects (type)",
)

VERSION_FOUR_TASK_INDEX_DDL = (
    "CREATE INDEX ix_tasks_completed ON tasks (completed)",
    "CREATE INDEX ix_tasks_priority ON tasks (priority)",
    "CREATE INDEX ix_tasks_project_id ON tasks (project_id)",
    "CREATE INDEX ix_tasks_space_id ON tasks (space_id)",
)


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

    def create_version_two_database(self) -> None:
        import app.models  # noqa: F401

        timestamp = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

        with self.engine.begin() as connection:
            create_pre_v4_tables(
                connection,
                set(VERSION_TWO_TABLES),
            )

            connection.execute(
                Base.metadata.tables["inventory_items"].insert(),
                {
                    "id": "inventory-v2",
                    "name": "Fastener",
                    "category": "Hardware",
                    "quantity": 10,
                    "unit": "each",
                    "minimum": 2,
                    "location": "Bin",
                    "cost": 1,
                    "supplier": "",
                    "notes": "Preserve inventory",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )
            connection.execute(
                Base.metadata.tables["projects"].insert(),
                {
                    "id": "project-v2",
                    "name": "Version 2 Project",
                    "type": "other",
                    "status": "active",
                    "priority": "medium",
                    "progress": 25,
                    "start_date": None,
                    "target_date": None,
                    "estimated_cost": 0,
                    "description": "",
                    "notes": "Preserve project",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "archived_at": None,
                },
            )
            connection.execute(
                Base.metadata.tables[
                    "project_material_requirements"
                ].insert(),
                {
                    "project_id": "project-v2",
                    "inventory_item_id": "inventory-v2",
                    "required_quantity": 3,
                    "note": "Preserve material",
                },
            )
            connection.execute(
                Base.metadata.tables["tasks"].insert(),
                {
                    "id": "task-v2",
                    "title": "Version 2 Task",
                    "priority": "high",
                    "completed": False,
                    "project_id": "project-v2",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )
            connection.execute(
                Base.metadata.tables["inventory_migrations"].insert(),
                {
                    "source": "browser-local",
                    "source_record_id": "inventory-source-v2",
                    "inventory_item_id": "inventory-v2",
                    "migrated_at": timestamp,
                },
            )
            connection.execute(
                Base.metadata.tables["project_migrations"].insert(),
                {
                    "source": "browser-local",
                    "source_record_id": "project-source-v2",
                    "project_id": "project-v2",
                    "payload_hash": "a" * 64,
                    "migrated_at": timestamp,
                },
            )
            connection.execute(
                Base.metadata.tables["task_migrations"].insert(),
                {
                    "source": "browser-local",
                    "source_record_id": "task-source-v2",
                    "task_id": "task-v2",
                    "migrated_at": timestamp,
                },
            )
            connection.exec_driver_sql("PRAGMA user_version = 2")

    def create_version_four_database(self) -> None:
        import app.models  # noqa: F401

        timestamp = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)

        with self.engine.begin() as connection:
            unchanged_tables = [
                table
                for table in Base.metadata.sorted_tables
                if table.name
                not in {
                    "projects",
                    "tasks",
                    "work_dependencies",
                }
            ]
            Base.metadata.create_all(
                bind=connection,
                tables=unchanged_tables,
            )

            connection.exec_driver_sql(VERSION_FOUR_PROJECTS_DDL)
            connection.exec_driver_sql(VERSION_FOUR_TASKS_DDL)

            for statement in VERSION_FOUR_PROJECT_INDEX_DDL:
                connection.exec_driver_sql(statement)

            for statement in VERSION_FOUR_TASK_INDEX_DDL:
                connection.exec_driver_sql(statement)

            connection.execute(
                Base.metadata.tables["spaces"].insert(),
                {
                    "id": DEFAULT_SPACE_ID,
                    "name": "Household",
                    "description": "Version four fixture",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )

            connection.execute(
                text(
                    """
                    INSERT INTO projects (
                        id,
                        space_id,
                        name,
                        type,
                        status,
                        priority,
                        progress,
                        start_date,
                        target_date,
                        estimated_cost,
                        description,
                        notes,
                        created_at,
                        updated_at,
                        archived_at
                    ) VALUES (
                        :id,
                        :space_id,
                        :name,
                        :type,
                        :status,
                        :priority,
                        :progress,
                        :start_date,
                        :target_date,
                        :estimated_cost,
                        :description,
                        :notes,
                        :created_at,
                        :updated_at,
                        :archived_at
                    )
                    """
                ),
                {
                    "id": "project-v4",
                    "space_id": DEFAULT_SPACE_ID,
                    "name": "Version Four Project",
                    "type": "build",
                    "status": "active",
                    "priority": "high",
                    "progress": 42.5,
                    "start_date": "2026-08-01",
                    "target_date": "2026-09-01",
                    "estimated_cost": 250.0,
                    "description": "Preserve v4 project",
                    "notes": "Historical schema fixture",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "archived_at": None,
                },
            )

            connection.execute(
                text(
                    """
                    INSERT INTO tasks (
                        id,
                        space_id,
                        title,
                        priority,
                        completed,
                        project_id,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :space_id,
                        :title,
                        :priority,
                        :completed,
                        :project_id,
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                {
                    "id": "task-v4",
                    "space_id": DEFAULT_SPACE_ID,
                    "title": "Version Four Task",
                    "priority": "high",
                    "completed": False,
                    "project_id": "project-v4",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )

            connection.exec_driver_sql("PRAGMA user_version = 4")

    def run_upgrade(self) -> None:
        import app.models  # noqa: F401

        with self.engine.connect() as connection:
            prepare_database_schema(connection)

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
        self.assertIn("project_migrations", table_names)
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

        table_names = set(inspect(self.engine).get_table_names())
        self.assertIn("project_migrations", table_names)
        unique_constraints = {
            constraint["name"]
            for constraint in inspect(
                self.engine
            ).get_unique_constraints("project_migrations")
        }
        self.assertIn(
            "uq_project_migration_source_record",
            unique_constraints,
        )

    def test_version_four_database_upgrades_to_universal_work_schema(
        self,
    ) -> None:
        self.create_version_four_database()

        before_inspector = inspect(self.engine)
        self.assertNotIn(
            "responsible_member_id",
            {
                column["name"]
                for column in before_inspector.get_columns("projects")
            },
        )
        self.assertNotIn(
            "due_date",
            {
                column["name"]
                for column in before_inspector.get_columns("tasks")
            },
        )
        self.assertNotIn(
            "responsible_member_id",
            {
                column["name"]
                for column in before_inspector.get_columns("tasks")
            },
        )
        self.assertNotIn(
            "work_dependencies",
            before_inspector.get_table_names(),
        )

        with self.engine.connect() as connection:
            self.assertEqual(get_database_schema_version(connection), 4)

        self.run_upgrade()

        database_inspector = inspect(self.engine)

        project_columns = {
            column["name"]
            for column in database_inspector.get_columns("projects")
        }
        task_columns = {
            column["name"]
            for column in database_inspector.get_columns("tasks")
        }

        self.assertIn("responsible_member_id", project_columns)
        self.assertIn("due_date", task_columns)
        self.assertIn("responsible_member_id", task_columns)
        self.assertIn(
            "work_dependencies",
            database_inspector.get_table_names(),
        )

        project_indexes = {
            index["name"]
            for index in database_inspector.get_indexes("projects")
        }
        task_indexes = {
            index["name"]
            for index in database_inspector.get_indexes("tasks")
        }

        self.assertIn(
            "ix_projects_responsible_member_id",
            project_indexes,
        )
        self.assertIn("ix_tasks_due_date", task_indexes)
        self.assertIn(
            "ix_tasks_responsible_member_id",
            task_indexes,
        )

        with self.engine.connect() as connection:
            project = connection.execute(
                text(
                    """
                    SELECT name, progress, responsible_member_id
                    FROM projects
                    WHERE id = 'project-v4'
                    """
                )
            ).mappings().one()
            task = connection.execute(
                text(
                    """
                    SELECT title, project_id, due_date,
                           responsible_member_id
                    FROM tasks
                    WHERE id = 'task-v4'
                    """
                )
            ).mappings().one()

            self.assertEqual(project["name"], "Version Four Project")
            self.assertAlmostEqual(project["progress"], 42.5)
            self.assertIsNone(project["responsible_member_id"])

            self.assertEqual(task["title"], "Version Four Task")
            self.assertEqual(task["project_id"], "project-v4")
            self.assertIsNone(task["due_date"])
            self.assertIsNone(task["responsible_member_id"])

            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_interrupted_version_five_upgrade_resumes_safely(
        self,
    ) -> None:
        self.create_version_four_database()

        # Simulate a process interruption after only the two Task
        # additions have committed. The schema-version checkpoint must
        # still say 4 because final v5 verification never completed.
        with self.engine.begin() as connection:
            for (
                table_name,
                _column_name,
                statement,
            ) in UNIVERSAL_WORK_COLUMN_UPGRADES[:2]:
                self.assertEqual(table_name, "tasks")
                connection.exec_driver_sql(statement)

            self.assertEqual(
                get_database_schema_version(connection),
                4,
            )

        partial_inspector = inspect(self.engine)
        partial_task_columns = {
            column["name"]
            for column in partial_inspector.get_columns("tasks")
        }
        partial_project_columns = {
            column["name"]
            for column in partial_inspector.get_columns("projects")
        }

        self.assertIn("due_date", partial_task_columns)
        self.assertIn(
            "responsible_member_id",
            partial_task_columns,
        )
        self.assertNotIn(
            "responsible_member_id",
            partial_project_columns,
        )
        self.assertNotIn(
            "work_dependencies",
            partial_inspector.get_table_names(),
        )

        with self.engine.connect() as connection:
            project_before = connection.execute(
                text(
                    """
                    SELECT name, progress
                    FROM projects
                    WHERE id = 'project-v4'
                    """
                )
            ).mappings().one()
            task_before = connection.execute(
                text(
                    """
                    SELECT title, project_id, due_date,
                           responsible_member_id
                    FROM tasks
                    WHERE id = 'task-v4'
                    """
                )
            ).mappings().one()

            self.assertEqual(
                project_before["name"],
                "Version Four Project",
            )
            self.assertAlmostEqual(
                project_before["progress"],
                42.5,
            )
            self.assertEqual(
                task_before["title"],
                "Version Four Task",
            )
            self.assertEqual(
                task_before["project_id"],
                "project-v4",
            )
            self.assertIsNone(task_before["due_date"])
            self.assertIsNone(
                task_before["responsible_member_id"]
            )

        # Normal startup must recognize the approved partial v5 shape,
        # complete the remaining additive work, and checkpoint v5.
        self.run_upgrade()

        completed_inspector = inspect(self.engine)
        project_columns = {
            column["name"]
            for column in completed_inspector.get_columns(
                "projects"
            )
        }
        task_columns = {
            column["name"]
            for column in completed_inspector.get_columns("tasks")
        }

        self.assertIn(
            "responsible_member_id",
            project_columns,
        )
        self.assertIn("due_date", task_columns)
        self.assertIn(
            "responsible_member_id",
            task_columns,
        )
        self.assertIn(
            "work_dependencies",
            completed_inspector.get_table_names(),
        )

        project_indexes = {
            index["name"]
            for index in completed_inspector.get_indexes("projects")
        }
        task_indexes = {
            index["name"]
            for index in completed_inspector.get_indexes("tasks")
        }

        self.assertIn(
            "ix_projects_responsible_member_id",
            project_indexes,
        )
        self.assertIn("ix_tasks_due_date", task_indexes)
        self.assertIn(
            "ix_tasks_responsible_member_id",
            task_indexes,
        )

        def capture_completed_state():
            with self.engine.connect() as connection:
                schema = connection.execute(
                    text(
                        """
                        SELECT type, name, tbl_name, sql
                        FROM sqlite_master
                        WHERE tbl_name IN (
                            'projects',
                            'tasks',
                            'work_dependencies'
                        )
                        AND sql IS NOT NULL
                        ORDER BY type, name
                        """
                    )
                ).all()
                project = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM projects
                        WHERE id = 'project-v4'
                        """
                    )
                ).mappings().one()
                task = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM tasks
                        WHERE id = 'task-v4'
                        """
                    )
                ).mappings().one()

                return (
                    schema,
                    dict(project),
                    dict(task),
                    get_database_schema_version(connection),
                    connection.exec_driver_sql(
                        "PRAGMA foreign_key_check"
                    ).all(),
                )

        completed = capture_completed_state()

        self.assertEqual(
            completed[3],
            CURRENT_DATABASE_SCHEMA_VERSION,
        )
        self.assertEqual(completed[4], [])
        self.assertIsNone(
            completed[1]["responsible_member_id"]
        )
        self.assertIsNone(completed[2]["due_date"])
        self.assertIsNone(
            completed[2]["responsible_member_id"]
        )

        # A second startup after the resumed migration must be a no-op.
        self.run_upgrade()
        restarted = capture_completed_state()

        self.assertEqual(restarted, completed)

    def test_version_five_restart_is_idempotent(self) -> None:
        self.create_version_four_database()
        self.run_upgrade()

        def capture_state():
            with self.engine.connect() as connection:
                schema = connection.execute(
                    text(
                        """
                        SELECT type, name, tbl_name, sql
                        FROM sqlite_master
                        WHERE (
                            tbl_name IN (
                                'projects',
                                'tasks',
                                'work_dependencies'
                            )
                            OR name IN (
                                'projects',
                                'tasks',
                                'work_dependencies'
                            )
                        )
                        AND sql IS NOT NULL
                        ORDER BY type, name
                        """
                    )
                ).all()
                project = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM projects
                        WHERE id = 'project-v4'
                        """
                    )
                ).mappings().one()
                task = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM tasks
                        WHERE id = 'task-v4'
                        """
                    )
                ).mappings().one()

                return (
                    schema,
                    dict(project),
                    dict(task),
                    get_database_schema_version(connection),
                )

        before = capture_state()
        self.run_upgrade()
        after = capture_state()

        self.assertEqual(after, before)
        self.assertEqual(
            after[3],
            CURRENT_DATABASE_SCHEMA_VERSION,
        )

    def test_responsibility_foreign_keys_set_null_on_member_delete(
        self,
    ) -> None:
        self.create_version_four_database()
        self.run_upgrade()

        with Session(self.engine) as session:
            person = Person(display_name="Responsible Person")
            session.add(person)
            session.flush()

            member = Member(
                space_id=DEFAULT_SPACE_ID,
                person_id=person.id,
                role="member",
            )
            session.add(member)
            session.flush()
            member_id = member.id

            session.execute(
                text(
                    """
                    UPDATE projects
                    SET responsible_member_id = :member_id
                    WHERE id = 'project-v4'
                    """
                ),
                {"member_id": member_id},
            )
            session.execute(
                text(
                    """
                    UPDATE tasks
                    SET responsible_member_id = :member_id
                    WHERE id = 'task-v4'
                    """
                ),
                {"member_id": member_id},
            )
            session.commit()

        with Session(self.engine) as session:
            member = session.get(Member, member_id)
            self.assertIsNotNone(member)
            session.delete(member)
            session.commit()

        with self.engine.connect() as connection:
            self.assertIsNone(
                connection.execute(
                    text(
                        """
                        SELECT responsible_member_id
                        FROM projects
                        WHERE id = 'project-v4'
                        """
                    )
                ).scalar_one()
            )
            self.assertIsNone(
                connection.execute(
                    text(
                        """
                        SELECT responsible_member_id
                        FROM tasks
                        WHERE id = 'task-v4'
                        """
                    )
                ).scalar_one()
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_work_dependency_storage_contract(self) -> None:
        self.create_version_four_database()
        self.run_upgrade()

        database_inspector = inspect(self.engine)

        indexes = {
            index["name"]: tuple(index["column_names"])
            for index in database_inspector.get_indexes(
                "work_dependencies"
            )
        }
        self.assertEqual(
            indexes["ix_work_dependencies_space_id"],
            ("space_id",),
        )
        self.assertEqual(
            indexes["ix_work_dependencies_dependent"],
            ("space_id", "dependent_type", "dependent_id"),
        )
        self.assertEqual(
            indexes["ix_work_dependencies_prerequisite"],
            ("space_id", "prerequisite_type", "prerequisite_id"),
        )

        checks = {
            constraint["name"]
            for constraint
            in database_inspector.get_check_constraints(
                "work_dependencies"
            )
        }
        self.assertEqual(
            checks,
            {
                "ck_work_dependencies_dependent_type",
                "ck_work_dependencies_prerequisite_type",
                "ck_work_dependencies_not_self",
            },
        )

        unique_constraints = {
            constraint["name"]
            for constraint
            in database_inspector.get_unique_constraints(
                "work_dependencies"
            )
        }
        self.assertIn(
            "uq_work_dependencies_relationship",
            unique_constraints,
        )

        insert_sql = text(
            """
            INSERT INTO work_dependencies (
                id,
                space_id,
                dependent_type,
                dependent_id,
                prerequisite_type,
                prerequisite_id,
                created_at
            ) VALUES (
                :id,
                :space_id,
                :dependent_type,
                :dependent_id,
                :prerequisite_type,
                :prerequisite_id,
                :created_at
            )
            """
        )
        timestamp = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)

        valid_relationship = {
            "id": "dependency-1",
            "space_id": DEFAULT_SPACE_ID,
            "dependent_type": "task",
            "dependent_id": "task-v4",
            "prerequisite_type": "project",
            "prerequisite_id": "project-v4",
            "created_at": timestamp,
        }

        with self.engine.begin() as connection:
            connection.execute(insert_sql, valid_relationship)

        duplicate = valid_relationship | {"id": "dependency-2"}
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(insert_sql, duplicate)

        self_dependency = valid_relationship | {
            "id": "dependency-self",
            "dependent_type": "task",
            "dependent_id": "task-v4",
            "prerequisite_type": "task",
            "prerequisite_id": "task-v4",
        }
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(insert_sql, self_dependency)

        invalid_type = valid_relationship | {
            "id": "dependency-invalid-type",
            "dependent_type": "goal",
        }
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(insert_sql, invalid_type)

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM work_dependencies"
                    )
                ).scalar_one(),
                1,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_version_two_database_adds_foundation_and_space_ownership(
        self,
    ) -> None:
        self.create_version_two_database()

        with self.engine.connect() as connection:
            version_two_definitions = {
                row.name: row.sql
                for row in connection.execute(
                    text(
                        "SELECT name, sql FROM sqlite_master "
                        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                    )
                )
                if row.name in VERSION_TWO_TABLES
            }

        self.run_upgrade()
        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
            preserved = {
                table_name: connection.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                ).scalar_one()
                for table_name in VERSION_TWO_TABLES
            }
            self.assertEqual(
                preserved,
                {table_name: 1 for table_name in VERSION_TWO_TABLES},
            )
            for table_name in set(VERSION_TWO_TABLES) - {
                "project_material_requirements"
            }:
                self.assertNotEqual(
                    connection.execute(
                        text(
                            "SELECT sql FROM sqlite_master "
                            "WHERE type = 'table' AND name = :name"
                        ),
                        {"name": table_name},
                    ).scalar_one(),
                    version_two_definitions[table_name],
                )
                self.assertEqual(
                    connection.execute(
                        text(
                            f'SELECT COUNT(*) FROM "{table_name}" '
                            "WHERE space_id = :space_id"
                        ),
                        {"space_id": DEFAULT_SPACE_ID},
                    ).scalar_one(),
                    1,
                )

            self.assertEqual(
                connection.execute(
                    text(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type = 'table' "
                        "AND name = 'project_material_requirements'"
                    )
                ).scalar_one(),
                version_two_definitions[
                    "project_material_requirements"
                ],
            )

            for table_name in (
                "people",
                "organizations",
                "organization_space_relationships",
                "members",
                "module_states",
            ):
                self.assertEqual(
                    connection.execute(
                        text(f'SELECT COUNT(*) FROM "{table_name}"')
                    ).scalar_one(),
                    0,
                )

            self.assertEqual(
                connection.execute(
                    text("SELECT COUNT(*) FROM spaces")
                ).scalar_one(),
                1,
            )

    def test_partial_foundation_creation_resumes_idempotently(self) -> None:
        self.create_version_two_database()
        timestamp = datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc)

        with self.engine.begin() as connection:
            Space.__table__.create(bind=connection)
            connection.execute(
                Space.__table__.insert(),
                {
                    "id": "space-before-resume",
                    "name": "Workshop",
                    "description": "Preserve partial state",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )

        self.run_upgrade()
        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text(
                        "SELECT description FROM spaces "
                        "WHERE id = 'space-before-resume'"
                    )
                ).scalar_one(),
                "Preserve partial state",
            )
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

    def test_missing_foundation_indexes_are_repaired_idempotently(
        self,
    ) -> None:
        self.create_version_two_database()

        with self.engine.begin() as connection:
            Base.metadata.create_all(bind=connection)
            connection.exec_driver_sql(
                "DROP INDEX ix_people_display_name"
            )
            connection.exec_driver_sql(
                "DROP INDEX "
                "ix_organization_space_relationships_space_id"
            )

        self.run_upgrade()
        self.run_upgrade()

        expected_indexes = {
            "people": {
                "ix_people_display_name": ("display_name",),
            },
            "organization_space_relationships": {
                "ix_organization_space_relationships_space_id": (
                    "space_id",
                ),
            },
        }
        database_inspector = inspect(self.engine)

        for table_name, expected in expected_indexes.items():
            actual = {
                index["name"]: tuple(index["column_names"])
                for index in database_inspector.get_indexes(table_name)
            }

            for index_name, columns in expected.items():
                self.assertEqual(actual[index_name], columns)

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

    def test_unrepaired_foundation_index_keeps_version_below_three(
        self,
    ) -> None:
        self.create_version_two_database()

        with self.engine.begin() as connection:
            Base.metadata.create_all(bind=connection)
            connection.exec_driver_sql(
                "DROP INDEX ix_members_person_id"
            )

        with patch(
            "app.core.schema_upgrades.FOUNDATION_INDEX_UPGRADES",
            (),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "members indexes are incomplete",
            ):
                with self.engine.connect() as connection:
                    apply_schema_upgrades(connection)

        with self.engine.connect() as connection:
            self.assertEqual(get_database_schema_version(connection), 2)

        self.run_upgrade()

        repaired_indexes = {
            index["name"]: tuple(index["column_names"])
            for index in inspect(self.engine).get_indexes("members")
        }
        self.assertEqual(
            repaired_indexes["ix_members_person_id"],
            ("person_id",),
        )

    def test_failed_upgrade_retains_version_and_can_resume(self) -> None:
        self.create_legacy_database()

        with self.assertRaises(Exception):
            with self.engine.connect() as connection:
                with patch(
                    "app.core.schema_upgrades.PROJECT_INDEX_UPGRADES",
                    ("THIS IS NOT VALID SQL",),
                ):
                    prepare_database_schema(connection)

        with self.engine.connect() as connection:
            self.assertEqual(get_database_schema_version(connection), 0)

        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

    def test_version_one_database_resumes_missing_migration_table(
        self,
    ) -> None:
        self.create_legacy_database()

        with self.engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA user_version = 1")

        with self.engine.connect() as connection:
            with self.assertRaisesRegex(
                RuntimeError,
                "Project material requirements table is missing",
            ):
                apply_schema_upgrades(connection)

        with self.engine.connect() as connection:
            self.assertEqual(get_database_schema_version(connection), 1)

        self.run_upgrade()
        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
        self.assertIn(
            "project_migrations",
            inspect(self.engine).get_table_names(),
        )

    def test_version_one_partial_ddl_failure_resumes_safely(
        self,
    ) -> None:
        self.create_legacy_database()
        self.run_upgrade()

        with self.engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE project_migrations")
            connection.exec_driver_sql("PRAGMA user_version = 1")

        with self.assertRaises(Exception):
            with self.engine.connect() as connection:
                with patch(
                    "app.core.schema_upgrades.PROJECT_INDEX_UPGRADES",
                    ("THIS IS NOT VALID SQL",),
                ):
                    prepare_database_schema(connection)

        with self.engine.connect() as connection:
            self.assertEqual(get_database_schema_version(connection), 1)

        # SQLite may retain the table created before the later DDL failure.
        # A restart must accept that partial state and finish idempotently.
        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
        self.assertIn(
            "project_migrations",
            inspect(self.engine).get_table_names(),
        )
