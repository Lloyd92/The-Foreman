import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import prepare_database_schema
from app.core.module_registry import MODULE_DEFINITIONS
from app.core.schema_upgrades import CURRENT_DATABASE_SCHEMA_VERSION
from app.models.base import Base
from app.models.member import Member
from app.models.module_state import ModuleState
from app.models.organization import Organization
from app.models.organization_space_relationship import (
    OrganizationSpaceRelationship,
)
from app.models.person import Person
from app.models.space import Space
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.schemas.module_registry import (
    ModuleDefinition,
    ModuleStateCreate,
    ModuleStateRead,
)
from app.schemas.organization import OrganizationSpaceRelationshipCreate


FOUNDATION_TABLES = {
    "spaces",
    "people",
    "organizations",
    "organization_space_relationships",
    "members",
    "module_states",
}


class UniversalFoundationSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = (
            Path(self.temporary_directory.name) / "foundation.db"
        )
        self.engine = create_engine(f"sqlite:///{database_path}")

        with self.engine.connect() as connection:
            prepare_database_schema(connection)

        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def test_clean_database_creates_complete_foundation_schema(
        self,
    ) -> None:
        tables = set(inspect(self.engine).get_table_names())
        self.assertTrue(FOUNDATION_TABLES.issubset(tables))

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA user_version"
                ).scalar_one(),
                CURRENT_DATABASE_SCHEMA_VERSION,
            )

            for table_name in FOUNDATION_TABLES - {"spaces"}:
                count = connection.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                ).scalar_one()
                self.assertEqual(count, 0)

            self.assertEqual(
                connection.execute(
                    text("SELECT COUNT(*) FROM spaces")
                ).scalar_one(),
                1,
            )

    def test_future_schema_is_rejected_before_create_all(self) -> None:
        future_engine = create_engine("sqlite:///:memory:")

        try:
            with future_engine.begin() as connection:
                connection.exec_driver_sql(
                    f"PRAGMA user_version = "
                    f"{CURRENT_DATABASE_SCHEMA_VERSION + 1}"
                )

            with future_engine.connect() as connection:
                with patch.object(Base.metadata, "create_all") as create_all:
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "newer than this application supports",
                    ):
                        prepare_database_schema(connection)

                    create_all.assert_not_called()
        finally:
            future_engine.dispose()

    def test_sqlite_foreign_keys_remain_enabled(self) -> None:
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql(
                    "PRAGMA foreign_keys"
                ).scalar_one(),
                1,
            )

    def test_space_names_are_case_insensitively_unique(self) -> None:
        self.session.add(Space(name="hardhead works"))

        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_duplicate_person_and_organization_names_are_valid(self) -> None:
        self.session.add_all(
            [
                Person(display_name="Alex Smith"),
                Person(display_name="Alex Smith"),
                Organization(name="Acme"),
                Organization(name="Acme"),
            ]
        )
        self.session.commit()

        self.assertEqual(self.session.query(Person).count(), 2)
        self.assertEqual(self.session.query(Organization).count(), 2)

    def test_organization_relationship_requires_valid_roots(self) -> None:
        organization = Organization(name="Utility")
        space = Space(name="Household")
        self.session.add_all([organization, space])
        self.session.commit()
        self.session.add(
            OrganizationSpaceRelationship(
                space_id=space.id,
                organization_id=organization.id,
                role="utility",
            )
        )
        self.session.commit()

        self.session.add(
            OrganizationSpaceRelationship(
                space_id="missing-space",
                organization_id=organization.id,
                role="employer",
            )
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

        self.session.rollback()
        self.session.add(
            OrganizationSpaceRelationship(
                space_id=space.id,
                organization_id="missing-organization",
                role="employer",
            )
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

        self.session.rollback()
        self.session.add(
            OrganizationSpaceRelationship(
                space_id=space.id,
                organization_id=organization.id,
                role="utility",
            )
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_member_requires_valid_roots_and_is_unique_per_person_space(
        self,
    ) -> None:
        person = Person(display_name="Amber")
        space = Space(name="Household")
        self.session.add_all([person, space])
        self.session.commit()
        self.session.add(
            Member(
                space_id=space.id,
                person_id=person.id,
                role="household administrator",
            )
        )
        self.session.commit()
        self.session.add(
            Member(
                space_id=space.id,
                person_id=person.id,
                role="member",
            )
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

        self.session.rollback()
        self.session.add(
            Member(
                space_id="missing-space",
                person_id=person.id,
                role="member",
            )
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

        self.session.rollback()
        self.session.add(
            Member(
                space_id=space.id,
                person_id="missing-person",
                role="member",
            )
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_referenced_roots_use_restrict_deletion(self) -> None:
        person = Person(display_name="Amber")
        organization = Organization(name="Utility")
        space = Space(name="Household")
        self.session.add_all([person, organization, space])
        self.session.flush()
        self.session.add_all(
            [
                Member(
                    space_id=space.id,
                    person_id=person.id,
                    role="member",
                ),
                OrganizationSpaceRelationship(
                    space_id=space.id,
                    organization_id=organization.id,
                    role="utility",
                ),
            ]
        )
        self.session.commit()

        for root in (space, person, organization):
            self.session.delete(root)

            with self.assertRaises(IntegrityError):
                self.session.commit()

            self.session.rollback()

    def test_roles_are_normalized_by_typed_schemas(self) -> None:
        member = MemberCreate(
            person_id="person-id",
            role="  Household   Administrator ",
        )
        relationship = OrganizationSpaceRelationshipCreate(
            organization_id="organization-id",
            role=" Service Provider ",
        )

        self.assertEqual(member.role, "household administrator")
        self.assertEqual(relationship.role, "service provider")

    def test_relationship_ids_follow_stable_string_conventions(self) -> None:
        valid_id = "a" * 36
        member = MemberCreate(
            person_id=valid_id,
            role="member",
        )
        relationship = OrganizationSpaceRelationshipCreate(
            organization_id="  organization-id  ",
            role="utility",
        )

        self.assertEqual(member.person_id, valid_id)
        self.assertEqual(
            relationship.organization_id,
            "organization-id",
        )

        schema_cases = (
            (
                MemberCreate,
                {
                    "person_id": "person-id",
                    "role": "member",
                },
                ("person_id",),
            ),
            (
                OrganizationSpaceRelationshipCreate,
                {
                    "organization_id": "organization-id",
                    "role": "utility",
                },
                ("organization_id",),
            ),
        )

        for schema, valid_payload, fields in schema_cases:
            for field_name in fields:
                for invalid_value in ("", "   ", "a" * 37):
                    with self.subTest(
                        schema=schema.__name__,
                        field=field_name,
                        value=invalid_value,
                    ):
                        payload = valid_payload | {
                            field_name: invalid_value,
                        }

                        with self.assertRaises(ValidationError):
                            schema.model_validate(payload)

    def test_persisted_roles_reject_non_normalized_values(self) -> None:
        person = Person(display_name="Amber")
        organization = Organization(name="Utility")
        space = Space(name="Household")
        self.session.add_all([person, organization, space])
        self.session.commit()

        invalid_records = (
            Member(
                space_id=space.id,
                person_id=person.id,
                role="Household Administrator",
            ),
            OrganizationSpaceRelationship(
                space_id=space.id,
                organization_id=organization.id,
                role="service  provider",
            ),
        )

        for record in invalid_records:
            with self.subTest(model=type(record).__name__):
                self.session.add(record)

                with self.assertRaises(IntegrityError):
                    self.session.commit()

                self.session.rollback()

    def test_member_and_module_schemas_exclude_prohibited_fields(self) -> None:
        member_fields = (
            set(MemberCreate.model_fields)
            | set(MemberUpdate.model_fields)
            | set(MemberRead.model_fields)
        )
        self.assertEqual(
            member_fields,
            {
                "id",
                "person_id",
                "role",
                "responsibilities",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(
            set(ModuleStateCreate.model_fields),
            {"module_id", "enabled"},
        )
        self.assertEqual(
            set(ModuleStateRead.model_fields),
            {"module_id", "enabled", "created_at", "updated_at"},
        )
        self.assertEqual(MODULE_DEFINITIONS, ())

        for prohibited_field in (
            "billing",
            "subscription",
            "licensing",
            "plan",
            "tier",
            "entitlement",
            "provisioning",
            "hosting",
            "customer_state",
        ):
            with self.subTest(field=prohibited_field):
                with self.assertRaises(ValidationError):
                    ModuleDefinition.model_validate(
                        {
                            "moduleId": "inventory",
                            "name": "Inventory",
                            "description": "Consumable stock",
                            "defaultEnabled": True,
                            prohibited_field: "prohibited",
                        }
                    )

    def test_static_module_definition_validation_is_strict(self) -> None:
        base_definition = {
            "moduleId": "inventory",
            "name": "Inventory",
            "description": "Consumable stock",
            "defaultEnabled": True,
        }

        for invalid_identifier in ("", "   "):
            with self.subTest(identifier=invalid_identifier):
                with self.assertRaises(ValidationError):
                    ModuleDefinition.model_validate(
                        base_definition
                        | {"moduleId": invalid_identifier}
                    )

        normalized = ModuleDefinition.model_validate(
            base_definition
            | {
                "moduleId": " Inventory.Core ",
                "dependencies": [" Work "],
            }
        )
        self.assertEqual(normalized.module_id, "inventory.core")
        self.assertEqual(normalized.dependencies, ("work",))

        invalid_relationships = (
            {"dependencies": ["work", " WORK "]},
            {"dependencies": ["inventory"]},
            {"contributionLocations": ["account"]},
            {"contributionLocations": ["work", "work"]},
        )

        for update in invalid_relationships:
            with self.subTest(update=update):
                with self.assertRaises(ValidationError):
                    ModuleDefinition.model_validate(
                        base_definition | update
                    )

        first = ModuleDefinition.model_validate(base_definition)
        second = ModuleDefinition.model_validate(
            base_definition | {"moduleId": "work", "name": "Work"}
        )
        self.assertIsInstance(first.dependencies, tuple)
        self.assertIsInstance(first.contribution_locations, tuple)
        self.assertEqual(first.dependencies, ())
        self.assertEqual(second.dependencies, ())

        with self.assertRaises(ValidationError):
            ModuleDefinition.model_validate(
                base_definition | {"unexpected": "value"}
            )

    def test_persisted_module_state_contains_only_local_mutable_state(
        self,
    ) -> None:
        self.session.add(ModuleState(module_id="inventory", enabled=True))
        self.session.commit()

        columns = {
            column["name"]
            for column in inspect(self.engine).get_columns("module_states")
        }
        self.assertEqual(
            columns,
            {"module_id", "enabled", "created_at", "updated_at"},
        )


if __name__ == "__main__":
    unittest.main()
