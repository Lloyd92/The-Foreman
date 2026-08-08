"""Local module registration browser acceptance."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.inventory import InventoryPage
from foreman_e2e.modules import ModuleSettings
from foreman_e2e.spaces import SpacesControl
from foreman_e2e.tasks import TasksPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Module acceptance requires the disposable deployment runner.",
)
class ModuleRegistrationTests(BrowserE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.inventory = InventoryPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.tasks = TasksPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.modules = ModuleSettings(
            self.driver,
            self.app,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.spaces = SpacesControl(
            self.driver,
            self.app,
            timeout_seconds=self.config.timeout_seconds,
        )

    def _delete_owned_record(
        self,
        path: str,
        *,
        space_id: str,
        field: str,
        value: str,
    ) -> None:
        records = self.spaces.operational_collection(
            path,
            space_id=space_id,
        )

        for record in records:
            if record.get(field) != value:
                continue

            record_id = record.get("id")

            if not isinstance(record_id, str) or not record_id:
                continue

            self.app.api_request(
                f"{path}/{record_id}",
                method="DELETE",
                headers={
                    "X-Foreman-Space-Id": space_id,
                },
            )

    def test_disable_reload_route_gating_and_retained_data(
        self,
    ) -> None:
        task_title = "E2E Retained Work Task"
        inventory_item = {
            "name": "E2E Retained Inventory",
            "category": "Hardware",
            "location": "E2E Module Shelf",
            "quantity": 9,
            "unit": "pieces",
            "minimum": 3,
            "cost": 8.50,
            "supplier": "E2E Module Supplier",
            "notes": "Must survive module disable and re-enable.",
        }

        self.app.open("tasks")
        space_id = self.spaces.active_space_id()
        self.tasks.create_task(task_title, "high")

        self.app.open("inventory")
        self.inventory.create_item(inventory_item)

        try:
            # Work module: disable through Settings, prove its contributions
            # disappear, and prove deep links canonicalize to Work.
            self.app.open("settings")
            self.assertEqual(self.modules.state("work"), "enabled")
            self.modules.set_enabled("work", False)

            self.app.navigate("work")
            self.assertFalse(
                self.modules.route_link_is_displayed("tasks")
            )
            self.assertFalse(
                self.modules.route_link_is_displayed("projects")
            )

            self.app.open(
                "tasks",
                expected_route="work",
            )
            self.assertEqual(
                self.app.visible_routes(),
                ["work"],
            )

            self.app.open("today")
            self.assertEqual(
                self.modules.visible_contribution_count("work"),
                0,
            )

            # The disabled state itself must survive a fresh application
            # startup before it is changed again.
            self.app.open("settings")
            self.assertEqual(self.modules.state("work"), "disabled")

            self.modules.set_enabled("work", True)

            self.app.navigate("work")
            self.assertTrue(
                self.modules.route_link_is_displayed("tasks")
            )
            self.assertTrue(
                self.modules.route_link_is_displayed("projects")
            )

            self.app.open("tasks")
            self.assertGreater(
                self.modules.visible_contribution_count("work"),
                0,
            )
            self.assertIsNotNone(
                self.tasks.find_row(task_title)
            )

            # Inventory module: same visible Settings workflow and route
            # gating, then prove its existing data returns unchanged.
            self.app.open("settings")
            self.assertEqual(
                self.modules.state("inventory"),
                "enabled",
            )
            self.modules.set_enabled("inventory", False)

            self.app.navigate("resources")
            self.assertFalse(
                self.modules.route_link_is_displayed("inventory")
            )

            self.app.open(
                "inventory",
                expected_route="resources",
            )
            self.assertEqual(
                self.app.visible_routes(),
                ["resources"],
            )

            self.app.open("today")
            self.assertEqual(
                self.modules.visible_contribution_count("inventory"),
                0,
            )

            self.app.open("settings")
            self.assertEqual(
                self.modules.state("inventory"),
                "disabled",
            )

            self.modules.set_enabled("inventory", True)

            self.app.navigate("resources")
            self.assertTrue(
                self.modules.route_link_is_displayed("inventory")
            )

            self.app.open("today")
            self.assertGreater(
                self.modules.visible_contribution_count("inventory"),
                0,
            )

            self.app.open("inventory")
            self.assertIsNotNone(
                self.inventory.find_row(inventory_item["name"])
            )
            self.assertEqual(
                self.inventory.row_values(
                    inventory_item["name"]
                )["quantity"],
                "9 pieces",
            )
        finally:
            # Backend access remains available while a local module is
            # disabled; restore product configuration before cleanup.
            self.modules.reset_enabled("work")
            self.modules.reset_enabled("inventory")

            self._delete_owned_record(
                "/api/tasks",
                space_id=space_id,
                field="title",
                value=task_title,
            )
            self._delete_owned_record(
                "/api/inventory",
                space_id=space_id,
                field="name",
                value=inventory_item["name"],
            )


if __name__ == "__main__":
    unittest.main()
