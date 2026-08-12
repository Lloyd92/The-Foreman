import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import MetaData, UniqueConstraint, inspect, text
from sqlalchemy.engine import Connection

from app.core.default_space import (
    DEFAULT_SPACE_DESCRIPTION,
    DEFAULT_SPACE_ID,
    DEFAULT_SPACE_NAME,
    DefaultSpaceConflictError,
)
from app.models.base import Base


FOUNDATION_DATABASE_SCHEMA_VERSION = 3
SPACE_SCOPE_DATABASE_SCHEMA_VERSION = 4
UNIVERSAL_WORK_DATABASE_SCHEMA_VERSION = 5
RESOURCE_DATABASE_SCHEMA_VERSION = 6
CALENDAR_DATABASE_SCHEMA_VERSION = 7
CURRENT_DATABASE_SCHEMA_VERSION = CALENDAR_DATABASE_SCHEMA_VERSION
SPACE_SCOPE_JOURNAL_TABLE = "__foreman_v4_space_scope_journal"

RESOURCE_TABLES = (
    "tools",
    "care_plans",
    "tool_maintenance_records",
    "work_tool_requirements",
)

CALENDAR_TABLES = (
    "calendar_settings",
    "calendar_entries",
    "calendar_series",
    "calendar_series_exclusions",
    "work_calendar_relationships",
)

UNIVERSAL_WORK_COLUMN_UPGRADES = (
    (
        "tasks",
        "due_date",
        "ALTER TABLE tasks ADD COLUMN due_date DATE",
    ),
    (
        "tasks",
        "responsible_member_id",
        "ALTER TABLE tasks "
        "ADD COLUMN responsible_member_id VARCHAR(36) "
        "CONSTRAINT fk_tasks_responsible_member_id "
        "REFERENCES members (id) ON DELETE SET NULL",
    ),
    (
        "projects",
        "responsible_member_id",
        "ALTER TABLE projects "
        "ADD COLUMN responsible_member_id VARCHAR(36) "
        "CONSTRAINT fk_projects_responsible_member_id "
        "REFERENCES members (id) ON DELETE SET NULL",
    ),
)

VERSION_FOUR_EXCLUDED_COLUMNS = {
    "projects": frozenset({"responsible_member_id"}),
    "tasks": frozenset({"due_date", "responsible_member_id"}),
}

UNIVERSAL_WORK_CHECK_CONSTRAINTS = {
    "ck_work_dependencies_dependent_type": (
        "dependent_type IN ('task', 'project')"
    ),
    "ck_work_dependencies_prerequisite_type": (
        "prerequisite_type IN ('task', 'project')"
    ),
    "ck_work_dependencies_not_self": (
        "dependent_type != prerequisite_type "
        "OR dependent_id != prerequisite_id"
    ),
}

RESOURCE_CHECK_CONSTRAINTS = {
    "care_plans": {
        "ck_care_plans_frequency_pair": (
            "(frequency_value IS NULL AND frequency_unit IS NULL) "
            "OR (frequency_value IS NOT NULL "
            "AND frequency_value > 0 "
            "AND frequency_unit IS NOT NULL)"
        ),
    },
    "work_tool_requirements": {
        "ck_work_tool_requirements_work_type": (
            "work_type IN ('task', 'project')"
        ),
    },
}



CALENDAR_CHECK_CONSTRAINTS = {
    "calendar_settings": {
        "ck_calendar_settings_timezone_not_blank": (
            "length(trim(timezone_name)) > 0"
        ),
    },
    "calendar_entries": {
        "ck_calendar_entries_kind": (
            "kind IN ('commitment', 'event', 'availability')"
        ),
        "ck_calendar_entries_title_not_blank": (
            "length(trim(title)) > 0"
        ),
        "ck_calendar_entries_timezone_not_blank": (
            "length(trim(timezone_name)) > 0"
        ),
        "ck_calendar_entries_time_shape": (
            "(all_day = 1 "
            "AND start_date IS NOT NULL "
            "AND end_date IS NOT NULL "
            "AND end_date > start_date "
            "AND start_at IS NULL "
            "AND end_at IS NULL) "
            "OR (all_day = 0 "
            "AND start_date IS NULL "
            "AND end_date IS NULL "
            "AND start_at IS NOT NULL "
            "AND end_at IS NOT NULL "
            "AND end_at > start_at)"
        ),
    },
    "calendar_series": {
        "ck_calendar_series_kind": (
            "kind IN ('commitment', 'event', 'availability')"
        ),
        "ck_calendar_series_title_not_blank": (
            "length(trim(title)) > 0"
        ),
        "ck_calendar_series_timezone_not_blank": (
            "length(trim(timezone_name)) > 0"
        ),
        "ck_calendar_series_frequency": (
            "frequency IN ('daily', 'weekly')"
        ),
        "ck_calendar_series_interval_positive": (
            "interval_value > 0"
        ),
        "ck_calendar_series_duration_positive": (
            "duration_minutes > 0"
        ),
        "ck_calendar_series_weekday_mask_range": (
            "weekday_mask >= 0 AND weekday_mask <= 127"
        ),
        "ck_calendar_series_weekday_shape": (
            "(frequency = 'daily' AND weekday_mask = 0) "
            "OR (frequency = 'weekly' "
            "AND weekday_mask >= 1 "
            "AND weekday_mask <= 127)"
        ),
        "ck_calendar_series_end_date": (
            "end_date IS NULL OR end_date >= anchor_date"
        ),
    },
    "work_calendar_relationships": {
        "ck_work_calendar_relationships_work_type": (
            "work_type IN ('task', 'project')"
        ),
        "ck_work_calendar_relationships_calendar_type": (
            "calendar_type IN ('entry', 'series')"
        ),
    },
}

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

FOUNDATION_TABLE_COLUMNS = {
    "spaces": {
        "id",
        "name",
        "description",
        "created_at",
        "updated_at",
    },
    "people": {
        "id",
        "display_name",
        "given_name",
        "family_name",
        "description",
        "created_at",
        "updated_at",
    },
    "organizations": {
        "id",
        "name",
        "description",
        "created_at",
        "updated_at",
    },
    "organization_space_relationships": {
        "id",
        "space_id",
        "organization_id",
        "role",
        "created_at",
        "updated_at",
    },
    "members": {
        "id",
        "space_id",
        "person_id",
        "role",
        "responsibilities",
        "created_at",
        "updated_at",
    },
    "module_states": {
        "module_id",
        "enabled",
        "created_at",
        "updated_at",
    },
}

