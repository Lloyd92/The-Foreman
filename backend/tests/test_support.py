import asyncio
import unittest

from httpx import ASGITransport, AsyncClient

from app.core.config import DATABASE_URL
from app.core.database import (
    SessionLocal,
    engine,
    initialize_database,
)
from app.main import app
from app.models.base import Base


# Frozen from the schema at commit 35e3c43 (SQLite user_version 3). These
# fixtures intentionally do not derive operational DDL from current ORM
# metadata, so a model change cannot silently rewrite migration input.
PRE_V4_TABLE_DDL = {
    "spaces": """
        CREATE TABLE spaces (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(120) COLLATE "NOCASE" NOT NULL,
            description TEXT DEFAULT '' NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_spaces_name_not_blank CHECK (
                length(trim(name)) > 0
            ),
            CONSTRAINT uq_spaces_name UNIQUE (name)
        )
    """,
    "people": """
        CREATE TABLE people (
            id VARCHAR(36) NOT NULL,
            display_name VARCHAR(120) NOT NULL,
            given_name VARCHAR(80) DEFAULT '' NOT NULL,
            family_name VARCHAR(80) DEFAULT '' NOT NULL,
            description TEXT DEFAULT '' NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_people_display_name_not_blank CHECK (
                length(trim(display_name)) > 0
            )
        )
    """,
    "organizations": """
        CREATE TABLE organizations (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(120) NOT NULL,
            description TEXT DEFAULT '' NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_organizations_name_not_blank CHECK (
                length(trim(name)) > 0
            )
        )
    """,
    "organization_space_relationships": """
        CREATE TABLE organization_space_relationships (
            id VARCHAR(36) NOT NULL,
            space_id VARCHAR(36) NOT NULL,
            organization_id VARCHAR(36) NOT NULL,
            role VARCHAR(80) COLLATE "NOCASE" NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_organization_space_relationships_role_normalized CHECK (
                    length(role) > 0
                    AND role = lower(trim(role))
                    AND role NOT GLOB '*[^a-z0-9 -]*'
                    AND role NOT LIKE '%  %'
                    AND role NOT LIKE '%--%'
                    AND role NOT LIKE '% -%'
                    AND role NOT LIKE '%- %'
                    AND substr(role, 1, 1) GLOB '[a-z0-9]'
                    AND substr(role, -1, 1) GLOB '[a-z0-9]'
                ),
            CONSTRAINT uq_organization_space_relationship_role UNIQUE (space_id, organization_id, role),
            CONSTRAINT fk_organization_space_relationships_space_id FOREIGN KEY(space_id) REFERENCES spaces (id) ON DELETE RESTRICT,
            CONSTRAINT fk_organization_space_relationships_organization_id FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT
        )
    """,
    "members": """
        CREATE TABLE members (
            id VARCHAR(36) NOT NULL,
            space_id VARCHAR(36) NOT NULL,
            person_id VARCHAR(36) NOT NULL,
            role VARCHAR(80) COLLATE "NOCASE" NOT NULL,
            responsibilities TEXT DEFAULT '' NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_members_role_normalized CHECK (
                    length(role) > 0
                    AND role = lower(trim(role))
                    AND role NOT GLOB '*[^a-z0-9 -]*'
                    AND role NOT LIKE '%  %'
                    AND role NOT LIKE '%--%'
                    AND role NOT LIKE '% -%'
                    AND role NOT LIKE '%- %'
                    AND substr(role, 1, 1) GLOB '[a-z0-9]'
                    AND substr(role, -1, 1) GLOB '[a-z0-9]'
                ),
            CONSTRAINT uq_members_space_person UNIQUE (space_id, person_id),
            CONSTRAINT fk_members_space_id FOREIGN KEY(space_id) REFERENCES spaces (id) ON DELETE RESTRICT,
            CONSTRAINT fk_members_person_id FOREIGN KEY(person_id) REFERENCES people (id) ON DELETE RESTRICT
        )
    """,
    "module_states": """
        CREATE TABLE module_states (
            module_id VARCHAR(80) NOT NULL,
            enabled BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (module_id)
        )
    """,
    "inventory_items": """
        CREATE TABLE inventory_items (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(120) NOT NULL,
            category VARCHAR(80) NOT NULL,
            quantity FLOAT NOT NULL,
            unit VARCHAR(30) NOT NULL,
            minimum FLOAT NOT NULL,
            location VARCHAR(100) NOT NULL,
            cost FLOAT NOT NULL,
            supplier VARCHAR(100) NOT NULL,
            notes TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id)
        )
    """,
    "projects": """
        CREATE TABLE projects (
            id VARCHAR(36) NOT NULL,
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
            PRIMARY KEY (id)
        )
    """,
    "project_material_requirements": """
        CREATE TABLE project_material_requirements (
            project_id VARCHAR(36) NOT NULL,
            inventory_item_id VARCHAR(36) NOT NULL,
            required_quantity FLOAT NOT NULL,
            note TEXT DEFAULT '' NOT NULL,
            PRIMARY KEY (project_id, inventory_item_id),
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    """,
    "tasks": """
        CREATE TABLE tasks (
            id VARCHAR(36) NOT NULL,
            title VARCHAR(120) NOT NULL,
            priority VARCHAR(10) NOT NULL,
            completed BOOLEAN NOT NULL,
            project_id VARCHAR(36),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
        )
    """,
    "inventory_migrations": """
        CREATE TABLE inventory_migrations (
            id INTEGER NOT NULL,
            source VARCHAR(40) NOT NULL,
            source_record_id VARCHAR(120) NOT NULL,
            inventory_item_id VARCHAR(36),
            migrated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_inventory_migration_source_record UNIQUE (source, source_record_id),
            UNIQUE (inventory_item_id),
            FOREIGN KEY(inventory_item_id) REFERENCES inventory_items (id) ON DELETE SET NULL
        )
    """,
    "project_migrations": """
        CREATE TABLE project_migrations (
            id INTEGER NOT NULL,
            source VARCHAR(40) NOT NULL,
            source_record_id VARCHAR(120) NOT NULL,
            project_id VARCHAR(36),
            payload_hash VARCHAR(64) NOT NULL,
            migrated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_project_migration_source_record UNIQUE (source, source_record_id),
            UNIQUE (project_id),
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
        )
    """,
    "task_migrations": """
        CREATE TABLE task_migrations (
            id INTEGER NOT NULL,
            source VARCHAR(40) NOT NULL,
            source_record_id VARCHAR(120) NOT NULL,
            task_id VARCHAR(36),
            migrated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_task_migration_source_record UNIQUE (source, source_record_id),
            UNIQUE (task_id),
            FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE SET NULL
        )
    """,
}

