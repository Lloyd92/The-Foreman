from unittest.mock import patch

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.module_state import ModuleState
from app.schemas.module_registry import ModuleDefinition
from app.services import modules as module_service
from test_support import ApiTestCase, DatabaseTestCase


class ModulesApiTests(ApiTestCase):
    async def test_registry_defaults_require_no_seed_rows(self) -> None:
        response = await self.client.get("/api/modules")

        self.assertEqual(response.status_code, 200)
        modules = response.json()

        self.assertEqual(
            [module["moduleId"] for module in modules],
            ["work", "inventory"],
        )
        self.assertEqual(
            modules[0]["contributionLocations"],
            ["today", "work"],
        )
        self.assertEqual(
            modules[1]["contributionLocations"],
            ["today", "resources"],
        )

        for module in modules:
            with self.subTest(module=module["moduleId"]):
                self.assertTrue(module["enabled"])
                self.assertTrue(module["defaultEnabled"])
                self.assertEqual(module["health"], "ready")
                self.assertEqual(
                    module["dataRetentionBehavior"],
                    "retain",
                )
                self.assertEqual(module["dependencies"], [])

        with SessionLocal() as session:
            self.assertEqual(
                list(session.scalars(select(ModuleState))),
                [],
            )

    async def test_state_changes_are_installation_wide(self) -> None:
        created_space = await self.client.post(
            "/api/spaces",
            json={"name": "Workshop"},
        )
        self.assertEqual(created_space.status_code, 201)
        space_id = created_space.json()["id"]

        disabled = await self.client.patch(
            "/api/modules/inventory",
            headers={"X-Foreman-Space-Id": space_id},
            json={"enabled": False},
        )

        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()["enabled"])
        self.assertEqual(
            disabled.json()["dataRetentionBehavior"],
            "retain",
        )

        # Module configuration is installation-wide, not Space-scoped.
        read_without_space = await self.client.get(
            "/api/modules/inventory"
        )
        self.assertEqual(read_without_space.status_code, 200)
        self.assertFalse(read_without_space.json()["enabled"])

        with SessionLocal() as session:
            states = list(
                session.scalars(
                    select(ModuleState).order_by(
                        ModuleState.module_id
                    )
                )
            )

            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].module_id, "inventory")
            self.assertFalse(states[0].enabled)

        enabled = await self.client.patch(
            "/api/modules/inventory",
            json={"enabled": True},
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.json()["enabled"])

        with SessionLocal() as session:
            state = session.get(ModuleState, "inventory")
            self.assertIsNotNone(state)
            self.assertTrue(state.enabled)

    async def test_default_state_is_not_seeded_by_idempotent_write(
        self,
    ) -> None:
        response = await self.client.patch(
            "/api/modules/work",
            json={"enabled": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["enabled"])

        with SessionLocal() as session:
            self.assertIsNone(
                session.get(ModuleState, "work")
            )

    async def test_missing_module_and_invalid_update_are_controlled(
        self,
    ) -> None:
        missing = await self.client.get("/api/modules/missing")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["detail"]["code"],
            "MODULE_NOT_FOUND",
        )

        missing_update = await self.client.patch(
            "/api/modules/missing",
            json={"enabled": False},
        )
        self.assertEqual(missing_update.status_code, 404)
        self.assertEqual(
            missing_update.json()["detail"]["code"],
            "MODULE_NOT_FOUND",
        )

        invalid = await self.client.patch(
            "/api/modules/work",
            json={},
        )
        self.assertEqual(invalid.status_code, 422)


class ModuleDependencyServiceTests(DatabaseTestCase):
    def registry_context(
        self,
        definitions: tuple[ModuleDefinition, ...],
    ):
        definitions_by_id = {
            definition.module_id: definition
            for definition in definitions
        }

        return (
            patch.object(
                module_service,
                "MODULE_DEFINITIONS",
                definitions,
            ),
            patch.object(
                module_service,
                "get_module_definition",
                side_effect=definitions_by_id.get,
            ),
        )

    def test_enable_requires_enabled_dependencies(self) -> None:
        definitions = (
            ModuleDefinition(
                module_id="foundation",
                name="Foundation",
                description="Synthetic dependency.",
                default_enabled=False,
            ),
            ModuleDefinition(
                module_id="dependent",
                name="Dependent",
                description="Synthetic dependent.",
                dependencies=("foundation",),
                default_enabled=False,
            ),
        )
        registry_patch, lookup_patch = self.registry_context(
            definitions
        )

        with registry_patch, lookup_patch:
            with self.assertRaises(
                module_service.ModuleDependenciesUnsatisfiedError
            ):
                module_service.set_module_enabled(
                    self.session,
                    "dependent",
                    True,
                )

            foundation = module_service.set_module_enabled(
                self.session,
                "foundation",
                True,
            )
            self.assertTrue(foundation.enabled)

            dependent = module_service.set_module_enabled(
                self.session,
                "dependent",
                True,
            )
            self.assertTrue(dependent.enabled)

    def test_disable_rejects_enabled_dependents(self) -> None:
        definitions = (
            ModuleDefinition(
                module_id="foundation",
                name="Foundation",
                description="Synthetic dependency.",
                default_enabled=True,
            ),
            ModuleDefinition(
                module_id="dependent",
                name="Dependent",
                description="Synthetic dependent.",
                dependencies=("foundation",),
                default_enabled=True,
            ),
        )
        registry_patch, lookup_patch = self.registry_context(
            definitions
        )

        with registry_patch, lookup_patch:
            with self.assertRaises(
                module_service.ModuleEnabledDependentsError
            ):
                module_service.set_module_enabled(
                    self.session,
                    "foundation",
                    False,
                )

            dependent = module_service.set_module_enabled(
                self.session,
                "dependent",
                False,
            )
            self.assertFalse(dependent.enabled)

            foundation = module_service.set_module_enabled(
                self.session,
                "foundation",
                False,
            )
            self.assertFalse(foundation.enabled)


if __name__ == "__main__":
    import unittest

    unittest.main()
