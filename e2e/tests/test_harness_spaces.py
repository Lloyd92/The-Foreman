"""Active-Space browser isolation and persistence acceptance."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.inventory import InventoryPage
from foreman_e2e.spaces import SpacesControl


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Space acceptance requires the disposable deployment runner.",
)
class SpaceIsolationTests(BrowserE2ETestCase):
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
        self.spaces = SpacesControl(
            self.driver,
            self.app,
            timeout_seconds=self.config.timeout_seconds,
        )

    def _delete_owned_inventory(
        self,
        space_id: str,
        names: set[str],
    ) -> None:
        records = self.spaces.operational_collection(
            "/api/inventory",
            space_id=space_id,
        )

        for record in records:
            if record.get("name") not in names:
                continue

            record_id = record.get("id")

            if not isinstance(record_id, str) or not record_id:
                continue

            self.app.api_request(
                f"/api/inventory/{record_id}",
                method="DELETE",
                headers={
                    "X-Foreman-Space-Id": space_id,
                },
            )

    def test_space_switch_reloads_persists_and_isolates_inventory(
        self,
    ) -> None:
        default_item = {
            "name": "E2E Default Space Stock",
            "category": "Hardware",
            "location": "Default Space Shelf",
            "quantity": 7,
            "unit": "pieces",
            "minimum": 2,
            "cost": 3.25,
            "supplier": "E2E Default Supplier",
            "notes": "Owned by the deterministic default Space.",
        }
        second_item = {
            "name": "E2E Second Space Stock",
            "category": "Hardware",
            "location": "Second Space Shelf",
            "quantity": 11,
            "unit": "pieces",
            "minimum": 4,
            "cost": 5.75,
            "supplier": "E2E Second Supplier",
            "notes": "Owned only by the disposable second Space.",
        }
        owned_names = {
            default_item["name"],
            second_item["name"],
        }

        self.app.open("inventory")
        default_space_id = self.spaces.active_space_id()

        second_space = self.spaces.create_space(
            "E2E Secondary Space",
            "Disposable Space used only for browser acceptance.",
        )
        second_space_id = second_space.get("id")

        self.assertIsInstance(second_space_id, str)
        self.assertTrue(second_space_id)

        try:
            # Reload once so the newly created Space is present in the
            # visible selector. Space creation itself is not a UI feature.
            self.app.open("inventory")

            self.assertIn(
                default_space_id,
                self.spaces.option_ids(),
            )
            self.assertIn(
                second_space_id,
                self.spaces.option_ids(),
            )

            self.inventory.create_item(default_item)

            default_records = self.spaces.operational_collection(
                "/api/inventory",
                space_id=default_space_id,
            )
            self.assertTrue(
                any(
                    record.get("name") == default_item["name"]
                    for record in default_records
                )
            )

            self.spaces.select_space(
                second_space_id,
                expected_route="inventory",
            )

            self.inventory.wait_for_empty_state()
            self.assertIsNone(
                self.inventory.find_row(default_item["name"])
            )

            second_records = self.spaces.operational_collection(
                "/api/inventory",
                space_id=second_space_id,
            )
            self.assertFalse(
                any(
                    record.get("name") == default_item["name"]
                    for record in second_records
                )
            )

            self.inventory.create_item(second_item)

            # A genuine application startup must resolve the persisted
            # second-Space selection rather than falling back to default.
            self.app.open("inventory")

            self.assertEqual(
                self.spaces.active_space_id(),
                second_space_id,
            )
            self.assertIsNotNone(
                self.inventory.find_row(second_item["name"])
            )
            self.assertIsNone(
                self.inventory.find_row(default_item["name"])
            )

            self.spaces.select_space(
                default_space_id,
                expected_route="inventory",
            )

            self.assertIsNotNone(
                self.inventory.find_row(default_item["name"])
            )
            self.assertIsNone(
                self.inventory.find_row(second_item["name"])
            )

            default_records = self.spaces.operational_collection(
                "/api/inventory",
                space_id=default_space_id,
            )
            second_records = self.spaces.operational_collection(
                "/api/inventory",
                space_id=second_space_id,
            )

            self.assertTrue(
                any(
                    record.get("name") == default_item["name"]
                    for record in default_records
                )
            )
            self.assertFalse(
                any(
                    record.get("name") == second_item["name"]
                    for record in default_records
                )
            )
            self.assertTrue(
                any(
                    record.get("name") == second_item["name"]
                    for record in second_records
                )
            )
            self.assertFalse(
                any(
                    record.get("name") == default_item["name"]
                    for record in second_records
                )
            )
        finally:
            self._delete_owned_inventory(
                default_space_id,
                owned_names,
            )
            self._delete_owned_inventory(
                second_space_id,
                owned_names,
            )
            self.spaces.delete_space(second_space_id)


if __name__ == "__main__":
    unittest.main()