PRE_V4_INDEX_DDL = {
    "inventory_items": (
        "CREATE INDEX ix_inventory_items_category "
        "ON inventory_items (category)",
    ),
    "people": (
        "CREATE INDEX ix_people_display_name ON people (display_name)",
    ),
    "organizations": (
        "CREATE INDEX ix_organizations_name ON organizations (name)",
    ),
    "organization_space_relationships": (
        "CREATE INDEX ix_organization_space_relationships_space_id "
        "ON organization_space_relationships (space_id)",
        "CREATE INDEX ix_organization_space_relationships_organization_id "
        "ON organization_space_relationships (organization_id)",
    ),
    "members": (
        "CREATE INDEX ix_members_space_id ON members (space_id)",
        "CREATE INDEX ix_members_person_id ON members (person_id)",
    ),
    "project_material_requirements": (
        "CREATE INDEX ix_project_material_requirements_inventory_item_id "
        "ON project_material_requirements (inventory_item_id)",
    ),
    "projects": (
        "CREATE INDEX ix_projects_priority ON projects (priority)",
        "CREATE INDEX ix_projects_status ON projects (status)",
        "CREATE INDEX ix_projects_type ON projects (type)",
    ),
    "tasks": (
        "CREATE INDEX ix_tasks_completed ON tasks (completed)",
        "CREATE INDEX ix_tasks_priority ON tasks (priority)",
        "CREATE INDEX ix_tasks_project_id ON tasks (project_id)",
    ),
}


def require_test_database() -> None:
    if "/tmp/" not in DATABASE_URL:
        raise RuntimeError(
            "Tests require a temporary SQLite database URL."
        )


def reset_test_database() -> None:
    Base.metadata.drop_all(bind=engine)

    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA user_version=0")

    initialize_database()


def create_pre_v4_tables(connection, table_names: set[str]) -> None:
    """Create selected frozen version-2/version-3 tables."""
    unknown_tables = table_names - set(PRE_V4_TABLE_DDL)

    if unknown_tables:
        names = ", ".join(sorted(unknown_tables))
        raise ValueError(f"No frozen pre-v4 DDL exists for: {names}.")

    for table_name, statement in PRE_V4_TABLE_DDL.items():
        if table_name in table_names:
            connection.exec_driver_sql(statement)

    for table_name, statements in PRE_V4_INDEX_DDL.items():
        if table_name not in table_names:
            continue

        for statement in statements:
            connection.exec_driver_sql(statement)


class DatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        require_test_database()
        initialize_database()

    def setUp(self) -> None:
        reset_test_database()
        self.session = SessionLocal()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()


class ApiTestCase(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        require_test_database()
        initialize_database()

    async def asyncSetUp(self) -> None:
        asyncio.get_running_loop().slow_callback_duration = 5
        reset_test_database()
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def create_project(
        self,
        *,
        name: str = "Test Project",
        status: str = "planning",
    ) -> dict:
        response = await self.client.post(
            "/api/projects",
            json={
                "name": name,
                "status": status,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()
