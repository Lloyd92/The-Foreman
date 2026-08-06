from sqlalchemy import inspect
from sqlalchemy.engine import Connection

CURRENT_DATABASE_SCHEMA_VERSION = 3

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


def apply_schema_upgrades(connection: Connection) -> None:
    if connection.dialect.name != "sqlite":
        return

    version = assert_supported_database_version(connection)

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

    if version < CURRENT_DATABASE_SCHEMA_VERSION:
        connection.exec_driver_sql(
            f"PRAGMA user_version = "
            f"{CURRENT_DATABASE_SCHEMA_VERSION}"
        )
