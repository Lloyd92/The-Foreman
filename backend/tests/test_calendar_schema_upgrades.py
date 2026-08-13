import tempfile
import unittest
from datetime import date, datetime, time, timezone
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.core.database import prepare_database_schema
from app.core.default_space import DEFAULT_SPACE_ID
from app.core.schema_upgrades import (
    CALENDAR_DATABASE_SCHEMA_VERSION,
    CURRENT_DATABASE_SCHEMA_VERSION,
    get_database_schema_version,
)
from app.models.base import Base
from app.services.recovery import CURRENT_REQUIRED_DATABASE_TABLES

import app.models  # noqa: F401


CALENDAR_TABLES = {
    "calendar_entries",
    "calendar_series",
    "calendar_series_exclusions",
    "calendar_settings",
    "work_calendar_relationships",
}


class CalendarSchemaUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = (
            Path(self.temp_directory.name)
            / "calendar-schema.sqlite3"
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

    def create_version_six_database(self) -> None:
        self.run_upgrade()

        drop_order = (
            "work_calendar_relationships",
            "calendar_series_exclusions",
            "calendar_entries",
            "calendar_series",
            "calendar_settings",
        )

        with self.engine.begin() as connection:
            for table_name in drop_order:
                connection.exec_driver_sql(
                    f'DROP TABLE "{table_name}"'
                )

            connection.exec_driver_sql(
                "PRAGMA user_version = 6"
            )

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                6,
            )

    def test_fresh_database_reaches_schema_seven(self) -> None:
        self.run_upgrade()

        database_inspector = inspect(self.engine)
        tables = set(database_inspector.get_table_names())

        self.assertTrue(CALENDAR_TABLES.issubset(tables))

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )
            self.assertGreaterEqual(
                CURRENT_DATABASE_SCHEMA_VERSION,
                CALENDAR_DATABASE_SCHEMA_VERSION,
            )
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_version_six_database_adds_calendar_schema_without_data_loss(
        self,
    ) -> None:
        self.create_version_six_database()

        timestamp = datetime(
            2026,
            8,
            12,
            20,
            0,
            tzinfo=timezone.utc,
        )

        with self.engine.begin() as connection:
            connection.execute(
                Base.metadata.tables["spaces"].insert(),
                {
                    "id": "space-preserved-v6",
                    "name": "Preserved v6 Space",
                    "description": "Must survive v7 upgrade",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
            )

        prior_tables = (
            set(Base.metadata.tables)
            - CALENDAR_TABLES
        )

        with self.engine.connect() as connection:
            before_counts = {
                table_name: connection.execute(
                    select(
                        func.count()
                    ).select_from(
                        Base.metadata.tables[table_name]
                    )
                ).scalar_one()
                for table_name in prior_tables
            }

        self.run_upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

            preserved = connection.execute(
                select(
                    Base.metadata.tables["spaces"].c.description
                ).where(
                    Base.metadata.tables["spaces"].c.id
                    == "space-preserved-v6"
                )
            ).scalar_one()

            self.assertEqual(
                preserved,
                "Must survive v7 upgrade",
            )

            after_counts = {
                table_name: connection.execute(
                    select(
                        func.count()
                    ).select_from(
                        Base.metadata.tables[table_name]
                    )
                ).scalar_one()
                for table_name in prior_tables
            }

            self.assertEqual(after_counts, before_counts)

            for table_name in CALENDAR_TABLES:
                count = connection.exec_driver_sql(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).scalar_one()
                self.assertEqual(count, 0)

    def test_partial_version_seven_table_creation_resumes_idempotently(
        self,
    ) -> None:
        self.create_version_six_database()

        with self.engine.begin() as connection:
            Base.metadata.tables["calendar_settings"].create(
                bind=connection,
            )
            Base.metadata.tables["calendar_entries"].create(
                bind=connection,
            )

        self.run_upgrade()
        first_tables = set(inspect(self.engine).get_table_names())

        self.assertTrue(CALENDAR_TABLES.issubset(first_tables))

        with self.engine.connect() as connection:
            self.assertEqual(
                get_database_schema_version(connection),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

        self.run_upgrade()
        restarted_tables = set(
            inspect(self.engine).get_table_names()
        )

        self.assertEqual(restarted_tables, first_tables)

    def test_calendar_storage_constraints_and_lifecycle(self) -> None:
        self.run_upgrade()

        timestamp = datetime(
            2026,
            8,
            12,
            20,
            0,
            tzinfo=timezone.utc,
        )

        people = Base.metadata.tables["people"]
        members = Base.metadata.tables["members"]
        entries = Base.metadata.tables["calendar_entries"]
        series = Base.metadata.tables["calendar_series"]
        exclusions = Base.metadata.tables[
            "calendar_series_exclusions"
        ]
        relationships = Base.metadata.tables[
            "work_calendar_relationships"
        ]

        with self.engine.begin() as connection:
            person_result = connection.execute(
                people.insert().values(
                    display_name="Calendar Person",
                )
            )
            person_id = person_result.inserted_primary_key[0]

            member_result = connection.execute(
                members.insert().values(
                    space_id=DEFAULT_SPACE_ID,
                    person_id=person_id,
                    role="member",
                )
            )
            member_id = member_result.inserted_primary_key[0]

            connection.execute(
                entries.insert().values(
                    id="entry-timed",
                    space_id=DEFAULT_SPACE_ID,
                    member_id=member_id,
                    kind="commitment",
                    title="Timed commitment",
                    all_day=False,
                    start_at=datetime(
                        2026,
                        8,
                        13,
                        12,
                        0,
                        tzinfo=timezone.utc,
                    ),
                    end_at=datetime(
                        2026,
                        8,
                        13,
                        13,
                        0,
                        tzinfo=timezone.utc,
                    ),
                    timezone_name="America/New_York",
                )
            )

            connection.execute(
                entries.insert().values(
                    id="entry-all-day",
                    space_id=DEFAULT_SPACE_ID,
                    kind="event",
                    title="All-day event",
                    all_day=True,
                    start_date=date(2026, 8, 14),
                    end_date=date(2026, 8, 15),
                    timezone_name="America/New_York",
                )
            )

            connection.execute(
                series.insert().values(
                    id="series-weekly",
                    space_id=DEFAULT_SPACE_ID,
                    member_id=member_id,
                    kind="commitment",
                    title="Weekly routine",
                    frequency="weekly",
                    interval_value=1,
                    weekday_mask=31,
                    anchor_date=date(2026, 8, 10),
                    local_start_time=time(6, 0),
                    duration_minutes=510,
                    timezone_name="America/New_York",
                )
            )

            connection.execute(
                exclusions.insert().values(
                    id="exclusion-1",
                    space_id=DEFAULT_SPACE_ID,
                    series_id="series-weekly",
                    excluded_date=date(2026, 8, 12),
                )
            )

            connection.execute(
                relationships.insert().values(
                    id="relationship-missing-calendar",
                    space_id=DEFAULT_SPACE_ID,
                    work_type="task",
                    work_id="missing-work-evidence",
                    calendar_type="entry",
                    calendar_id="deleted-calendar-evidence",
                    note="Relationship evidence survives target loss.",
                    created_at=timestamp,
                )
            )

        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(
                    entries.insert().values(
                        id="entry-invalid-shape",
                        space_id=DEFAULT_SPACE_ID,
                        kind="event",
                        title="Invalid",
                        all_day=True,
                        start_at=timestamp,
                        end_at=timestamp,
                        timezone_name="America/New_York",
                    )
                )

        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(
                    series.insert().values(
                        id="series-invalid-weekdays",
                        space_id=DEFAULT_SPACE_ID,
                        kind="event",
                        title="Invalid series",
                        frequency="daily",
                        interval_value=1,
                        weekday_mask=1,
                        anchor_date=date(2026, 8, 12),
                        local_start_time=time(8, 0),
                        duration_minutes=60,
                        timezone_name="America/New_York",
                    )
                )

        with self.engine.begin() as connection:
            connection.execute(
                members.delete().where(
                    members.c.id == member_id
                )
            )

        with self.engine.connect() as connection:
            entry_member = connection.execute(
                select(entries.c.member_id).where(
                    entries.c.id == "entry-timed"
                )
            ).scalar_one()

            series_member = connection.execute(
                select(series.c.member_id).where(
                    series.c.id == "series-weekly"
                )
            ).scalar_one()

            self.assertIsNone(entry_member)
            self.assertIsNone(series_member)

        with self.engine.begin() as connection:
            connection.execute(
                series.delete().where(
                    series.c.id == "series-weekly"
                )
            )

        with self.engine.connect() as connection:
            exclusion_count = connection.execute(
                select(exclusions.c.id).where(
                    exclusions.c.series_id
                    == "series-weekly"
                )
            ).all()

            self.assertEqual(exclusion_count, [])

            relationship = connection.execute(
                select(
                    relationships.c.calendar_id,
                    relationships.c.note,
                ).where(
                    relationships.c.id
                    == "relationship-missing-calendar"
                )
            ).one()

            self.assertEqual(
                relationship.calendar_id,
                "deleted-calendar-evidence",
            )

            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                ).all(),
                [],
            )

    def test_recovery_contract_requires_all_calendar_tables(
        self,
    ) -> None:
        self.assertTrue(
            CALENDAR_TABLES.issubset(
                CURRENT_REQUIRED_DATABASE_TABLES
            )
        )


if __name__ == "__main__":
    unittest.main()