FOUNDATION_COLUMN_TYPES = {
    "spaces": {
        "id": "VARCHAR(36)",
        "name": "VARCHAR(120)",
        "description": "TEXT",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "people": {
        "id": "VARCHAR(36)",
        "display_name": "VARCHAR(120)",
        "given_name": "VARCHAR(80)",
        "family_name": "VARCHAR(80)",
        "description": "TEXT",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "organizations": {
        "id": "VARCHAR(36)",
        "name": "VARCHAR(120)",
        "description": "TEXT",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "organization_space_relationships": {
        "id": "VARCHAR(36)",
        "space_id": "VARCHAR(36)",
        "organization_id": "VARCHAR(36)",
        "role": "VARCHAR(80)",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "members": {
        "id": "VARCHAR(36)",
        "space_id": "VARCHAR(36)",
        "person_id": "VARCHAR(36)",
        "role": "VARCHAR(80)",
        "responsibilities": "TEXT",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "module_states": {
        "module_id": "VARCHAR(80)",
        "enabled": "BOOLEAN",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
}

FOUNDATION_EMPTY_STRING_DEFAULTS = {
    "spaces": {"description"},
    "people": {"given_name", "family_name", "description"},
    "organizations": {"description"},
    "members": {"responsibilities"},
}

FOUNDATION_NOCASE_COLUMN_TOKENS = {
    "spaces": {'namevarchar(120)collate"nocase"'},
    "organization_space_relationships": {
        'rolevarchar(80)collate"nocase"'
    },
    "members": {'rolevarchar(80)collate"nocase"'},
}

FOUNDATION_PRIMARY_KEYS = {
    "spaces": {"id"},
    "people": {"id"},
    "organizations": {"id"},
    "organization_space_relationships": {"id"},
    "members": {"id"},
    "module_states": {"module_id"},
}

FOUNDATION_INDEXES = {
    "people": {"ix_people_display_name": ("display_name",)},
    "organizations": {"ix_organizations_name": ("name",)},
    "organization_space_relationships": {
        "ix_organization_space_relationships_space_id": ("space_id",),
        "ix_organization_space_relationships_organization_id": (
            "organization_id",
        ),
    },
    "members": {
        "ix_members_space_id": ("space_id",),
        "ix_members_person_id": ("person_id",),
    },
}

FOUNDATION_INDEX_UPGRADES = (
    (
        "people",
        (
            "CREATE INDEX IF NOT EXISTS ix_people_display_name "
            "ON people (display_name)"
        ),
    ),
    (
        "organizations",
        (
            "CREATE INDEX IF NOT EXISTS ix_organizations_name "
            "ON organizations (name)"
        ),
    ),
    (
        "organization_space_relationships",
        (
            "CREATE INDEX IF NOT EXISTS "
            "ix_organization_space_relationships_space_id "
            "ON organization_space_relationships (space_id)"
        ),
    ),
    (
        "organization_space_relationships",
        (
            "CREATE INDEX IF NOT EXISTS "
            "ix_organization_space_relationships_organization_id "
            "ON organization_space_relationships (organization_id)"
        ),
    ),
    (
        "members",
        (
            "CREATE INDEX IF NOT EXISTS ix_members_space_id "
            "ON members (space_id)"
        ),
    ),
    (
        "members",
        (
            "CREATE INDEX IF NOT EXISTS ix_members_person_id "
            "ON members (person_id)"
        ),
    ),
)

FOUNDATION_UNIQUE_CONSTRAINTS = {
    "spaces": {"uq_spaces_name": ("name",)},
    "organization_space_relationships": {
        "uq_organization_space_relationship_role": (
            "space_id",
            "organization_id",
            "role",
        ),
    },
    "members": {"uq_members_space_person": ("space_id", "person_id")},
}

FOUNDATION_CHECK_CONSTRAINTS = {
    "spaces": {"ck_spaces_name_not_blank": "length(trim(name)) > 0"},
    "people": {
        "ck_people_display_name_not_blank": (
            "length(trim(display_name)) > 0"
        )
    },
    "organizations": {
        "ck_organizations_name_not_blank": "length(trim(name)) > 0"
    },
    "organization_space_relationships": {
        "ck_organization_space_relationships_role_normalized": (
            "length(role) > 0 "
            "AND role = lower(trim(role)) "
            "AND role NOT GLOB '*[^a-z0-9 -]*' "
            "AND role NOT LIKE '%  %' "
            "AND role NOT LIKE '%--%' "
            "AND role NOT LIKE '% -%' "
            "AND role NOT LIKE '%- %' "
            "AND substr(role, 1, 1) GLOB '[a-z0-9]' "
            "AND substr(role, -1, 1) GLOB '[a-z0-9]'"
        ),
    },
    "members": {
        "ck_members_role_normalized": (
            "length(role) > 0 "
            "AND role = lower(trim(role)) "
            "AND role NOT GLOB '*[^a-z0-9 -]*' "
            "AND role NOT LIKE '%  %' "
            "AND role NOT LIKE '%--%' "
            "AND role NOT LIKE '% -%' "
            "AND role NOT LIKE '%- %' "
            "AND substr(role, 1, 1) GLOB '[a-z0-9]' "
            "AND substr(role, -1, 1) GLOB '[a-z0-9]'"
        ),
    },
}

FOUNDATION_FOREIGN_KEYS = {
    "organization_space_relationships": {
        "fk_organization_space_relationships_space_id": (
            ("space_id",),
            "spaces",
            ("id",),
        ),
        "fk_organization_space_relationships_organization_id": (
            ("organization_id",),
            "organizations",
            ("id",),
        ),
    },
    "members": {
        "fk_members_space_id": (
            ("space_id",),
            "spaces",
            ("id",),
        ),
        "fk_members_person_id": (
            ("person_id",),
            "people",
            ("id",),
        ),
    },
}


@dataclass(frozen=True)
class SpaceScopedTableUpgrade:
    table_name: str

    @property
    def shadow_name(self) -> str:
        return f"__foreman_v4_{self.table_name}_shadow"

    @property
    def ready_name(self) -> str:
        return f"__foreman_v4_{self.table_name}_ready"


@dataclass(frozen=True)
class SpaceScopedMigrationEvidence:
    canonical_table: str
    replacement_table: str
    phase: str
    source_row_count: int
    replacement_row_count: int
    source_digest: str
    replacement_digest: str
    expected_space_id: str


SPACE_SCOPED_TABLE_UPGRADES = tuple(
    SpaceScopedTableUpgrade(table_name)
    for table_name in (
        "inventory_items",
        "projects",
        "tasks",
        "inventory_migrations",
        "project_migrations",
        "task_migrations",
    )
)
SPACE_SCOPED_TABLE_UPGRADES_BY_NAME = {
    upgrade.table_name: upgrade
    for upgrade in SPACE_SCOPED_TABLE_UPGRADES
}
SPACE_SCOPE_JOURNAL_PHASES = frozenset({"ready", "complete"})
SPACE_SCOPE_JOURNAL_COLUMNS = (
    (0, "canonical_table", "VARCHAR(80)", 1, None, 1),
    (1, "replacement_table", "VARCHAR(120)", 1, None, 0),
    (2, "phase", "VARCHAR(20)", 1, None, 0),
    (3, "source_row_count", "INTEGER", 1, None, 0),
    (4, "replacement_row_count", "INTEGER", 1, None, 0),
    (5, "source_digest", "VARCHAR(64)", 1, None, 0),
    (6, "replacement_digest", "VARCHAR(64)", 1, None, 0),
    (7, "expected_space_id", "VARCHAR(36)", 1, None, 0),
)
SPACE_SCOPE_JOURNAL_CHECKS = {
    "ck_foreman_v4_journal_phase": "phase IN ('ready', 'complete')",
    "ck_foreman_v4_journal_source_count": "source_row_count >= 0",
    "ck_foreman_v4_journal_replacement_count": (
        "replacement_row_count >= 0"
    ),
}
SPACE_SCOPE_JOURNAL_CREATE_SQL = f"""
    CREATE TABLE {SPACE_SCOPE_JOURNAL_TABLE} (
        canonical_table VARCHAR(80) NOT NULL PRIMARY KEY,
        replacement_table VARCHAR(120) NOT NULL,
        phase VARCHAR(20) NOT NULL,
        source_row_count INTEGER NOT NULL,
        replacement_row_count INTEGER NOT NULL,
        source_digest VARCHAR(64) NOT NULL,
        replacement_digest VARCHAR(64) NOT NULL,
        expected_space_id VARCHAR(36) NOT NULL,
        CONSTRAINT ck_foreman_v4_journal_phase
            CHECK (phase IN ('ready', 'complete')),
        CONSTRAINT ck_foreman_v4_journal_source_count
            CHECK (source_row_count >= 0),
        CONSTRAINT ck_foreman_v4_journal_replacement_count
            CHECK (replacement_row_count >= 0)
    )
"""


def get_database_schema_version(connection: Connection) -> int:
    return int(
        connection.exec_driver_sql(
            "PRAGMA user_version"
        ).scalar_one()
    )


def assert_supported_database_version(connection: Connection) -> int:
    if connection.dialect.name != "sqlite":
        return 0

    version = get_database_schema_version(connection)

    if version > CURRENT_DATABASE_SCHEMA_VERSION:
        raise RuntimeError(
            "Database schema is newer than this application supports."
        )

    if SPACE_SCOPE_JOURNAL_TABLE in inspect(connection).get_table_names():
        _verify_migration_journal_schema(connection)

    return version


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

    if "project_migrations" not in tables:
        raise RuntimeError("Project migrations table is missing.")

    migration_unique_constraints = {
        constraint["name"]
        for constraint in inspect(connection).get_unique_constraints(
            "project_migrations"
        )
    }

    if (
        "uq_project_migration_source_record"
        not in migration_unique_constraints
    ):
        raise RuntimeError(
            "Project migration source uniqueness is missing."
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


def _canonical_sql(value: str) -> str:
    return "".join(value.lower().split())


def _verify_foundation_schema(connection: Connection) -> None:
    database_inspector = inspect(connection)
    tables = set(database_inspector.get_table_names())
    required_tables = set(FOUNDATION_TABLE_COLUMNS)
    missing_tables = required_tables - tables

    if missing_tables:
        names = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            f"Universal foundation tables are missing: {names}."
        )

    for table_name, expected_columns in FOUNDATION_TABLE_COLUMNS.items():
        column_definitions = database_inspector.get_columns(table_name)
        actual_columns = {
            column["name"]: column for column in column_definitions
        }

        if set(actual_columns) != expected_columns:
            raise RuntimeError(
                f"{table_name} columns do not match the foundation schema."
            )

        expected_types = FOUNDATION_COLUMN_TYPES[table_name]

        for column_name, expected_type in expected_types.items():
            actual = actual_columns[column_name]

            if (
                str(actual["type"]).upper() != expected_type
                or actual["nullable"]
            ):
                raise RuntimeError(
                    f"{table_name}.{column_name} is not required with "
                    "the expected type."
                )

        for column_name in FOUNDATION_EMPTY_STRING_DEFAULTS.get(
            table_name, set()
        ):
            if _canonical_sql(
                str(actual_columns[column_name].get("default"))
            ) != "''":
                raise RuntimeError(
                    f"{table_name}.{column_name} has no exact empty-string "
                    "default."
                )

        actual_primary_key = set(
            database_inspector.get_pk_constraint(table_name).get(
                "constrained_columns"
            )
            or []
        )

        if actual_primary_key != FOUNDATION_PRIMARY_KEYS[table_name]:
            raise RuntimeError(
                f"{table_name} primary key is incomplete."
            )

    table_sql = {
        table_name: _canonical_sql(
            str(
                connection.exec_driver_sql(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'table' AND name = ?",
                    (table_name,),
                ).scalar_one()
            )
        )
        for table_name in FOUNDATION_NOCASE_COLUMN_TOKENS
    }

    for table_name, required_tokens in (
        FOUNDATION_NOCASE_COLUMN_TOKENS.items()
    ):
        if any(
            token not in table_sql[table_name]
            for token in required_tokens
        ):
            raise RuntimeError(
                f"{table_name} case-insensitive columns are incomplete."
            )

    for table_name, expected_indexes in FOUNDATION_INDEXES.items():
        actual_indexes = {
            index["name"]: index
            for index in database_inspector.get_indexes(table_name)
        }

        for index_name, expected_columns in expected_indexes.items():
            actual = actual_indexes.get(index_name)

            if (
                actual is None
                or tuple(actual["column_names"]) != expected_columns
                or actual["unique"]
            ):
                raise RuntimeError(f"{table_name} indexes are incomplete.")

    for table_name, expected_constraints in (
        FOUNDATION_UNIQUE_CONSTRAINTS.items()
    ):
        actual_constraints = {
            constraint.get("name"): constraint
            for constraint in database_inspector.get_unique_constraints(
                table_name
            )
        }

        for constraint_name, expected_columns in (
            expected_constraints.items()
        ):
            actual = actual_constraints.get(constraint_name)

            if (
                actual is None
                or tuple(actual["column_names"]) != expected_columns
            ):
                raise RuntimeError(
                    f"{table_name} unique constraints are incomplete."
                )

    for table_name, expected_constraints in (
        FOUNDATION_CHECK_CONSTRAINTS.items()
    ):
        actual_constraints = {
            constraint.get("name"): constraint
            for constraint in database_inspector.get_check_constraints(
                table_name
            )
        }

        for constraint_name, expected_sql in expected_constraints.items():
            actual = actual_constraints.get(constraint_name)

            if (
                actual is None
                or _canonical_sql(actual["sqltext"])
                != _canonical_sql(expected_sql)
            ):
                raise RuntimeError(
                    f"{table_name} check constraints are incomplete."
                )

    for table_name, expected_foreign_keys in FOUNDATION_FOREIGN_KEYS.items():
        actual_foreign_keys = {
            foreign_key.get("name"): foreign_key
            for foreign_key in database_inspector.get_foreign_keys(table_name)
        }

        for name, expected in expected_foreign_keys.items():
            actual = actual_foreign_keys.get(name)

            if actual is None:
                raise RuntimeError(
                    f"{table_name} foreign keys are incomplete."
                )

            constrained_columns, referred_table, referred_columns = expected
            ondelete = (actual.get("options") or {}).get("ondelete")

            if (
                tuple(actual["constrained_columns"]) != constrained_columns
                or actual["referred_table"] != referred_table
                or tuple(actual["referred_columns"]) != referred_columns
                or str(ondelete).upper() != "RESTRICT"
            ):
                raise RuntimeError(
                    f"{table_name} foreign key {name} is invalid."
                )


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _normalized_default(value: object) -> str:
    normalized = _canonical_sql(str(value))

    if len(normalized) >= 2 and normalized[0] == normalized[-1] == "'":
        return normalized[1:-1]

    return normalized


def _physical_model_table(table_name: str, physical_name: str):
    metadata = MetaData()

    for existing_name, table in Base.metadata.tables.items():
        if existing_name != table_name:
            table.to_metadata(metadata)

    physical_table = Base.metadata.tables[table_name].to_metadata(
        metadata,
        name=physical_name,
    )

    for index in tuple(physical_table.indexes):
        physical_table.indexes.remove(index)

    return physical_table


def _table_has_final_structure(
    connection: Connection,
    table_name: str,
    physical_name: str | None = None,
) -> bool:
    actual_name = physical_name or table_name
    database_inspector = inspect(connection)

    if actual_name not in database_inspector.get_table_names():
        return False

    model_table = Base.metadata.tables[table_name]
    expected_columns = list(model_table.columns)
    actual_columns = database_inspector.get_columns(actual_name)

    if [column["name"] for column in actual_columns] != [
        column.name for column in expected_columns
    ]:
        return False

    for expected, actual in zip(expected_columns, actual_columns, strict=True):
        expected_default = (
            None
            if expected.server_default is None
            else _normalized_default(expected.server_default.arg)
        )
        actual_default = (
            None
            if actual.get("default") is None
            else _normalized_default(actual["default"])
        )

        if (
            str(actual["type"]).upper() != str(expected.type).upper()
            or bool(actual["nullable"]) != bool(expected.nullable)
            or actual_default != expected_default
        ):
            return False

    actual_primary_key = tuple(
        database_inspector.get_pk_constraint(actual_name).get(
            "constrained_columns"
        )
        or []
    )
    expected_primary_key = tuple(
        column.name for column in model_table.primary_key.columns
    )

    if actual_primary_key != expected_primary_key:
        return False

    expected_unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in model_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    actual_unique_constraints = {
        constraint.get("name"): tuple(constraint["column_names"])
        for constraint in database_inspector.get_unique_constraints(
            actual_name
        )
    }

    if actual_unique_constraints != expected_unique_constraints:
        return False

    expected_foreign_keys = {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
            str(constraint.ondelete or "").upper(),
        )
        for constraint in model_table.foreign_key_constraints
    }
    actual_foreign_keys = {
        foreign_key.get("name"): (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
            str(
                (foreign_key.get("options") or {}).get("ondelete") or ""
            ).upper(),
        )
        for foreign_key in database_inspector.get_foreign_keys(actual_name)
    }
    return actual_foreign_keys == expected_foreign_keys


def _table_has_version_four_structure(
    connection: Connection,
    table_name: str,
    physical_name: str | None = None,
) -> bool:
    actual_name = physical_name or table_name
    database_inspector = inspect(connection)

    if actual_name not in database_inspector.get_table_names():
        return False

    model_table = Base.metadata.tables[table_name]
    excluded_columns = VERSION_FOUR_EXCLUDED_COLUMNS.get(
        table_name,
        frozenset(),
    )
    expected_columns = [
        column
        for column in model_table.columns
        if column.name not in excluded_columns
    ]
    actual_columns = database_inspector.get_columns(actual_name)

    if [column["name"] for column in actual_columns] != [
        column.name for column in expected_columns
    ]:
        return False

    for expected, actual in zip(expected_columns, actual_columns, strict=True):
        expected_default = (
            None
            if expected.server_default is None
            else _normalized_default(expected.server_default.arg)
        )
        actual_default = (
            None
            if actual.get("default") is None
            else _normalized_default(actual["default"])
        )

        if (
            str(actual["type"]).upper() != str(expected.type).upper()
            or bool(actual["nullable"]) != bool(expected.nullable)
            or actual_default != expected_default
        ):
            return False

    actual_primary_key = tuple(
        database_inspector.get_pk_constraint(actual_name).get(
            "constrained_columns"
        )
        or []
    )
    expected_primary_key = tuple(
        column.name for column in model_table.primary_key.columns
    )

    if actual_primary_key != expected_primary_key:
        return False

    expected_unique_constraints = {
        constraint.name: tuple(
            column.name for column in constraint.columns
        )
        for constraint in model_table.constraints
        if isinstance(constraint, UniqueConstraint)
        and not any(
            column.name in excluded_columns
            for column in constraint.columns
        )
    }
    actual_unique_constraints = {
        constraint.get("name"): tuple(constraint["column_names"])
        for constraint in database_inspector.get_unique_constraints(
            actual_name
        )
    }

    if actual_unique_constraints != expected_unique_constraints:
        return False

    expected_foreign_keys = {
        constraint.name: (
            tuple(
                element.parent.name
                for element in constraint.elements
            ),
            constraint.referred_table.name,
            tuple(
                element.column.name
                for element in constraint.elements
            ),
            str(constraint.ondelete or "").upper(),
        )
        for constraint in model_table.foreign_key_constraints
        if not any(
            element.parent.name in excluded_columns
            for element in constraint.elements
        )
    }
    actual_foreign_keys = {
        foreign_key.get("name"): (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
            str(
                (foreign_key.get("options") or {}).get("ondelete")
                or ""
            ).upper(),
        )
        for foreign_key in database_inspector.get_foreign_keys(
            actual_name
        )
    }

    return actual_foreign_keys == expected_foreign_keys


def _table_has_version_four_compatible_structure(
    connection: Connection,
    table_name: str,
    physical_name: str | None = None,
) -> bool:
    actual_name = physical_name or table_name
    database_inspector = inspect(connection)

    if actual_name not in database_inspector.get_table_names():
        return False

    model_table = Base.metadata.tables[table_name]
    allowed_additions = VERSION_FOUR_EXCLUDED_COLUMNS.get(
        table_name,
        frozenset(),
    )
    actual_columns = database_inspector.get_columns(actual_name)
    actual_column_names = [
        column["name"] for column in actual_columns
    ]

    expected_base_columns = [
        column
        for column in model_table.columns
        if column.name not in allowed_additions
    ]
    expected_base_names = [
        column.name for column in expected_base_columns
    ]

    # Historical v4 columns must retain their original physical order.
    # Approved additive v5 columns may appear in ORM declaration order
    # on a fresh/rebuilt table or at the end after SQLite ALTER TABLE.
    actual_base_names = [
        name
        for name in actual_column_names
        if name not in allowed_additions
    ]

    if actual_base_names != expected_base_names:
        return False

    expected_all_names = {
        column.name for column in model_table.columns
    }

    if not set(actual_column_names).issubset(expected_all_names):
        return False

    expected_by_name = {
        column.name: column
        for column in model_table.columns
    }

    for actual in actual_columns:
        expected = expected_by_name[actual["name"]]
        expected_default = (
            None
            if expected.server_default is None
            else _normalized_default(expected.server_default.arg)
        )
        actual_default = (
            None
            if actual.get("default") is None
            else _normalized_default(actual["default"])
        )

        if (
            str(actual["type"]).upper()
            != str(expected.type).upper()
            or bool(actual["nullable"]) != bool(expected.nullable)
            or actual_default != expected_default
        ):
            return False

    actual_primary_key = tuple(
        database_inspector.get_pk_constraint(actual_name).get(
            "constrained_columns"
        )
        or []
    )
    expected_primary_key = tuple(
        column.name for column in model_table.primary_key.columns
    )

    if actual_primary_key != expected_primary_key:
        return False

    actual_column_set = set(actual_column_names)
    expected_unique_constraints = {
        constraint.name: tuple(
            column.name for column in constraint.columns
        )
        for constraint in model_table.constraints
        if isinstance(constraint, UniqueConstraint)
        and all(
            column.name in actual_column_set
            for column in constraint.columns
        )
    }
    actual_unique_constraints = {
        constraint.get("name"): tuple(constraint["column_names"])
        for constraint
        in database_inspector.get_unique_constraints(actual_name)
    }

    if actual_unique_constraints != expected_unique_constraints:
        return False

    expected_foreign_keys = {
        (
            tuple(
                element.parent.name
                for element in constraint.elements
            ),
            constraint.referred_table.name,
            tuple(
                element.column.name
                for element in constraint.elements
            ),
            str(constraint.ondelete or "").upper(),
        )
        for constraint in model_table.foreign_key_constraints
        if all(
            element.parent.name in actual_column_set
            for element in constraint.elements
        )
    }

    raw_foreign_keys = connection.exec_driver_sql(
        "PRAGMA foreign_key_list("
        f"{_quote_identifier(actual_name)})"
    ).all()
    grouped_foreign_keys: dict[int, list[object]] = {}

    for row in raw_foreign_keys:
        grouped_foreign_keys.setdefault(int(row[0]), []).append(row)

    actual_foreign_keys = set()

    for rows in grouped_foreign_keys.values():
        ordered = sorted(rows, key=lambda row: int(row[1]))
        actual_foreign_keys.add(
            (
                tuple(str(row[3]) for row in ordered),
                str(ordered[0][2]),
                tuple(str(row[4]) for row in ordered),
                str(ordered[0][6] or "").upper(),
            )
        )

    return actual_foreign_keys == expected_foreign_keys


def _expected_indexes(table_name: str) -> dict[str, tuple[str, ...]]:
    return {
        index.name: tuple(column.name for column in index.columns)
        for index in Base.metadata.tables[table_name].indexes
    }


def _actual_indexes(
    connection: Connection,
    table_name: str,
) -> dict[str, tuple[tuple[str, ...], bool]]:
    return {
        index["name"]: (
            tuple(index["column_names"]),
            bool(index["unique"]),
        )
        for index in inspect(connection).get_indexes(table_name)
    }


def _verify_legacy_indexes(
    connection: Connection,
    table_name: str,
) -> None:
    expected = _expected_indexes(table_name)
    expected.pop(f"ix_{table_name}_space_id")
    actual = _actual_indexes(connection, table_name)

    unexpected = set(actual) - set(expected)

    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise RuntimeError(
            f"{table_name} has unsupported indexes that cannot be "
            f"discarded during migration: {names}."
        )

    for name, (columns, unique) in actual.items():
        if columns != expected[name] or unique:
            raise RuntimeError(
                f"{table_name} index {name} is malformed."
            )


def _repair_scoped_indexes(
    connection: Connection,
    table_name: str,
) -> None:
    for name, columns in sorted(_expected_indexes(table_name).items()):
        column_sql = ", ".join(_quote_identifier(column) for column in columns)
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS "
            f"{_quote_identifier(name)} ON "
            f"{_quote_identifier(table_name)} ({column_sql})"
        )


def _verify_scoped_indexes(
    connection: Connection,
    table_name: str,
) -> None:
    expected = _expected_indexes(table_name)
    actual = _actual_indexes(connection, table_name)

    if set(actual) != set(expected):
        raise RuntimeError(f"{table_name} indexes are incomplete.")

    for name, columns in expected.items():
        actual_columns, unique = actual[name]

        if actual_columns != columns or unique:
            raise RuntimeError(f"{table_name} index {name} is malformed.")


def _verify_version_four_compatible_indexes(
    connection: Connection,
    table_name: str,
) -> None:
    expected = _expected_indexes(table_name)
    actual = _actual_indexes(connection, table_name)

    unexpected = set(actual) - set(expected)

    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise RuntimeError(
            f"{table_name} has unsupported indexes: {names}."
        )

    for name, (actual_columns, unique) in actual.items():
        if actual_columns != expected[name] or unique:
            raise RuntimeError(
                f"{table_name} index {name} is malformed."
            )


def _unexpected_triggers(
    connection: Connection,
    table_names: tuple[str, ...],
) -> list[str]:
    if not table_names:
        return []

    placeholders = ", ".join(
        f":table_{index}" for index, _ in enumerate(table_names)
    )
    parameters = {
        f"table_{index}": table_name
        for index, table_name in enumerate(table_names)
    }
    return list(
        connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'trigger' "
                f"AND tbl_name IN ({placeholders}) "
                "ORDER BY name"
            ),
            parameters,
        ).scalars()
    )


def _assert_no_migration_triggers(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    triggers = _unexpected_triggers(
        connection,
        (upgrade.table_name, upgrade.shadow_name, upgrade.ready_name),
    )

    if triggers:
        names = ", ".join(triggers)
        raise RuntimeError(
            f"{upgrade.table_name} has unsupported triggers that cannot be "
            f"discarded during migration: {names}."
        )


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _create_shadow_table(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    _physical_model_table(
        upgrade.table_name,
        upgrade.shadow_name,
    ).create(bind=connection)


def _copy_into_shadow(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    model_columns = [
        column.name
        for column in Base.metadata.tables[upgrade.table_name].columns
    ]
    insert_columns = ", ".join(
        _quote_identifier(column) for column in model_columns
    )
    select_columns = ", ".join(
        (
            ":default_space_id"
            if column == "space_id"
            else _quote_identifier(column)
        )
        for column in model_columns
    )
    connection.execute(
        text(
            f"INSERT INTO {_quote_identifier(upgrade.shadow_name)} "
            f"({insert_columns}) SELECT {select_columns} "
            f"FROM {_quote_identifier(upgrade.table_name)}"
        ),
        {"default_space_id": DEFAULT_SPACE_ID},
    )


def _legacy_column_names(table_name: str) -> tuple[str, ...]:
    excluded_columns = VERSION_FOUR_EXCLUDED_COLUMNS.get(
        table_name,
        frozenset(),
    )
    return tuple(
        column.name
        for column in Base.metadata.tables[table_name].columns
        if column.name != "space_id"
        and column.name not in excluded_columns
    )


def _digest_value(value: object) -> bytes:
    if value is None:
        return b"null"

    if isinstance(value, bytes):
        return b"bytes:" + value

    if isinstance(value, float):
        return b"float:" + value.hex().encode("ascii")

    if isinstance(value, int):
        return b"int:" + str(value).encode("ascii")

    return b"text:" + str(value).encode("utf-8")


def _table_evidence(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    physical_name: str,
) -> tuple[int, str]:
    columns = _legacy_column_names(upgrade.table_name)
    primary_key_columns = tuple(
        column.name
        for column in Base.metadata.tables[upgrade.table_name].primary_key
    )
    selected_columns = ", ".join(
        _quote_identifier(column) for column in columns
    )
    ordering = ", ".join(
        _quote_identifier(column) for column in primary_key_columns
    )
    rows = connection.exec_driver_sql(
        f"SELECT {selected_columns} FROM {_quote_identifier(physical_name)} "
        f"ORDER BY {ordering}"
    )
    digest = hashlib.sha256()
    digest.update(b"foreman-v4-space-scope\0")
    row_count = 0

    for column in columns:
        encoded_column = column.encode("utf-8")
        digest.update(len(encoded_column).to_bytes(8, "big"))
        digest.update(encoded_column)

    for row in rows:
        row_count += 1
        digest.update(b"row\0")

        for value in row:
            encoded_value = _digest_value(value)
            digest.update(len(encoded_value).to_bytes(8, "big"))
            digest.update(encoded_value)

    return row_count, digest.hexdigest()


def _replacement_has_exact_space(
    connection: Connection,
    table_name: str,
) -> bool:
    invalid_space_count = connection.execute(
        text(
            f"SELECT COUNT(*) FROM {_quote_identifier(table_name)} "
            "WHERE space_id IS NULL OR space_id != :default_space_id"
        ),
        {"default_space_id": DEFAULT_SPACE_ID},
    ).scalar_one()
    return invalid_space_count == 0


def _copy_evidence(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    replacement_name: str,
) -> SpaceScopedMigrationEvidence | None:
    if not _table_has_version_four_compatible_structure(
        connection,
        upgrade.table_name,
        replacement_name,
    ):
        return None

    if not _replacement_has_exact_space(connection, replacement_name):
        return None

    source_count, source_digest = _table_evidence(
        connection,
        upgrade,
        upgrade.table_name,
    )
    replacement_count, replacement_digest = _table_evidence(
        connection,
        upgrade,
        replacement_name,
    )

    if (
        source_count != replacement_count
        or source_digest != replacement_digest
    ):
        return None

    return SpaceScopedMigrationEvidence(
        canonical_table=upgrade.table_name,
        replacement_table=upgrade.ready_name,
        phase="ready",
        source_row_count=source_count,
        replacement_row_count=replacement_count,
        source_digest=source_digest,
        replacement_digest=replacement_digest,
        expected_space_id=DEFAULT_SPACE_ID,
    )


def _shadow_matches_canonical(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    shadow_name: str,
) -> bool:
    return _copy_evidence(connection, upgrade, shadow_name) is not None


def _ensure_migration_journal(connection: Connection) -> None:
    with connection.begin():
        connection.exec_driver_sql(
            SPACE_SCOPE_JOURNAL_CREATE_SQL.replace(
                "CREATE TABLE ",
                "CREATE TABLE IF NOT EXISTS ",
                1,
            )
        )
        _verify_migration_journal_schema(connection)


def _verify_migration_journal_schema(connection: Connection) -> None:
    database_inspector = inspect(connection)

    if SPACE_SCOPE_JOURNAL_TABLE not in database_inspector.get_table_names():
        raise RuntimeError("The version 4 migration journal is missing.")

    table_info = tuple(
        tuple(row)
        for row in connection.exec_driver_sql(
            f"PRAGMA table_info({_quote_identifier(SPACE_SCOPE_JOURNAL_TABLE)})"
        )
    )

    if table_info != SPACE_SCOPE_JOURNAL_COLUMNS:
        raise RuntimeError("The version 4 migration journal is malformed.")

    primary_key = tuple(
        database_inspector.get_pk_constraint(
            SPACE_SCOPE_JOURNAL_TABLE
        ).get("constrained_columns")
        or []
    )

    if primary_key != ("canonical_table",):
        raise RuntimeError("The version 4 migration journal is malformed.")

    actual_checks = {
        constraint.get("name"): _canonical_sql(constraint["sqltext"])
        for constraint in database_inspector.get_check_constraints(
            SPACE_SCOPE_JOURNAL_TABLE
        )
    }
    expected_checks = {
        name: _canonical_sql(expression)
        for name, expression in SPACE_SCOPE_JOURNAL_CHECKS.items()
    }

    if actual_checks != expected_checks:
        raise RuntimeError("The version 4 migration journal is malformed.")

    if database_inspector.get_foreign_keys(SPACE_SCOPE_JOURNAL_TABLE):
        raise RuntimeError("The version 4 migration journal is malformed.")

    if database_inspector.get_unique_constraints(SPACE_SCOPE_JOURNAL_TABLE):
        raise RuntimeError("The version 4 migration journal is malformed.")

    if database_inspector.get_indexes(SPACE_SCOPE_JOURNAL_TABLE):
        raise RuntimeError("The version 4 migration journal is malformed.")

    pragma_indexes = tuple(
        (int(row[2]), str(row[3]), int(row[4]))
        for row in connection.exec_driver_sql(
            f"PRAGMA index_list({_quote_identifier(SPACE_SCOPE_JOURNAL_TABLE)})"
        )
    )

    if pragma_indexes != ((1, "pk", 0),):
        raise RuntimeError("The version 4 migration journal is malformed.")

    create_sql = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name = ?",
        (SPACE_SCOPE_JOURNAL_TABLE,),
    ).scalar_one()

    if _canonical_sql(str(create_sql)) != _canonical_sql(
        SPACE_SCOPE_JOURNAL_CREATE_SQL
    ):
        raise RuntimeError("The version 4 migration journal is malformed.")


def _read_migration_evidence(
    connection: Connection,
    table_name: str,
) -> SpaceScopedMigrationEvidence | None:
    if SPACE_SCOPE_JOURNAL_TABLE not in _table_names(connection):
        return None

    _verify_migration_journal_schema(connection)
    row = connection.execute(
        text(
            f"SELECT canonical_table, replacement_table, phase, "
            "source_row_count, replacement_row_count, source_digest, "
            "replacement_digest, expected_space_id "
            f"FROM {SPACE_SCOPE_JOURNAL_TABLE} "
            "WHERE canonical_table = :canonical_table"
        ),
        {"canonical_table": table_name},
    ).mappings().one_or_none()

    if row is None:
        return None

    return SpaceScopedMigrationEvidence(**row)


def _write_migration_evidence(
    connection: Connection,
    evidence: SpaceScopedMigrationEvidence,
) -> None:
    connection.execute(
        text(
            f"""
            INSERT INTO {SPACE_SCOPE_JOURNAL_TABLE} (
                canonical_table,
                replacement_table,
                phase,
                source_row_count,
                replacement_row_count,
                source_digest,
                replacement_digest,
                expected_space_id
            ) VALUES (
                :canonical_table,
                :replacement_table,
                :phase,
                :source_row_count,
                :replacement_row_count,
                :source_digest,
                :replacement_digest,
                :expected_space_id
            )
            ON CONFLICT(canonical_table) DO UPDATE SET
                replacement_table = excluded.replacement_table,
                phase = excluded.phase,
                source_row_count = excluded.source_row_count,
                replacement_row_count = excluded.replacement_row_count,
                source_digest = excluded.source_digest,
                replacement_digest = excluded.replacement_digest,
                expected_space_id = excluded.expected_space_id
            """
        ),
        evidence.__dict__,
    )


def _evidence_is_self_consistent(
    evidence: SpaceScopedMigrationEvidence,
    upgrade: SpaceScopedTableUpgrade,
) -> bool:
    return (
        evidence.canonical_table == upgrade.table_name
        and evidence.replacement_table == upgrade.ready_name
        and evidence.phase in SPACE_SCOPE_JOURNAL_PHASES
        and evidence.source_row_count == evidence.replacement_row_count
        and evidence.source_digest == evidence.replacement_digest
        and evidence.expected_space_id == DEFAULT_SPACE_ID
    )


def _ready_matches_durable_evidence(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    evidence: SpaceScopedMigrationEvidence,
    *,
    canonical_exists: bool,
) -> bool:
    if evidence.phase != "ready" or not _evidence_is_self_consistent(
        evidence,
        upgrade,
    ):
        return False

    if not _table_has_version_four_compatible_structure(
        connection,
        upgrade.table_name,
        upgrade.ready_name,
    ):
        return False

    if not _replacement_has_exact_space(connection, upgrade.ready_name):
        return False

    ready_count, ready_digest = _table_evidence(
        connection,
        upgrade,
        upgrade.ready_name,
    )

    if (
        ready_count != evidence.replacement_row_count
        or ready_digest != evidence.replacement_digest
    ):
        return False

    if canonical_exists:
        source_count, source_digest = _table_evidence(
            connection,
            upgrade,
            upgrade.table_name,
        )

        if (
            source_count != evidence.source_row_count
            or source_digest != evidence.source_digest
        ):
            return False

    return True


def _final_matches_durable_evidence(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    evidence: SpaceScopedMigrationEvidence,
) -> bool:
    if not _evidence_is_self_consistent(evidence, upgrade):
        return False

    if not _replacement_has_exact_space(connection, upgrade.table_name):
        return False

    final_count, final_digest = _table_evidence(
        connection,
        upgrade,
        upgrade.table_name,
    )
    return (
        final_count == evidence.replacement_row_count
        and final_digest == evidence.replacement_digest
    )


def _validate_existing_migration_journal(
    connection: Connection,
) -> None:
    if SPACE_SCOPE_JOURNAL_TABLE not in _table_names(connection):
        return

    _verify_migration_journal_schema(connection)
    rows = connection.execute(
        text(
            f"SELECT canonical_table, replacement_table, phase, "
            "source_row_count, replacement_row_count, source_digest, "
            "replacement_digest, expected_space_id "
            f"FROM {SPACE_SCOPE_JOURNAL_TABLE} "
            "ORDER BY canonical_table"
        )
    ).mappings().all()
    tables = _table_names(connection)

    for row in rows:
        canonical_table = row["canonical_table"]
        upgrade = SPACE_SCOPED_TABLE_UPGRADES_BY_NAME.get(canonical_table)

        if upgrade is None:
            raise RuntimeError(
                "The version 4 migration journal contains an unknown "
                "canonical table."
            )

        evidence = SpaceScopedMigrationEvidence(**row)

        if not _evidence_is_self_consistent(evidence, upgrade):
            raise RuntimeError(
                f"{upgrade.table_name} has invalid migration journal "
                "evidence."
            )

        canonical_exists = upgrade.table_name in tables
        ready_exists = upgrade.ready_name in tables
        canonical_is_final = (
            canonical_exists
            and _table_has_version_four_compatible_structure(
                connection,
                upgrade.table_name,
            )
        )

        if evidence.phase == "ready":
            ready_is_valid = (
                ready_exists
                and _ready_matches_durable_evidence(
                    connection,
                    upgrade,
                    evidence,
                    canonical_exists=canonical_exists,
                )
            )
            installed_is_valid = (
                not ready_exists
                and canonical_is_final
                and _final_matches_durable_evidence(
                    connection,
                    upgrade,
                    evidence,
                )
            )

            if not ready_is_valid and not installed_is_valid:
                raise RuntimeError(
                    f"{upgrade.table_name} has invalid ready migration "
                    "journal evidence."
                )
        elif not canonical_is_final or not _final_matches_durable_evidence(
            connection,
            upgrade,
            evidence,
        ):
            raise RuntimeError(
                f"{upgrade.table_name} has invalid complete migration "
                "journal evidence."
            )


def _drop_internal_table(connection: Connection, table_name: str) -> None:
    connection.exec_driver_sql(
        f"DROP TABLE {_quote_identifier(table_name)}"
    )


def _rename_table(
    connection: Connection,
    source_name: str,
    destination_name: str,
) -> None:
    connection.exec_driver_sql(
        f"ALTER TABLE {_quote_identifier(source_name)} "
        f"RENAME TO {_quote_identifier(destination_name)}"
    )


def _discard_unverified_replacements(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    with connection.begin():
        tables = _table_names(connection)

        for table_name in (upgrade.shadow_name, upgrade.ready_name):
            if table_name in tables:
                _drop_internal_table(connection, table_name)


def _prepare_replacement_table(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    with connection.begin():
        _create_shadow_table(connection, upgrade)


def _build_ready_replacement(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    with connection.begin():
        _copy_into_shadow(connection, upgrade)

        if not _shadow_matches_canonical(
            connection,
            upgrade,
            upgrade.shadow_name,
        ):
            raise RuntimeError(
                f"{upgrade.table_name} shadow copy verification failed."
            )

        _rename_table(
            connection,
            upgrade.shadow_name,
            upgrade.ready_name,
        )


def _record_ready_replacement(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    with connection.begin():
        evidence = _copy_evidence(
            connection,
            upgrade,
            upgrade.ready_name,
        )

        if evidence is None:
            raise RuntimeError(
                f"{upgrade.table_name} ready copy verification failed."
            )

        _write_migration_evidence(connection, evidence)


def _drop_verified_canonical(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    with connection.begin():
        evidence = _read_migration_evidence(
            connection,
            upgrade.table_name,
        )

        if evidence is None or not _ready_matches_durable_evidence(
            connection,
            upgrade,
            evidence,
            canonical_exists=True,
        ):
            raise RuntimeError(
                f"{upgrade.table_name} has invalid durable ready evidence."
            )

        _drop_internal_table(connection, upgrade.table_name)


def _install_verified_replacement(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
) -> None:
    with connection.begin():
        evidence = _read_migration_evidence(
            connection,
            upgrade.table_name,
        )

        if evidence is None or not _ready_matches_durable_evidence(
            connection,
            upgrade,
            evidence,
            canonical_exists=False,
        ):
            raise RuntimeError(
                f"{upgrade.table_name} has invalid durable ready evidence."
            )

        _rename_table(
            connection,
            upgrade.ready_name,
            upgrade.table_name,
        )


def _complete_final_table(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    *,
    record_journal: bool,
) -> None:
    with connection.begin():
        if not _table_has_final_structure(connection, upgrade.table_name):
            raise RuntimeError(
                f"{upgrade.table_name} replacement structure is invalid."
            )

        evidence = _read_migration_evidence(
            connection,
            upgrade.table_name,
        )

        # Exact default-Space ownership is migration evidence, not a
        # steady-state v4 invariant. Once migration is complete, records may
        # legitimately belong to any existing Space.
        if (
            (record_journal or evidence is not None)
            and not _replacement_has_exact_space(
                connection,
                upgrade.table_name,
            )
        ):
            raise RuntimeError(
                f"{upgrade.table_name} contains invalid Space ownership."
            )

        if evidence is not None and not _final_matches_durable_evidence(
            connection,
            upgrade,
            evidence,
        ):
            raise RuntimeError(
                f"{upgrade.table_name} does not match durable migration "
                "evidence."
            )

        _repair_scoped_indexes(connection, upgrade.table_name)
        _verify_scoped_indexes(connection, upgrade.table_name)
        tables = _table_names(connection)

        for table_name in (upgrade.shadow_name, upgrade.ready_name):
            if table_name in tables:
                _drop_internal_table(connection, table_name)

        if record_journal:
            row_count, digest = _table_evidence(
                connection,
                upgrade,
                upgrade.table_name,
            )
            _write_migration_evidence(
                connection,
                SpaceScopedMigrationEvidence(
                    canonical_table=upgrade.table_name,
                    replacement_table=upgrade.ready_name,
                    phase="complete",
                    source_row_count=row_count,
                    replacement_row_count=row_count,
                    source_digest=digest,
                    replacement_digest=digest,
                    expected_space_id=DEFAULT_SPACE_ID,
                ),
            )


def _migrate_space_scoped_table(
    connection: Connection,
    upgrade: SpaceScopedTableUpgrade,
    *,
    record_journal: bool = True,
) -> None:
    with connection.begin():
        _assert_no_migration_triggers(connection, upgrade)
        tables = _table_names(connection)
        canonical_exists = upgrade.table_name in tables
        shadow_exists = upgrade.shadow_name in tables
        ready_exists = upgrade.ready_name in tables
        canonical_is_final = canonical_exists and _table_has_final_structure(
            connection,
            upgrade.table_name,
        )
        evidence = _read_migration_evidence(
            connection,
            upgrade.table_name,
        )

        if canonical_exists and not canonical_is_final:
            actual_columns = {
                column["name"]
                for column in inspect(connection).get_columns(
                    upgrade.table_name
                )
            }
            expected_legacy_columns = set(
                _legacy_column_names(upgrade.table_name)
            )

            allowed_additive_columns = set(
                VERSION_FOUR_EXCLUDED_COLUMNS.get(
                    upgrade.table_name,
                    frozenset(),
                )
            )
            expected_transitional_columns = (
                expected_legacy_columns | allowed_additive_columns
            )

            if actual_columns not in (
                expected_legacy_columns,
                expected_transitional_columns,
            ):
                raise RuntimeError(
                    f"{upgrade.table_name} has a malformed partial Space "
                    "schema."
                )

            _verify_legacy_indexes(connection, upgrade.table_name)

    if canonical_is_final:
        _complete_final_table(
            connection,
            upgrade,
            record_journal=record_journal,
        )
        return

    if not record_journal:
        raise RuntimeError(
            f"{upgrade.table_name} is not valid for schema version 4."
        )

    if not canonical_exists:
        if shadow_exists or not ready_exists or evidence is None:
            raise RuntimeError(
                f"{upgrade.table_name} is missing without valid durable "
                "ready evidence."
            )

        with connection.begin():
            if not _ready_matches_durable_evidence(
                connection,
                upgrade,
                evidence,
                canonical_exists=False,
            ):
                raise RuntimeError(
                    f"{upgrade.table_name} has invalid durable ready "
                    "evidence."
                )

        _install_verified_replacement(connection, upgrade)
        _complete_final_table(
            connection,
            upgrade,
            record_journal=True,
        )
        return

    if evidence is not None:
        with connection.begin():
            if not ready_exists or not _ready_matches_durable_evidence(
                connection,
                upgrade,
                evidence,
                canonical_exists=True,
            ):
                raise RuntimeError(
                    f"{upgrade.table_name} has invalid durable ready "
                    "evidence."
                )

        if shadow_exists:
            with connection.begin():
                _drop_internal_table(connection, upgrade.shadow_name)
    else:
        _discard_unverified_replacements(connection, upgrade)
        _prepare_replacement_table(connection, upgrade)
        _build_ready_replacement(connection, upgrade)
        _record_ready_replacement(connection, upgrade)

    _drop_verified_canonical(connection, upgrade)
    _install_verified_replacement(connection, upgrade)
    _complete_final_table(
        connection,
        upgrade,
        record_journal=True,
    )


def _ensure_default_space(connection: Connection) -> None:
    with connection.begin():
        fixed_space = connection.execute(
            text(
                "SELECT id FROM spaces WHERE id = :default_space_id"
            ),
            {"default_space_id": DEFAULT_SPACE_ID},
        ).scalar_one_or_none()

        if fixed_space is not None:
            return

        conflicting_space = connection.execute(
            text(
                "SELECT id FROM spaces "
                "WHERE name = :default_space_name COLLATE NOCASE"
            ),
            {"default_space_name": DEFAULT_SPACE_NAME},
        ).scalar_one_or_none()

        if conflicting_space is not None:
            raise DefaultSpaceConflictError(
                "Default Space name conflict: HardHead Works is already "
                "owned by another Space."
            )

        timestamp = datetime.now(timezone.utc)
        connection.execute(
            Base.metadata.tables["spaces"].insert(),
            {
                "id": DEFAULT_SPACE_ID,
                "name": DEFAULT_SPACE_NAME,
                "description": DEFAULT_SPACE_DESCRIPTION,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )


def _verify_default_space(connection: Connection) -> None:
    count = connection.execute(
        text("SELECT COUNT(*) FROM spaces WHERE id = :default_space_id"),
        {"default_space_id": DEFAULT_SPACE_ID},
    ).scalar_one()

    if count != 1:
        raise RuntimeError("The deterministic default Space is missing.")


def _verify_space_scoped_schema(connection: Connection) -> None:
    tables = _table_names(connection)

    for upgrade in SPACE_SCOPED_TABLE_UPGRADES:
        if upgrade.shadow_name in tables or upgrade.ready_name in tables:
            raise RuntimeError(
                f"{upgrade.table_name} has unfinished migration tables."
            )

        if not _table_has_final_structure(connection, upgrade.table_name):
            raise RuntimeError(
                f"{upgrade.table_name} does not match the version 4 schema."
            )

        _verify_scoped_indexes(connection, upgrade.table_name)

    for provenance_table, target_table, target_column in (
        ("inventory_migrations", "inventory_items", "inventory_item_id"),
        ("project_migrations", "projects", "project_id"),
        ("task_migrations", "tasks", "task_id"),
    ):
        mismatch = connection.execute(
            text(
                f"SELECT COUNT(*) FROM {_quote_identifier(provenance_table)} "
                f"AS provenance JOIN {_quote_identifier(target_table)} "
                f"AS target ON target.id = provenance.{target_column} "
                "WHERE provenance.space_id != target.space_id"
            )
        ).scalar_one()

        if mismatch:
            raise RuntimeError(
                f"{provenance_table} contains cross-Space target mappings."
            )


def _verify_version_four_upgrade_source(
    connection: Connection,
) -> None:
    _verify_project_schema(connection)
    _verify_foundation_schema(connection)
    _verify_default_space(connection)
    tables = _table_names(connection)

    for upgrade in SPACE_SCOPED_TABLE_UPGRADES:
        _assert_no_migration_triggers(connection, upgrade)

        if (
            upgrade.shadow_name in tables
            or upgrade.ready_name in tables
        ):
            raise RuntimeError(
                f"{upgrade.table_name} has unfinished migration tables."
            )

        if not _table_has_version_four_compatible_structure(
            connection,
            upgrade.table_name,
        ):
            raise RuntimeError(
                f"{upgrade.table_name} does not match a supported "
                "version 4-to-5 upgrade structure."
            )

        _verify_version_four_compatible_indexes(
            connection,
            upgrade.table_name,
        )

    for provenance_table, target_table, target_column in (
        ("inventory_migrations", "inventory_items", "inventory_item_id"),
        ("project_migrations", "projects", "project_id"),
        ("task_migrations", "tasks", "task_id"),
    ):
        mismatch = connection.execute(
            text(
                f"SELECT COUNT(*) FROM "
                f"{_quote_identifier(provenance_table)} "
                f"AS provenance JOIN "
                f"{_quote_identifier(target_table)} "
                f"AS target ON target.id = provenance.{target_column} "
                "WHERE provenance.space_id != target.space_id"
            )
        ).scalar_one()

        if mismatch:
            raise RuntimeError(
                f"{provenance_table} contains cross-Space "
                "target mappings."
            )

    foreign_key_violations = list(
        connection.exec_driver_sql("PRAGMA foreign_key_check")
    )

    if foreign_key_violations:
        raise RuntimeError(
            "The version 4 upgrade source contains "
            "foreign-key violations."
        )


def _set_sqlite_foreign_keys(
    connection: Connection,
    *,
    enabled: bool,
) -> None:
    if connection.in_transaction():
        raise RuntimeError(
            "SQLite foreign-key mode cannot change during a transaction."
        )

    state = "ON" if enabled else "OFF"
    connection.exec_driver_sql(f"PRAGMA foreign_keys={state}")
    actual = int(
        connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
    )
    connection.commit()

    if actual != int(enabled):
        raise RuntimeError(
            f"SQLite foreign-key mode could not be set to {state}."
        )


def _verify_completed_migration_journal(connection: Connection) -> None:
    _validate_existing_migration_journal(connection)
    rows = connection.execute(
        text(
            f"SELECT canonical_table, phase FROM "
            f"{SPACE_SCOPE_JOURNAL_TABLE} ORDER BY canonical_table"
        )
    ).all()
    expected = {
        upgrade.table_name for upgrade in SPACE_SCOPED_TABLE_UPGRADES
    }
    actual = {str(row[0]) for row in rows}

    if actual != expected or any(row[1] != "complete" for row in rows):
        raise RuntimeError(
            "The version 4 migration journal is not fully complete."
        )


def _drop_migration_journal(connection: Connection) -> None:
    with connection.begin():
        if SPACE_SCOPE_JOURNAL_TABLE in _table_names(connection):
            _drop_internal_table(connection, SPACE_SCOPE_JOURNAL_TABLE)


def _verify_version_four_database(connection: Connection) -> None:
    _verify_project_schema(connection)
    _verify_foundation_schema(connection)
    _verify_default_space(connection)
    _verify_space_scoped_schema(connection)
    foreign_key_violations = list(
        connection.exec_driver_sql("PRAGMA foreign_key_check")
    )

    if foreign_key_violations:
        raise RuntimeError(
            "The version 4 schema contains foreign-key violations."
        )


def _prepare_foundation_schema(
    connection: Connection,
    version: int,
) -> int:
    with connection.begin():
        columns = _project_columns(connection)

        for name, statement in PROJECT_COLUMN_UPGRADES.items():
            if name not in columns:
                connection.exec_driver_sql(statement)

        for statement in PROJECT_INDEX_UPGRADES:
            connection.exec_driver_sql(statement)

        existing_tables = set(inspect(connection).get_table_names())

        for table_name, statement in FOUNDATION_INDEX_UPGRADES:
            if table_name in existing_tables:
                connection.exec_driver_sql(statement)

        _verify_project_schema(connection)
        _verify_foundation_schema(connection)

        if version < FOUNDATION_DATABASE_SCHEMA_VERSION:
            connection.exec_driver_sql(
                f"PRAGMA user_version = {FOUNDATION_DATABASE_SCHEMA_VERSION}"
            )
            return FOUNDATION_DATABASE_SCHEMA_VERSION

    return version


def _ensure_universal_work_columns(
    connection: Connection,
) -> None:
    for table_name, column_name, statement in UNIVERSAL_WORK_COLUMN_UPGRADES:
        upgrade = SPACE_SCOPED_TABLE_UPGRADES_BY_NAME[table_name]

        with connection.begin():
            existing_tables = _table_names(connection)
            physical_names = tuple(
                name
                for name in (
                    table_name,
                    upgrade.shadow_name,
                    upgrade.ready_name,
                )
                if name in existing_tables
            )

            if not physical_names:
                raise RuntimeError(
                    f"{table_name} is missing during the version 5 upgrade."
                )

            for physical_name in physical_names:
                columns = {
                    column["name"]
                    for column in inspect(connection).get_columns(
                        physical_name
                    )
                }

                if column_name in columns:
                    continue

                if physical_name == table_name:
                    physical_statement = statement
                else:
                    physical_statement = statement.replace(
                        f"ALTER TABLE {table_name} ",
                        "ALTER TABLE "
                        f"{_quote_identifier(physical_name)} ",
                        1,
                    )

                connection.exec_driver_sql(physical_statement)


def _table_has_universal_work_augmented_structure(
    connection: Connection,
    table_name: str,
) -> bool:
    database_inspector = inspect(connection)

    if table_name not in database_inspector.get_table_names():
        return False

    actual_names = {
        column["name"]
        for column in database_inspector.get_columns(table_name)
    }
    expected_names = {
        column.name
        for column in Base.metadata.tables[table_name].columns
    }

    return (
        actual_names == expected_names
        and _table_has_version_four_compatible_structure(
            connection,
            table_name,
        )
    )


def _ensure_universal_work_table(
    connection: Connection,
) -> None:
    with connection.begin():
        Base.metadata.tables["work_dependencies"].create(
            bind=connection,
            checkfirst=True,
        )
        _repair_scoped_indexes(connection, "work_dependencies")


def _verify_universal_work_schema(
    connection: Connection,
) -> None:
    for table_name in ("tasks", "projects"):
        if not _table_has_universal_work_augmented_structure(
            connection,
            table_name,
        ):
            raise RuntimeError(
                f"{table_name} does not match the version 5 schema."
            )

        _verify_scoped_indexes(connection, table_name)

    if not _table_has_final_structure(
        connection,
        "work_dependencies",
    ):
        raise RuntimeError(
            "work_dependencies does not match the version 5 schema."
        )

    _verify_scoped_indexes(connection, "work_dependencies")

    actual_checks = {
        constraint.get("name"): _canonical_sql(constraint["sqltext"])
        for constraint in inspect(connection).get_check_constraints(
            "work_dependencies"
        )
    }
    expected_checks = {
        name: _canonical_sql(expression)
        for name, expression in UNIVERSAL_WORK_CHECK_CONSTRAINTS.items()
    }

    if actual_checks != expected_checks:
        raise RuntimeError(
            "work_dependencies check constraints are incomplete."
        )

    foreign_key_violations = list(
        connection.exec_driver_sql("PRAGMA foreign_key_check")
    )

    if foreign_key_violations:
        raise RuntimeError(
            "The version 5 schema contains foreign-key violations."
        )


def _ensure_resource_tables(
    connection: Connection,
) -> None:
    with connection.begin():
        for table_name in RESOURCE_TABLES:
            Base.metadata.tables[table_name].create(
                bind=connection,
                checkfirst=True,
            )
            _repair_scoped_indexes(connection, table_name)


def _verify_resource_schema(
    connection: Connection,
) -> None:
    database_inspector = inspect(connection)

    for table_name in RESOURCE_TABLES:
        if not _table_has_final_structure(
            connection,
            table_name,
        ):
            raise RuntimeError(
                f"{table_name} does not match the version 6 schema."
            )

        _verify_scoped_indexes(connection, table_name)

    for table_name, expected in RESOURCE_CHECK_CONSTRAINTS.items():
        actual = {
            constraint.get("name"): _canonical_sql(
                constraint["sqltext"]
            )
            for constraint
            in database_inspector.get_check_constraints(table_name)
        }
        expected_canonical = {
            name: _canonical_sql(expression)
            for name, expression in expected.items()
        }

        if actual != expected_canonical:
            raise RuntimeError(
                f"{table_name} check constraints are incomplete."
            )

    foreign_key_violations = list(
        connection.exec_driver_sql("PRAGMA foreign_key_check")
    )

    if foreign_key_violations:
        raise RuntimeError(
            "The version 6 schema contains foreign-key violations."
        )


def _ensure_calendar_tables(
    connection: Connection,
) -> None:
    with connection.begin():
        for table_name in CALENDAR_TABLES:
            Base.metadata.tables[table_name].create(
                bind=connection,
                checkfirst=True,
            )
            _repair_scoped_indexes(connection, table_name)


def _verify_calendar_schema(
    connection: Connection,
) -> None:
    database_inspector = inspect(connection)

    for table_name in CALENDAR_TABLES:
        if not _table_has_final_structure(
            connection,
            table_name,
        ):
            raise RuntimeError(
                f"{table_name} does not match the version 7 schema."
            )

        _verify_scoped_indexes(connection, table_name)

    for table_name, expected in CALENDAR_CHECK_CONSTRAINTS.items():
        actual = {
            constraint.get("name"): _canonical_sql(
                constraint["sqltext"]
            )
            for constraint
            in database_inspector.get_check_constraints(table_name)
        }
        expected_canonical = {
            name: _canonical_sql(expression)
            for name, expression in expected.items()
        }

        if actual != expected_canonical:
            raise RuntimeError(
                f"{table_name} check constraints are incomplete."
            )

    foreign_key_violations = list(
        connection.exec_driver_sql("PRAGMA foreign_key_check")
    )

    if foreign_key_violations:
        raise RuntimeError(
            "The version 7 schema contains foreign-key violations."
        )


def apply_schema_upgrades(connection: Connection) -> None:
    if connection.dialect.name != "sqlite":
        return

    if connection.in_transaction():
        raise RuntimeError(
            "Schema upgrades require a connection without an active "
            "transaction."
        )

    version = assert_supported_database_version(connection)
    connection.rollback()

    with connection.begin():
        _validate_existing_migration_journal(connection)

    version = _prepare_foundation_schema(connection, version)
    _ensure_default_space(connection)

    record_journal = version < SPACE_SCOPE_DATABASE_SCHEMA_VERSION

    if record_journal:
        # Current ORM metadata defines the v4 replacement tables. Install
        # nullable v5 additions first so an in-progress v4 migration can
        # build and resume against that current physical shape.
        _ensure_universal_work_columns(connection)
        _ensure_migration_journal(connection)

        try:
            _set_sqlite_foreign_keys(connection, enabled=False)

            for upgrade in SPACE_SCOPED_TABLE_UPGRADES:
                _migrate_space_scoped_table(
                    connection,
                    upgrade,
                    record_journal=True,
                )
        finally:
            if connection.in_transaction():
                connection.rollback()

            _set_sqlite_foreign_keys(connection, enabled=True)

        with connection.begin():
            _verify_version_four_database(connection)

            if SPACE_SCOPE_JOURNAL_TABLE in _table_names(connection):
                _validate_existing_migration_journal(connection)

            _verify_completed_migration_journal(connection)

        _drop_migration_journal(connection)

        with connection.begin():
            _verify_version_four_database(connection)

            if SPACE_SCOPE_JOURNAL_TABLE in _table_names(connection):
                raise RuntimeError(
                    "The version 4 migration journal was not removed."
                )

            connection.exec_driver_sql(
                "PRAGMA user_version = "
                f"{SPACE_SCOPE_DATABASE_SCHEMA_VERSION}"
            )
            version = SPACE_SCOPE_DATABASE_SCHEMA_VERSION

    else:
        # A released schema-v4 database has already completed the destructive
        # Space migration. Validate it without replaying that migration.
        # This verifier also accepts approved partial v5 additions so a
        # failed v4-to-v5 upgrade can resume safely.
        with connection.begin():
            _verify_version_four_upgrade_source(connection)

        _drop_migration_journal(connection)

        with connection.begin():
            if SPACE_SCOPE_JOURNAL_TABLE in _table_names(connection):
                raise RuntimeError(
                    "The version 4 migration journal was not removed."
                )

    # Both paths converge here. These operations are additive/idempotent.
    _ensure_universal_work_columns(connection)

    with connection.begin():
        for upgrade in SPACE_SCOPED_TABLE_UPGRADES:
            _repair_scoped_indexes(
                connection,
                upgrade.table_name,
            )

    _ensure_universal_work_table(connection)

    with connection.begin():
        _verify_universal_work_schema(connection)

        if version < UNIVERSAL_WORK_DATABASE_SCHEMA_VERSION:
            connection.exec_driver_sql(
                "PRAGMA user_version = "
                f"{UNIVERSAL_WORK_DATABASE_SCHEMA_VERSION}"
            )
            version = UNIVERSAL_WORK_DATABASE_SCHEMA_VERSION

    _ensure_resource_tables(connection)

    with connection.begin():
        _verify_resource_schema(connection)

        if version < RESOURCE_DATABASE_SCHEMA_VERSION:
            connection.exec_driver_sql(
                "PRAGMA user_version = "
                f"{RESOURCE_DATABASE_SCHEMA_VERSION}"
            )
            version = RESOURCE_DATABASE_SCHEMA_VERSION

    _ensure_calendar_tables(connection)

    with connection.begin():
        _verify_calendar_schema(connection)

        if version < CALENDAR_DATABASE_SCHEMA_VERSION:
            connection.exec_driver_sql(
                "PRAGMA user_version = "
                f"{CALENDAR_DATABASE_SCHEMA_VERSION}"
            )
