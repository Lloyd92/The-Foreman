"""v0.8.2 Resources browser compatibility acceptance."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.care import CarePage
from foreman_e2e.inventory import InventoryPage
from foreman_e2e.modules import ModuleSettings
from foreman_e2e.spaces import SpacesControl
from foreman_e2e.tools import ToolsPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Resources acceptance requires the disposable deployment runner.",
)
class ResourcesAcceptanceTests(BrowserE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.tools = ToolsPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.inventory = InventoryPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.care = CarePage(
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

    def _resource_metric(self, element_id: str) -> str:
        return self.app.text_by_id(element_id)

    def test_resources_crud_and_factual_overview(self) -> None:
        tool = {
            "name": "E2E Cordless Drill",
            "category": "Power Tools",
            "condition": "Good",
            "location": "E2E Tool Cabinet",
            "availability": "Available",
            "notes": "Disposable Resources acceptance.",
        }
        edited_tool = {
            **tool,
            "name": "E2E Cordless Drill Kit",
            "condition": "Serviced",
            "location": "E2E Tool Cabinet B",
        }
        inventory = {
            "name": "E2E Resources Fasteners",
            "category": "Hardware",
            "location": "E2E Parts Bin",
            "quantity": 2,
            "unit": "boxes",
            "minimum": 5,
            "cost": 4.25,
            "supplier": "E2E Supplier",
            "notes": "Low-stock Resources acceptance record.",
        }

        self.app.open("tools")
        space_id = self.spaces.active_space_id()

        self.tools.create_tool(tool)

        created_tool = self.spaces.operational_collection(
            "/api/tools",
            space_id=space_id,
        )
        tool_record = next(
            record
            for record in created_tool
            if record.get("name") == tool["name"]
        )
        tool_id = tool_record["id"]

        try:
            self.assertEqual(
                self.tools.row_values(tool["name"]),
                {
                    "name": "E2E Cordless Drill",
                    "category": "Power Tools",
                    "condition": "Good",
                    "location": "E2E Tool Cabinet",
                    "availability": "Available",
                },
            )

            self.tools.open_maintenance(tool["name"])
            self.tools.add_maintenance(
                maintenance_type="Inspection",
                performed_at="2026-08-10T12:30",
                notes="Factual isolated maintenance history.",
            )
            self.assertIn(
                "Inspection",
                self.tools.maintenance_text(),
            )
            self.tools.close_maintenance()

            self.tools.edit_tool(
                tool["name"],
                edited_tool,
            )
            self.assertEqual(
                self.tools.row_values(
                    edited_tool["name"]
                )["condition"],
                "Serviced",
            )

            self.app.open("inventory")
            self.inventory.create_item(inventory)

            self.app.open("care")
            self.care.create_plan({
                "name": "E2E Drill Inspection",
                "careType": "inspection",
                "toolId": tool_id,
                "description": "Inspect the drill.",
                "frequencyValue": 3,
                "frequencyUnit": "months",
                "notes": "Frequency is metadata only.",
            })

            care_values = self.care.row_values(
                "E2E Drill Inspection"
            )

            self.assertEqual(
                care_values["careType"],
                "inspection",
            )
            self.assertEqual(
                care_values["tool"],
                edited_tool["name"],
            )
            self.assertEqual(
                care_values["frequency"],
                "3 months",
            )

            self.app.open("resources")

            self.assertEqual(
                self._resource_metric(
                    "resources-tools-total"
                ),
                "1",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-inventory-total"
                ),
                "1",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-inventory-attention"
                ),
                "1",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-care-total"
                ),
                "1",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-care-linked"
                ),
                "1",
            )

            self.app.open("care")
            self.care.delete_plan(
                "E2E Drill Inspection"
            )

            self.app.open("inventory")
            self.inventory.delete_item(
                inventory["name"]
            )

            # Maintenance history intentionally blocks Tool deletion.
            # Remove this test-owned maintenance record through the
            # backend-authoritative disposable API before deleting Tool.
            maintenance = self.spaces.operational_collection(
                f"/api/tools/{tool_id}/maintenance",
                space_id=space_id,
            )
            for record in maintenance:
                record_id = record.get("id")
                if isinstance(record_id, str) and record_id:
                    self.app.api_request(
                        f"/api/tools/{tool_id}/maintenance/{record_id}",
                        method="DELETE",
                        headers={
                            "X-Foreman-Space-Id": space_id,
                        },
                    )

            self.app.open("tools")
            self.tools.delete_tool(
                edited_tool["name"]
            )

            self.app.open("resources")
            self.assertEqual(
                self._resource_metric(
                    "resources-tools-total"
                ),
                "0",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-inventory-total"
                ),
                "0",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-inventory-attention"
                ),
                "0",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-care-total"
                ),
                "0",
            )
            self.assertEqual(
                self._resource_metric(
                    "resources-care-linked"
                ),
                "0",
            )
        finally:
            self._delete_owned_record(
                "/api/care-plans",
                space_id=space_id,
                field="name",
                value="E2E Drill Inspection",
            )
            self._delete_owned_record(
                "/api/inventory",
                space_id=space_id,
                field="name",
                value=inventory["name"],
            )

            tools = self.spaces.operational_collection(
                "/api/tools",
                space_id=space_id,
            )

            for record in tools:
                if record.get("name") not in {
                    tool["name"],
                    edited_tool["name"],
                }:
                    continue

                record_id = record.get("id")

                if not isinstance(record_id, str) or not record_id:
                    continue

                maintenance = self.spaces.operational_collection(
                    f"/api/tools/{record_id}/maintenance",
                    space_id=space_id,
                )

                for maintenance_record in maintenance:
                    maintenance_id = maintenance_record.get("id")

                    if (
                        isinstance(maintenance_id, str)
                        and maintenance_id
                    ):
                        self.app.api_request(
                            f"/api/tools/{record_id}/maintenance/"
                            f"{maintenance_id}",
                            method="DELETE",
                            headers={
                                "X-Foreman-Space-Id": space_id,
                            },
                        )

                self.app.api_request(
                    f"/api/tools/{record_id}",
                    method="DELETE",
                    headers={
                        "X-Foreman-Space-Id": space_id,
                    },
                )

    def test_care_remains_usable_when_tools_is_disabled(self) -> None:
        care_name = "E2E Independent Property Care"

        self.app.open("care")
        space_id = self.spaces.active_space_id()

        self.care.create_plan({
            "name": care_name,
            "careType": "cleaning",
            "description": "Independent Care acceptance.",
            "frequencyValue": 2,
            "frequencyUnit": "weeks",
            "notes": "Must survive Tools module disable.",
        })

        try:
            self.app.open("settings")
            self.assertEqual(
                self.modules.state("tools"),
                "enabled",
            )
            self.assertEqual(
                self.modules.state("care"),
                "enabled",
            )

            self.modules.set_enabled(
                "tools",
                False,
            )

            self.app.navigate("resources")
            self.assertFalse(
                self.modules.route_link_is_displayed(
                    "tools"
                )
            )
            self.assertTrue(
                self.modules.route_link_is_displayed(
                    "care"
                )
            )

            self.app.open(
                "tools",
                expected_route="resources",
            )
            self.assertEqual(
                self.app.visible_routes(),
                ["resources"],
            )

            self.app.open("care")
            self.assertIsNotNone(
                self.care.find_row(care_name)
            )
            self.assertEqual(
                self.care.row_values(
                    care_name
                )["frequency"],
                "2 weeks",
            )

            self.app.open("settings")
            self.assertEqual(
                self.modules.state("tools"),
                "disabled",
            )
            self.assertEqual(
                self.modules.state("care"),
                "enabled",
            )

            self.modules.set_enabled(
                "tools",
                True,
            )

            self.app.navigate("resources")
            self.assertTrue(
                self.modules.route_link_is_displayed(
                    "tools"
                )
            )

            self.app.open("care")
            self.assertIsNotNone(
                self.care.find_row(care_name)
            )
        finally:
            self.modules.reset_enabled("tools")
            self.modules.reset_enabled("care")

            self._delete_owned_record(
                "/api/care-plans",
                space_id=space_id,
                field="name",
                value=care_name,
            )


if __name__ == "__main__":
    unittest.main()
