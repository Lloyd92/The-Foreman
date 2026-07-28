from sqlalchemy import inspect
from sqlalchemy.engine import Connection

CURRENT_DATABASE_SCHEMA_VERSION = 1

PROJECT_COLUMN_UPGRADES = {
    "type": (
        "ALTER TABLE projects "
        "ADD COLUMN type VARCHAR(30) NOT NULL DEFAULT 'other'"
    ),
    "priority": (
        "ALTER TABLE projects "
        "ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'medium'"
    ),
    "start_date": (
        "ALTER TABLE projects ADD COLUMN start_date DATE"
    ),
    "target_date": (
        "ALTER TABLE projects ADD COLUMN target_date DATE"
    ),
    "estimated_cost": (
        "ALTER TABLE projects "
        "ADD COLUMN estimated_cost FLOAT NOT NULL DEFAULT 0"
    ),
    "description": (
        "ALTER TABLE projects "
        "ADD COLUMN description TEXT NOT NULL DEFAULT ''"
    ),
}

PROJECT_INDEX_UPGRADES = (
    "CREATE INDEX IF NOT EXISTS ix_projects_type ON projects (type)",
    (
        "CREATE INDEX IF NOT EXISTS ix_projects_priority "
        "ON projects (priority)"
    ),
)

REQUIRED_PROJECT_COLUMNS = {
    "id",
    "name",
    "type",
    "status",
    "priority",
    "progress",
    "start_date",
    "target_date",
    "estimated_cost",
    "description",
    "notes",
    "created_at",
    "updated_at",
    "archived_at",
}


def get_database_schema_version(connection: Connection) -> int:
    return int(
        connection.exec_driver_sql(
            "PRAGMA user_version"
        ).scalar_one()
    )


def _project_columns(connection: Connection) -> set[str]:
    return {
        column["name"]
        for column in inspect(connection).get_columns("projects")
    }


def _verify_project_schema(connection: Connection) -> None:
    missing_columns = (
        REQUIRED_PROJECT_COLUMNS - _project_columns(connection)
    )

    if missing_columns:
        names = ", ".join(sorted(missing_columns))
        raise RuntimeError(
            f"Project schema upgrade is incomplete: {names}."
        )

    tables = set(inspect(connection).get_table_names())

    if "project_material_requirements" not in tables:
        raise RuntimeError(
            "Project material requirements table is missing."
        )

    index_names = {
        index["name"]
        for index in inspect(connection).get_indexes("projects")
    }
    required_indexes = {
        "ix_projects_type",
        "ix_projects_priority",
    }

    if not required_indexes.issubset(index_names):
        raise RuntimeError("Project indexes are incomplete.")


def apply_schema_upgrades(connection: Connection) -> None:
    if connection.dialect.name != "sqlite":
        return

    version = get_database_schema_version(connection)

    if version > CURRENT_DATABASE_SCHEMA_VERSION:
        raise RuntimeError(
            "Database schema is newer than this application supports."
        )

    columns = _project_columns(connection)

    for name, statement in PROJECT_COLUMN_UPGRADES.items():
        if name not in columns:
            connection.exec_driver_sql(statement)

    for statement in PROJECT_INDEX_UPGRADES:
        connection.exec_driver_sql(statement)

    _verify_project_schema(connection)

    if version < CURRENT_DATABASE_SCHEMA_VERSION:
        connection.exec_driver_sql(
            f"PRAGMA user_version = "
            f"{CURRENT_DATABASE_SCHEMA_VERSION}"
        )
