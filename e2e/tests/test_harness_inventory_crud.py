"""Backend-authoritative Inventory browser CRUD coverage."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.inventory import InventoryPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Inventory CRUD requires the disposable deployment runner.",
)
class InventoryCrudTests(BrowserE2ETestCase):
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

    def test_create_edit_reload_and_delete_inventory_item(self) -> None:
        created = {
            "name": "E2E Birch Plywood",
            "category": "Lumber",
            "location": "E2E Rack A",
            "quantity": 12,
            "unit": "sheets",
            "minimum": 5,
            "cost": 18.50,
            "supplier": "E2E Supplier",
            "notes": "Created by isolated Firefox E2E.",
        }
        edited = {
            "name": "E2E Baltic Birch Plywood",
            "category": "CNC Materials",
            "location": "E2E Rack B",
            "quantity": 3,
            "unit": "sheets",
            "minimum": 5,
            "cost": 21.25,
            "supplier": "Updated E2E Supplier",
            "notes": "Updated through backend-authoritative UI.",
        }

        self.app.open("inventory")
        self.inventory.wait_for_empty_state()
        self.assertEqual(self.inventory.summary_total(), "0")

        self.inventory.create_item(created)

        self.assertEqual(
            self.inventory.row_values(created["name"]),
            {
                "name": "E2E Birch Plywood",
                "cost": "$18.50 each",
                "category": "Lumber",
                "quantity": "12 sheets",
                "minimum": "5 sheets",
                "location": "E2E Rack A",
                "stock": "IN STOCK",
            },
        )
        self.assertEqual(self.inventory.summary_total(), "1")

        self.inventory.edit_item(created["name"], edited)

        self.assertEqual(
            self.inventory.row_values(edited["name"]),
            {
                "name": "E2E Baltic Birch Plywood",
                "cost": "$21.25 each",
                "category": "CNC Materials",
                "quantity": "3 sheets",
                "minimum": "5 sheets",
                "location": "E2E Rack B",
                "stock": "LOW STOCK",
            },
        )

        # A fresh application load proves the edited record came back
        # from HardHead rather than surviving only in browser memory.
        self.app.open("inventory")

        self.assertEqual(
            self.inventory.row_values(edited["name"]),
            {
                "name": "E2E Baltic Birch Plywood",
                "cost": "$21.25 each",
                "category": "CNC Materials",
                "quantity": "3 sheets",
                "minimum": "5 sheets",
                "location": "E2E Rack B",
                "stock": "LOW STOCK",
            },
        )
        self.assertEqual(self.inventory.summary_total(), "1")

        self.inventory.delete_item(edited["name"])
        self.inventory.wait_for_empty_state()
        self.assertEqual(self.inventory.summary_total(), "0")

        # Reload once more to prove deletion was persisted by HardHead.
        self.app.open("inventory")
        self.inventory.wait_for_empty_state()
        self.assertIsNone(
            self.inventory.find_row(edited["name"]),
        )
        self.assertEqual(self.inventory.summary_total(), "0")


if __name__ == "__main__":
    unittest.main()
