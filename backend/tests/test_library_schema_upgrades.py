import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select

from app.core.database import prepare_database_schema
from app.core.schema_upgrades import (
    CURRENT_DATABASE_SCHEMA_VERSION,
    LIBRARY_DATABASE_SCHEMA_VERSION,
    get_database_schema_version,
)
from app.models.base import Base
from app.services.recovery import CURRENT_REQUIRED_DATABASE_TABLES

import app.models  # noqa: F401


LIBRARY_TABLES = {
    "library_records",
    "library_relationships",
}


class LibrarySchemaUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = (
            Path(self.temp_directory.name)
            / "library-schema.sqlite3"
        )
        self.engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_directory.cleanup()

    def run_upgrade(self) -> None:
        with self.engine.connect() as connection:
            prepare_database_schema(connection)

    def create_version_eight_database(self) -> None:
        self.run_upgrade()

        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                'DROP TABLE "library_relationships"'
            )
            connection.exec_driver_sql(
                'DROP TABLE "library_records"'
            )
            connection.exec_driver_sql(
                "PRAGMA user_version = 8"
            )

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                8,
            )

    def test_fresh_database_reaches_schema_nine(self) -> None:
        self.run_upgrade()

        tables = set(inspect(self.engine).get_table_names())

        self.assertTrue(LIBRARY_TABLES.issubset(tables))

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                LIBRARY_DATABASE_SCHEMA_VERSION,
            )
            self.assertEqual(
                CURRENT_DATABASE_SCHEMA_VERSION,
                LIBRARY_DATABASE_SCHEMA_VERSION,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_version_eight_adds_library_without_data_loss(self) -> None:
        self.create_version_eight_database()

        timestamp = datetime(
            2026,
            8,
            14,
            16,
            0,
            tzinfo=timezone.utc,
        )

        with self.engine.begin() as connection:
            connection.execute(
                Base.metadata.tables["spaces"].insert(),
                {
                    "id": "space-preserved-v8",
                    "name": "Preserved v8 Space",
                    "description": "Must survive v9 upgrade",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )

        prior_tables = set(Base.metadata.tables) - LIBRARY_TABLES

        with self.engine.connect() as connection:
            before_counts = {
                table_name: connection.execute(
                    select(func.count()).select_from(
                        Base.metadata.tables[table_name]
                    )
                ).scalar_one()
                for table_name in prior_tables
            }

        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                9,
            )

            preserved = connection.execute(
                select(
                    Base.metadata.tables["spaces"].c.description
                ).where(
                    Base.metadata.tables["spaces"].c.id
                    == "space-preserved-v8"
                )
            ).scalar_one()

            self.assertEqual(
                preserved,
                "Must survive v9 upgrade",
            )

            after_counts = {
                table_name: connection.execute(
                    select(func.count()).select_from(
                        Base.metadata.tables[table_name]
                    )
                ).scalar_one()
                for table_name in prior_tables
            }

            self.assertEqual(after_counts, before_counts)
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_schema_nine_upgrade_is_idempotent(self) -> None:
        self.run_upgrade()
        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                9,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_recovery_requires_library_tables(self) -> None:
        self.assertTrue(
            LIBRARY_TABLES.issubset(
                CURRENT_REQUIRED_DATABASE_TABLES
            )
        )


if __name__ == "__main__":
    unittest.main()
