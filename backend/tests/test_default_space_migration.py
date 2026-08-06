import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.database import prepare_database_schema
from app.core.default_space import (
    DEFAULT_SPACE_DESCRIPTION,
    DEFAULT_SPACE_ID,
    DEFAULT_SPACE_NAME,
)
from app.core.schema_upgrades import (
    CURRENT_DATABASE_SCHEMA_VERSION,
    SPACE_SCOPE_JOURNAL_TABLE,
    SPACE_SCOPED_TABLE_UPGRADES,
    _build_ready_replacement,
    _copy_into_shadow,
    _create_shadow_table,
    _drop_migration_journal,
    _drop_verified_canonical,
    _ensure_default_space,
    _ensure_migration_journal,
    _install_verified_replacement,
    _prepare_replacement_table,
    _record_ready_replacement,
    _repair_scoped_indexes,
    _rename_table,
    _set_sqlite_foreign_keys,
    _table_evidence,
)
from app.models.base import Base
from tests.test_support import create_pre_v4_tables


SCOPED_TABLES = (
    "inventory_items",
    "projects",
    "tasks",
    "inventory_migrations",
    "project_migrations",
    "task_migrations",
)

SPACE_INDEXES = {
    table_name: f"ix_{table_name}_space_id"
    for table_name in SCOPED_TABLES
}

LOCKED_DEFAULT_SPACE_ID = "84be7a97-ee3f-5323-acea-4d98482bc294"
LOCKED_DEFAULT_SPACE_NAME = "HardHead Works"
LOCKED_DEFAULT_SPACE_DESCRIPTION = (
    "Default Space for records created before Space support."
)
LOCKED_JOURNAL_COLUMNS = (
    "canonical_table VARCHAR(80) NOT NULL PRIMARY KEY",
    "replacement_table VARCHAR(120) NOT NULL",
    "phase VARCHAR(20) NOT NULL",
    "source_row_count INTEGER NOT NULL",
    "replacement_row_count INTEGER NOT NULL",
    "source_digest VARCHAR(64) NOT NULL",
    "replacement_digest VARCHAR(64) NOT NULL",
    "expected_space_id VARCHAR(36) NOT NULL",
)
LOCKED_JOURNAL_CHECKS = (
    "CONSTRAINT ck_foreman_v4_journal_phase "
    "CHECK (phase IN ('ready', 'complete'))",
    "CONSTRAINT ck_foreman_v4_journal_source_count "
    "CHECK (source_row_count >= 0)",
    "CONSTRAINT ck_foreman_v4_journal_replacement_count "
    "CHECK (replacement_row_count >= 0)",
)


class DefaultSpaceMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "version-three.db"
        )
        self.engine = create_engine(f"sqlite:///{self.database_path}")

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def create_version_three_database(self) -> None:
        import app.models  # noqa: F401

        with self.engine.begin() as connection:
            create_pre_v4_tables(
                connection,
                set(Base.metadata.tables),
            )
            timestamp = "2026-08-02 09:10:11.123456"
            connection.execute(
                text(
                    """
                    INSERT INTO inventory_items (
                        id, name, category, quantity, unit, minimum,
                        location, cost, supplier, notes,
                        created_at, updated_at
                    ) VALUES (
                        'inventory-1', 'Fastener', 'Hardware', 17.5,
                        'boxes', 3.25, 'Shelf A', 4.75, 'Supplier A',
                        'preserve inventory', :timestamp, :timestamp
                    )
                    """
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO projects (
                        id, name, type, status, priority, progress,
                        start_date, target_date, estimated_cost,
                        description, notes, created_at, updated_at,
                        archived_at
                    ) VALUES (
                        'project-1', 'Workbench', 'build', 'active',
                        'high', 37.5, '2026-08-01', '2026-09-01',
                        725.5, 'preserve description', 'preserve notes',
                        :timestamp, :timestamp, NULL
                    )
                    """
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO project_material_requirements (
                        project_id, inventory_item_id,
                        required_quantity, note
                    ) VALUES (
                        'project-1', 'inventory-1', 6.5,
                        'preserve material'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO tasks (
                        id, title, priority, completed, project_id,
                        created_at, updated_at
                    ) VALUES (
                        'task-1', 'Cut stock', 'high', 0, 'project-1',
                        :timestamp, :timestamp
                    )
                    """
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO inventory_migrations (
                        id, source, source_record_id, inventory_item_id,
                        migrated_at
                    ) VALUES (
                        41, 'browser-local', 'inventory-source',
                        'inventory-1', :timestamp
                    )
                    """
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO project_migrations (
                        id, source, source_record_id, project_id,
                        payload_hash, migrated_at
                    ) VALUES (
                        42, 'browser-local', 'project-source',
                        'project-1', :payload_hash, :timestamp
                    )
                    """
                ),
                {
                    "payload_hash": "a" * 64,
                    "timestamp": timestamp,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO task_migrations (
                        id, source, source_record_id, task_id, migrated_at
                    ) VALUES (
                        43, 'browser-local', 'task-source', NULL, :timestamp
                    )
                    """
                ),
                {"timestamp": timestamp},
            )
            connection.exec_driver_sql("PRAGMA user_version=3")

    def run_upgrade(self) -> None:
        with self.engine.connect() as connection:
            prepare_database_schema(connection)

    @staticmethod
    def application_table_state(connection) -> dict[str, list[tuple]]:
        state = {}

        for table_name in sorted(Base.metadata.tables):
            table = Base.metadata.tables[table_name]
            order_by = ", ".join(
                f'"{column.name}"'
                for column in table.primary_key.columns
            )
            state[table_name] = connection.exec_driver_sql(
                f'SELECT * FROM "{table_name}" ORDER BY {order_by}'
            ).all()

        return state

    @staticmethod
    def insert_complete_journal_entry(
        connection,
        upgrade,
        **overrides,
    ) -> dict[str, object]:
        row_count, digest = _table_evidence(
            connection,
            upgrade,
            upgrade.table_name,
        )
        values = {
            "canonical_table": upgrade.table_name,
            "replacement_table": upgrade.ready_name,
            "phase": "complete",
            "source_row_count": row_count,
            "replacement_row_count": row_count,
            "source_digest": digest,
            "replacement_digest": digest,
            "expected_space_id": LOCKED_DEFAULT_SPACE_ID,
        }
        values.update(overrides)
        connection.execute(
            text(
                f"INSERT INTO {SPACE_SCOPE_JOURNAL_TABLE} ("
                "canonical_table, replacement_table, phase, "
                "source_row_count, replacement_row_count, source_digest, "
                "replacement_digest, expected_space_id"
                ") VALUES ("
                ":canonical_table, :replacement_table, :phase, "
                ":source_row_count, :replacement_row_count, :source_digest, "
                ":replacement_digest, :expected_space_id"
                ")"
            ),
            values,
        )
        return values

    @staticmethod
    def journal_create_sql(
        columns: tuple[str, ...] = LOCKED_JOURNAL_COLUMNS,
        checks: tuple[str, ...] = LOCKED_JOURNAL_CHECKS,
    ) -> str:
        definitions = ", ".join((*columns, *checks))
        return (
            f"CREATE TABLE {SPACE_SCOPE_JOURNAL_TABLE} "
            f"({definitions})"
        )

    def assert_malformed_journal_structure_is_rejected(
        self,
        create_sql: str,
    ) -> None:
        self.create_version_three_database()
        self.run_upgrade()
        first = SPACE_SCOPED_TABLE_UPGRADES[0]

        with self.engine.begin() as connection:
            connection.exec_driver_sql(create_sql)
            self.insert_complete_journal_entry(connection, first)

        with self.engine.connect() as connection:
            tables_before = set(inspect(connection).get_table_names())
            application_before = self.application_table_state(connection)
            journal_before = connection.execute(
                text(f"SELECT * FROM {SPACE_SCOPE_JOURNAL_TABLE}")
            ).one()
            create_sql_before = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = ?",
                (SPACE_SCOPE_JOURNAL_TABLE,),
            ).scalar_one()
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                4,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

        with self.assertRaisesRegex(RuntimeError, "journal is malformed"):
            self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                set(inspect(connection).get_table_names()),
                tables_before,
            )
            self.assertEqual(
                self.application_table_state(connection),
                application_before,
            )
            self.assertEqual(
                connection.execute(
                    text(f"SELECT * FROM {SPACE_SCOPE_JOURNAL_TABLE}")
                ).one(),
                journal_before,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'table' AND name = ?",
                    (SPACE_SCOPE_JOURNAL_TABLE,),
                ).scalar_one(),
                create_sql_before,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                4,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

    def test_version_three_rebuild_preserves_data_and_exact_schema(
        self,
    ) -> None:
        self.create_version_three_database()

        with self.engine.connect() as connection:
            before = {
                table_name: connection.execute(
                    text(f'SELECT * FROM "{table_name}"')
                ).mappings().all()
                for table_name in SCOPED_TABLES
            }
            material_before = connection.execute(
                text("SELECT * FROM project_material_requirements")
            ).mappings().all()

        self.run_upgrade()

        database_inspector = inspect(self.engine)
        self.assertNotIn(
            "space_id",
            Base.metadata.tables[
                "project_material_requirements"
            ].columns,
        )

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )
            self.assertNotIn(
                "sqlite_sequence",
                inspect(connection).get_table_names(),
            )
            self.assertEqual(
                connection.execute(
                    text("SELECT * FROM project_material_requirements")
                ).mappings().all(),
                material_before,
            )

            for table_name in SCOPED_TABLES:
                model_space_column = Base.metadata.tables[
                    table_name
                ].columns["space_id"]
                self.assertIsNone(model_space_column.default)
                self.assertIsNone(model_space_column.server_default)
                columns = database_inspector.get_columns(table_name)
                space_column = next(
                    column
                    for column in columns
                    if column["name"] == "space_id"
                )
                self.assertEqual(str(space_column["type"]), "VARCHAR(36)")
                self.assertFalse(space_column["nullable"])
                self.assertIsNone(space_column["default"])
                table_sql = connection.execute(
                    text(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type = 'table' AND name = :table_name"
                    ),
                    {"table_name": table_name},
                ).scalar_one()
                self.assertIn(
                    "space_id VARCHAR(36) NOT NULL",
                    table_sql,
                )
                self.assertIn(
                    "REFERENCES spaces (id) ON DELETE RESTRICT",
                    table_sql,
                )
                self.assertNotIn("AUTOINCREMENT", table_sql.upper())
                pragma_space_column = next(
                    row
                    for row in connection.exec_driver_sql(
                        f'PRAGMA table_info("{table_name}")'
                    )
                    if row[1] == "space_id"
                )
                self.assertEqual(pragma_space_column[2], "VARCHAR(36)")
                self.assertEqual(pragma_space_column[3], 1)
                self.assertIsNone(pragma_space_column[4])

                indexes = {
                    index["name"]: tuple(index["column_names"])
                    for index in database_inspector.get_indexes(table_name)
                }
                self.assertEqual(
                    indexes[SPACE_INDEXES[table_name]],
                    ("space_id",),
                )
                pragma_indexes = {
                    row[1]: row
                    for row in connection.exec_driver_sql(
                        f'PRAGMA index_list("{table_name}")'
                    )
                }
                self.assertIn(
                    SPACE_INDEXES[table_name],
                    pragma_indexes,
                )
                pragma_index_columns = tuple(
                    row[2]
                    for row in connection.exec_driver_sql(
                        "PRAGMA index_info("
                        f'"{SPACE_INDEXES[table_name]}"'
                        ")"
                    )
                )
                self.assertEqual(pragma_index_columns, ("space_id",))
                foreign_keys = database_inspector.get_foreign_keys(
                    table_name
                )
                space_foreign_key = next(
                    foreign_key
                    for foreign_key in foreign_keys
                    if foreign_key["constrained_columns"] == ["space_id"]
                )
                self.assertEqual(
                    space_foreign_key["referred_table"],
                    "spaces",
                )
                self.assertEqual(
                    space_foreign_key["referred_columns"],
                    ["id"],
                )
                self.assertEqual(
                    space_foreign_key["options"]["ondelete"],
                    "RESTRICT",
                )
                pragma_space_foreign_key = next(
                    row
                    for row in connection.exec_driver_sql(
                        f'PRAGMA foreign_key_list("{table_name}")'
                    )
                    if row[3] == "space_id"
                )
                self.assertEqual(
                    (
                        pragma_space_foreign_key[2],
                        pragma_space_foreign_key[4],
                        pragma_space_foreign_key[6],
                    ),
                    ("spaces", "id", "RESTRICT"),
                )

                after = connection.execute(
                    text(f'SELECT * FROM "{table_name}"')
                ).mappings().all()
                self.assertEqual(len(after), len(before[table_name]))

                for old_row, new_row in zip(
                    before[table_name],
                    after,
                    strict=True,
                ):
                    self.assertEqual(
                        {
                            key: value
                            for key, value in new_row.items()
                            if key != "space_id"
                        },
                        dict(old_row),
                    )
                    self.assertEqual(
                        new_row["space_id"],
                        DEFAULT_SPACE_ID,
                    )

            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "DELETE FROM spaces WHERE id = :default_space_id"
                    ),
                    {"default_space_id": DEFAULT_SPACE_ID},
                )

    def test_default_space_conflict_and_preservation_rules(self) -> None:
        self.assertEqual(DEFAULT_SPACE_ID, LOCKED_DEFAULT_SPACE_ID)
        self.assertEqual(DEFAULT_SPACE_NAME, LOCKED_DEFAULT_SPACE_NAME)
        self.assertEqual(
            DEFAULT_SPACE_DESCRIPTION,
            LOCKED_DEFAULT_SPACE_DESCRIPTION,
        )
        cases = (
            ("none", None),
            ("fixed-edited", None),
            ("fixed-edited-with-original-name-owner", None),
            ("other-space", None),
            ("name-conflict", "Default Space name conflict"),
        )

        for case, expected_error in cases:
            with self.subTest(case=case):
                self.engine.dispose()
                self.database_path.unlink(missing_ok=True)
                self.engine = create_engine(
                    f"sqlite:///{self.database_path}"
                )
                self.create_version_three_database()
                timestamp = "2026-08-02 10:00:00"

                with self.engine.begin() as connection:
                    if case in {
                        "fixed-edited",
                        "fixed-edited-with-original-name-owner",
                    }:
                        connection.execute(
                            text(
                                "INSERT INTO spaces VALUES "
                                "(:id, 'Renamed Space', 'Edited', "
                                ":timestamp, :timestamp)"
                            ),
                            {
                                "id": DEFAULT_SPACE_ID,
                                "timestamp": timestamp,
                            },
                        )

                        if case == "fixed-edited-with-original-name-owner":
                            connection.execute(
                                text(
                                    "INSERT INTO spaces VALUES "
                                    "('other-space', 'HardHead Works', "
                                    "'Other', :timestamp, :timestamp)"
                                ),
                                {"timestamp": timestamp},
                            )
                    elif case == "other-space":
                        connection.execute(
                            text(
                                "INSERT INTO spaces VALUES "
                                "('other-space', 'Workshop', 'Other', "
                                ":timestamp, :timestamp)"
                            ),
                            {"timestamp": timestamp},
                        )
                    elif case == "name-conflict":
                        connection.execute(
                            text(
                                "INSERT INTO spaces VALUES "
                                "('conflict', 'hardhead works', '', "
                                ":timestamp, :timestamp)"
                            ),
                            {"timestamp": timestamp},
                        )

                if expected_error:
                    with self.assertRaisesRegex(
                        RuntimeError,
                        expected_error,
                    ):
                        self.run_upgrade()

                    with self.engine.connect() as connection:
                        self.assertEqual(
                            connection.exec_driver_sql(
                                "PRAGMA user_version"
                            ).scalar_one(),
                            3,
                        )
                        self.assertEqual(
                            connection.execute(
                                text("SELECT COUNT(*) FROM spaces")
                            ).scalar_one(),
                            1,
                        )
                    continue

                self.run_upgrade()
                self.run_upgrade()

                with self.engine.connect() as connection:
                    fixed = connection.execute(
                        text(
                            "SELECT id, name, description, created_at, "
                            "updated_at "
                            "FROM spaces WHERE id = :id"
                        ),
                        {"id": LOCKED_DEFAULT_SPACE_ID},
                    ).one()
                    count = connection.execute(
                        text("SELECT COUNT(*) FROM spaces")
                    ).scalar_one()

                if case in {
                    "fixed-edited",
                    "fixed-edited-with-original-name-owner",
                }:
                    self.assertEqual(
                        fixed,
                        (
                            LOCKED_DEFAULT_SPACE_ID,
                            "Renamed Space",
                            "Edited",
                            timestamp,
                            timestamp,
                        ),
                    )
                    self.assertEqual(
                        count,
                        2
                        if case == "fixed-edited-with-original-name-owner"
                        else 1,
                    )
                else:
                    self.assertEqual(fixed[0], LOCKED_DEFAULT_SPACE_ID)
                    self.assertEqual(fixed[1], LOCKED_DEFAULT_SPACE_NAME)
                    self.assertEqual(
                        fixed[2],
                        LOCKED_DEFAULT_SPACE_DESCRIPTION,
                    )
                    self.assertEqual(fixed[3], fixed[4])
                    self.assertEqual(count, 2 if case == "other-space" else 1)

    def assert_completed_upgrade(self) -> None:
        with self.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                4,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )
            self.assertEqual(
                connection.execute(
                    text("SELECT id, space_id FROM inventory_items")
                ).one(),
                ("inventory-1", LOCKED_DEFAULT_SPACE_ID),
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )
            self.assertNotIn(SPACE_SCOPE_JOURNAL_TABLE, tables)

            for upgrade in SPACE_SCOPED_TABLE_UPGRADES:
                self.assertNotIn(upgrade.shadow_name, tables)
                self.assertNotIn(upgrade.ready_name, tables)
                indexes = {
                    row[1]
                    for row in connection.exec_driver_sql(
                        f'PRAGMA index_list("{upgrade.table_name}")'
                    )
                }
                self.assertIn(
                    f"ix_{upgrade.table_name}_space_id",
                    indexes,
                )

    @staticmethod
    def raise_after(function, message: str):
        def wrapper(*args, **kwargs):
            function(*args, **kwargs)
            raise RuntimeError(message)

        return wrapper

    def test_destructive_phase_failures_resume_without_data_loss(self) -> None:
        cases = (
            (
                "after-replacement-create",
                "app.core.schema_upgrades._build_ready_replacement",
                None,
            ),
            (
                "after-copy-before-ready-evidence",
                "app.core.schema_upgrades._record_ready_replacement",
                None,
            ),
            (
                "after-ready-evidence",
                "app.core.schema_upgrades._drop_verified_canonical",
                None,
            ),
            (
                "after-canonical-drop",
                "app.core.schema_upgrades._install_verified_replacement",
                None,
            ),
            (
                "after-replacement-rename",
                "app.core.schema_upgrades._complete_final_table",
                None,
            ),
            (
                "after-final-verification",
                "app.core.schema_upgrades._drop_migration_journal",
                _drop_migration_journal,
            ),
        )

        for state, target, completed_function in cases:
            with self.subTest(state=state):
                self.engine.dispose()
                self.database_path.unlink(missing_ok=True)
                self.engine = create_engine(
                    f"sqlite:///{self.database_path}"
                )
                self.create_version_three_database()
                side_effect = RuntimeError(state)

                if completed_function is not None:
                    side_effect = self.raise_after(
                        completed_function,
                        state,
                    )

                with patch(target, side_effect=side_effect):
                    with self.assertRaisesRegex(RuntimeError, state):
                        self.run_upgrade()

                with self.engine.connect() as connection:
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "PRAGMA user_version"
                        ).scalar_one(),
                        3,
                    )
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "PRAGMA foreign_keys"
                        ).scalar_one(),
                        1,
                    )
                    tables = set(inspect(connection).get_table_names())
                    first = SPACE_SCOPED_TABLE_UPGRADES[0]
                    inventory_tables = {
                        table_name
                        for table_name in tables
                        if "inventory_items" in table_name
                    }
                    inventory_rows = sum(
                        connection.execute(
                            text(f'SELECT COUNT(*) FROM "{table_name}"')
                        ).scalar_one()
                        for table_name in inventory_tables
                    )
                    self.assertGreaterEqual(inventory_rows, 1)

                    if state == "after-replacement-create":
                        self.assertIn(first.table_name, tables)
                        self.assertIn(first.shadow_name, tables)
                        self.assertEqual(
                            connection.execute(
                                text(
                                    f'SELECT COUNT(*) FROM "{first.shadow_name}"'
                                )
                            ).scalar_one(),
                            0,
                        )
                    elif state == "after-copy-before-ready-evidence":
                        self.assertIn(first.table_name, tables)
                        self.assertIn(first.ready_name, tables)
                        self.assertEqual(
                            connection.execute(
                                text(
                                    f'SELECT COUNT(*) FROM "{first.ready_name}"'
                                )
                            ).scalar_one(),
                            1,
                        )
                    elif state == "after-ready-evidence":
                        self.assertIn(first.table_name, tables)
                        self.assertIn(first.ready_name, tables)
                    elif state == "after-canonical-drop":
                        self.assertNotIn(first.table_name, tables)
                        self.assertIn(first.ready_name, tables)
                    elif state == "after-replacement-rename":
                        self.assertIn(first.table_name, tables)
                        self.assertNotIn(first.ready_name, tables)
                        indexes = {
                            row[1]
                            for row in connection.exec_driver_sql(
                                'PRAGMA index_list("inventory_items")'
                            )
                        }
                        self.assertNotIn(
                            "ix_inventory_items_space_id",
                            indexes,
                        )
                    elif state == "after-final-verification":
                        self.assertNotIn(SPACE_SCOPE_JOURNAL_TABLE, tables)

                    if state not in {
                        "after-replacement-create",
                        "after-copy-before-ready-evidence",
                        "after-final-verification",
                    }:
                        journal = connection.execute(
                            text(
                                f"SELECT phase, source_row_count, "
                                "replacement_row_count, source_digest, "
                                "replacement_digest, expected_space_id "
                                f"FROM {SPACE_SCOPE_JOURNAL_TABLE} "
                                "WHERE canonical_table = 'inventory_items'"
                            )
                        ).one()
                        self.assertEqual(journal[0], "ready")
                        self.assertEqual(journal[1:3], (1, 1))
                        self.assertEqual(journal[3], journal[4])
                        self.assertEqual(len(journal[3]), 64)
                        self.assertEqual(
                            journal[5],
                            LOCKED_DEFAULT_SPACE_ID,
                        )
                    elif state != "after-final-verification":
                        journal_count = connection.execute(
                            text(
                                f"SELECT COUNT(*) FROM "
                                f"{SPACE_SCOPE_JOURNAL_TABLE} "
                                "WHERE canonical_table = 'inventory_items'"
                            )
                        ).scalar_one()
                        self.assertEqual(journal_count, 0)

                self.run_upgrade()
                self.assert_completed_upgrade()

    def test_unverified_shadow_states_keep_canonical_authority(self) -> None:
        for complete_copy in (False, True):
            with self.subTest(complete_copy=complete_copy):
                self.engine.dispose()
                self.database_path.unlink(missing_ok=True)
                self.engine = create_engine(
                    f"sqlite:///{self.database_path}"
                )
                self.create_version_three_database()
                first = SPACE_SCOPED_TABLE_UPGRADES[0]

                with self.engine.connect() as connection:
                    _ensure_default_space(connection)

                    with connection.begin():
                        _create_shadow_table(connection, first)

                        if complete_copy:
                            _copy_into_shadow(connection, first)

                self.run_upgrade()
                self.assert_completed_upgrade()

    def test_indexed_final_table_with_ready_journal_resumes(self) -> None:
        self.create_version_three_database()
        first = SPACE_SCOPED_TABLE_UPGRADES[0]

        with self.engine.connect() as connection:
            _ensure_default_space(connection)
            _ensure_migration_journal(connection)
            _set_sqlite_foreign_keys(connection, enabled=False)

            try:
                _prepare_replacement_table(connection, first)
                _build_ready_replacement(connection, first)
                _record_ready_replacement(connection, first)
                _drop_verified_canonical(connection, first)
                _install_verified_replacement(connection, first)

                with connection.begin():
                    _repair_scoped_indexes(connection, first.table_name)
            finally:
                if connection.in_transaction():
                    connection.rollback()
                _set_sqlite_foreign_keys(connection, enabled=True)

        with self.engine.connect() as connection:
            indexes = {
                row[1]
                for row in connection.exec_driver_sql(
                    'PRAGMA index_list("inventory_items")'
                )
            }
            phase = connection.execute(
                text(
                    f"SELECT phase FROM {SPACE_SCOPE_JOURNAL_TABLE} "
                    "WHERE canonical_table = 'inventory_items'"
                )
            ).scalar_one()
            self.assertIn("ix_inventory_items_space_id", indexes)
            self.assertEqual(phase, "ready")

        self.run_upgrade()
        self.assert_completed_upgrade()

    def test_completed_table_with_later_legacy_table_resumes(self) -> None:
        self.create_version_three_database()

        def fail_on_projects(connection, upgrade):
            if upgrade.table_name == "projects":
                raise RuntimeError("projects-phase-stop")

            _build_ready_replacement(connection, upgrade)

        with patch(
            "app.core.schema_upgrades._build_ready_replacement",
            side_effect=fail_on_projects,
        ):
            with self.assertRaisesRegex(RuntimeError, "projects-phase-stop"):
                self.run_upgrade()

        with self.engine.connect() as connection:
            inventory_columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    'PRAGMA table_info("inventory_items")'
                )
            }
            project_columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    'PRAGMA table_info("projects")'
                )
            }
            journal = connection.execute(
                text(
                    f"SELECT canonical_table, phase FROM "
                    f"{SPACE_SCOPE_JOURNAL_TABLE} ORDER BY canonical_table"
                )
            ).all()
            self.assertIn("space_id", inventory_columns)
            self.assertNotIn("space_id", project_columns)
            self.assertEqual(journal, [("inventory_items", "complete")])
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )

        self.run_upgrade()
        self.assert_completed_upgrade()

    def test_missing_canonical_without_durable_evidence_is_rejected(
        self,
    ) -> None:
        for populated in (False, True):
            with self.subTest(populated=populated):
                self.engine.dispose()
                self.database_path.unlink(missing_ok=True)
                self.engine = create_engine(
                    f"sqlite:///{self.database_path}"
                )
                self.create_version_three_database()
                first = SPACE_SCOPED_TABLE_UPGRADES[0]

                with self.engine.connect() as connection:
                    _ensure_default_space(connection)
                    _ensure_migration_journal(connection)
                    _set_sqlite_foreign_keys(connection, enabled=False)

                    try:
                        with connection.begin():
                            _create_shadow_table(connection, first)

                            if populated:
                                _copy_into_shadow(connection, first)

                            _rename_table(
                                connection,
                                first.shadow_name,
                                first.ready_name,
                            )
                            connection.exec_driver_sql(
                                f'DROP TABLE "{first.table_name}"'
                            )
                    finally:
                        if connection.in_transaction():
                            connection.rollback()
                        _set_sqlite_foreign_keys(connection, enabled=True)

                with self.assertRaisesRegex(
                    RuntimeError,
                    "missing without valid durable ready evidence",
                ):
                    self.run_upgrade()

                with self.engine.connect() as connection:
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "PRAGMA user_version"
                        ).scalar_one(),
                        3,
                    )
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "PRAGMA foreign_keys"
                        ).scalar_one(),
                        1,
                    )

    def assert_missing_canonical_corrupt_evidence_is_rejected(
        self,
        field: str,
        value: object,
    ) -> None:
        self.create_version_three_database()
        first = SPACE_SCOPED_TABLE_UPGRADES[0]

        with self.engine.connect() as connection:
            _ensure_default_space(connection)
            _ensure_migration_journal(connection)
            _set_sqlite_foreign_keys(connection, enabled=False)

            try:
                _prepare_replacement_table(connection, first)
                _build_ready_replacement(connection, first)
                _record_ready_replacement(connection, first)
                _drop_verified_canonical(connection, first)

                with connection.begin():
                    connection.execute(
                        text(
                            f"UPDATE {SPACE_SCOPE_JOURNAL_TABLE} "
                            f"SET {field} = :value "
                            "WHERE canonical_table = :table_name"
                        ),
                        {
                            "value": value,
                            "table_name": first.table_name,
                        },
                    )
            finally:
                if connection.in_transaction():
                    connection.rollback()
                _set_sqlite_foreign_keys(connection, enabled=True)

        with self.engine.connect() as connection:
            tables_before = set(inspect(connection).get_table_names())
            ready_before = connection.execute(
                text(f'SELECT * FROM "{first.ready_name}"')
            ).all()
            journal_before = connection.execute(
                text(
                    f"SELECT * FROM {SPACE_SCOPE_JOURNAL_TABLE} "
                    "WHERE canonical_table = :table_name"
                ),
                {"table_name": first.table_name},
            ).one()
            self.assertNotIn(first.table_name, tables_before)
            self.assertIn(first.ready_name, tables_before)
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "invalid (?:ready )?migration journal evidence",
        ):
            self.run_upgrade()

        with self.engine.connect() as connection:
            tables_after = set(inspect(connection).get_table_names())
            self.assertEqual(tables_after, tables_before)
            self.assertNotIn(first.table_name, tables_after)
            self.assertIn(first.ready_name, tables_after)
            self.assertEqual(
                connection.execute(
                    text(f'SELECT * FROM "{first.ready_name}"')
                ).all(),
                ready_before,
            )
            self.assertEqual(
                connection.execute(
                    text(
                        f"SELECT * FROM {SPACE_SCOPE_JOURNAL_TABLE} "
                        "WHERE canonical_table = :table_name"
                    ),
                    {"table_name": first.table_name},
                ).one(),
                journal_before,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

    def test_missing_canonical_rejects_corrupt_ready_count(self) -> None:
        self.assert_missing_canonical_corrupt_evidence_is_rejected(
            "replacement_row_count",
            99,
        )

    def test_missing_canonical_rejects_corrupt_ready_digest(self) -> None:
        self.assert_missing_canonical_corrupt_evidence_is_rejected(
            "replacement_digest",
            "0" * 64,
        )

    def test_version_four_rejects_invalid_existing_journal(self) -> None:
        cases = (
            (
                "unknown-canonical",
                {
                    "canonical_table": "unknown_table",
                    "replacement_table": "__foreman_v4_unknown_table_ready",
                },
                False,
                "unknown canonical table",
            ),
            (
                "unsupported-phase",
                {"phase": "unsupported"},
                True,
                "invalid migration journal evidence",
            ),
            (
                "wrong-replacement",
                {"replacement_table": "__foreman_v4_wrong_ready"},
                False,
                "invalid migration journal evidence",
            ),
            (
                "wrong-default-space",
                {"expected_space_id": "wrong-space"},
                False,
                "invalid migration journal evidence",
            ),
        )

        for name, overrides, ignore_checks, expected_error in cases:
            with self.subTest(name=name):
                self.engine.dispose()
                self.database_path.unlink(missing_ok=True)
                self.engine = create_engine(
                    f"sqlite:///{self.database_path}"
                )
                self.create_version_three_database()
                self.run_upgrade()
                first = SPACE_SCOPED_TABLE_UPGRADES[0]

                with self.engine.connect() as connection:
                    _ensure_migration_journal(connection)

                    if ignore_checks:
                        connection.exec_driver_sql(
                            "PRAGMA ignore_check_constraints=ON"
                        )
                        connection.commit()

                    try:
                        with connection.begin():
                            inserted = self.insert_complete_journal_entry(
                                connection,
                                first,
                                **overrides,
                            )
                    finally:
                        if ignore_checks:
                            connection.exec_driver_sql(
                                "PRAGMA ignore_check_constraints=OFF"
                            )
                            connection.commit()

                with self.engine.connect() as connection:
                    tables_before = set(
                        inspect(connection).get_table_names()
                    )
                    application_before = self.application_table_state(
                        connection
                    )
                    journal_before = connection.execute(
                        text(
                            f"SELECT * FROM {SPACE_SCOPE_JOURNAL_TABLE}"
                        )
                    ).one()

                with self.assertRaisesRegex(RuntimeError, expected_error):
                    self.run_upgrade()

                with self.engine.connect() as connection:
                    self.assertEqual(
                        set(inspect(connection).get_table_names()),
                        tables_before,
                    )
                    self.assertEqual(
                        self.application_table_state(connection),
                        application_before,
                    )
                    self.assertEqual(
                        connection.execute(
                            text(
                                f"SELECT * FROM "
                                f"{SPACE_SCOPE_JOURNAL_TABLE}"
                            )
                        ).one(),
                        journal_before,
                    )
                    self.assertEqual(
                        journal_before[0],
                        inserted["canonical_table"],
                    )
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "PRAGMA user_version"
                        ).scalar_one(),
                        4,
                    )
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "PRAGMA foreign_keys"
                        ).scalar_one(),
                        1,
                    )

    def test_version_four_valid_stale_journal_is_cleaned(self) -> None:
        self.create_version_three_database()
        self.run_upgrade()
        first = SPACE_SCOPED_TABLE_UPGRADES[0]

        with self.engine.begin() as connection:
            connection.exec_driver_sql(self.journal_create_sql())
            self.insert_complete_journal_entry(connection, first)

        with self.engine.connect() as connection:
            application_before = self.application_table_state(connection)

        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertNotIn(
                SPACE_SCOPE_JOURNAL_TABLE,
                inspect(connection).get_table_names(),
            )
            self.assertEqual(
                self.application_table_state(connection),
                application_before,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                4,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

    def test_version_four_rejects_nullable_journal_without_checks(
        self,
    ) -> None:
        self.assert_malformed_journal_structure_is_rejected(
            self.journal_create_sql(
                columns=(
                    "canonical_table VARCHAR(80) PRIMARY KEY",
                    "replacement_table VARCHAR(120)",
                    "phase VARCHAR(20)",
                    "source_row_count INTEGER",
                    "replacement_row_count INTEGER",
                    "source_digest VARCHAR(64)",
                    "replacement_digest VARCHAR(64)",
                    "expected_space_id VARCHAR(36)",
                ),
                checks=(),
            )
        )

    def test_version_four_rejects_wrong_journal_column_type(self) -> None:
        columns = list(LOCKED_JOURNAL_COLUMNS)
        columns[3] = "source_row_count TEXT NOT NULL"
        self.assert_malformed_journal_structure_is_rejected(
            self.journal_create_sql(columns=tuple(columns))
        )

    def test_version_four_rejects_missing_journal_not_null(self) -> None:
        columns = list(LOCKED_JOURNAL_COLUMNS)
        columns[6] = "replacement_digest VARCHAR(64)"
        self.assert_malformed_journal_structure_is_rejected(
            self.journal_create_sql(columns=tuple(columns))
        )

    def test_version_four_rejects_missing_journal_check(self) -> None:
        self.assert_malformed_journal_structure_is_rejected(
            self.journal_create_sql(checks=LOCKED_JOURNAL_CHECKS[:-1])
        )

    def test_version_four_rejects_weakened_phase_check(self) -> None:
        checks = list(LOCKED_JOURNAL_CHECKS)
        checks[0] = (
            "CONSTRAINT ck_foreman_v4_journal_phase "
            "CHECK (phase IN ('ready', 'complete', 'aborted'))"
        )
        self.assert_malformed_journal_structure_is_rejected(
            self.journal_create_sql(checks=tuple(checks))
        )

    def test_version_four_rejects_weakened_count_check(self) -> None:
        checks = list(LOCKED_JOURNAL_CHECKS)
        checks[1] = (
            "CONSTRAINT ck_foreman_v4_journal_source_count "
            "CHECK (source_row_count >= -1)"
        )
        self.assert_malformed_journal_structure_is_rejected(
            self.journal_create_sql(checks=tuple(checks))
        )

    def test_journal_primary_key_rejects_conflicting_duplicate(self) -> None:
        self.create_version_three_database()
        self.run_upgrade()
        first = SPACE_SCOPED_TABLE_UPGRADES[0]

        with self.engine.connect() as connection:
            _ensure_migration_journal(connection)

            with connection.begin():
                original = self.insert_complete_journal_entry(
                    connection,
                    first,
                )

        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                self.insert_complete_journal_entry(
                    connection,
                    first,
                    replacement_table="__foreman_v4_wrong_ready",
                )

        with self.engine.connect() as connection:
            journal = connection.execute(
                text(f"SELECT * FROM {SPACE_SCOPE_JOURNAL_TABLE}")
            ).one()
            self.assertEqual(journal[0], original["canonical_table"])
            self.assertEqual(journal[1], original["replacement_table"])
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                4,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

    def test_trigger_and_forced_failure_are_restart_safe(self) -> None:
        self.create_version_three_database()

        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TRIGGER unexpected_inventory_trigger "
                "AFTER INSERT ON inventory_items BEGIN SELECT 1; END"
            )

        with self.assertRaisesRegex(RuntimeError, "unsupported triggers"):
            self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER unexpected_inventory_trigger"
            )

        with patch(
            "app.core.schema_upgrades._verify_space_scoped_schema",
            side_effect=RuntimeError("forced final verification failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "forced final verification failure",
            ):
                self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                4,
            )

    def test_missing_and_malformed_space_indexes_are_handled(self) -> None:
        self.create_version_three_database()
        self.run_upgrade()

        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP INDEX ix_inventory_items_space_id"
            )

        self.run_upgrade()
        indexes = {
            index["name"]: tuple(index["column_names"])
            for index in inspect(self.engine).get_indexes("inventory_items")
        }
        self.assertEqual(
            indexes["ix_inventory_items_space_id"],
            ("space_id",),
        )

        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP INDEX ix_inventory_items_space_id"
            )
            connection.exec_driver_sql(
                "CREATE INDEX ix_inventory_items_space_id "
                "ON inventory_items (name)"
            )
            connection.exec_driver_sql("PRAGMA user_version=3")

        with self.assertRaisesRegex(RuntimeError, "index .* is malformed"):
            self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )

    def test_malformed_partial_space_column_is_rejected(self) -> None:
        self.create_version_three_database()

        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE inventory_items "
                "ADD COLUMN space_id VARCHAR(36)"
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "malformed partial Space schema",
        ):
            self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                3,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )


if __name__ == "__main__":
    unittest.main()
