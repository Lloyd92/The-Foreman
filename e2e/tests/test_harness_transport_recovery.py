"""Deterministic connection-loss and safe-recovery browser coverage."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.connection import ConnectionGate
from foreman_e2e.deployment import (
    DisposableDeployment,
    DisposableDeploymentConfig,
)
from foreman_e2e.inventory import InventoryPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Transport recovery requires the disposable deployment runner.",
)
class TransportRecoveryTests(BrowserE2ETestCase):
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
        self.gate = ConnectionGate(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.deployment = DisposableDeployment(
            DisposableDeploymentConfig.from_environment()
        )

        # Always restore the disposable network before another test runs.
        self.addCleanup(
            self.deployment.reconnect_frontend_to_backend
        )

    def test_failed_write_requires_safe_reload_after_recovery(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        control_item = {
            "name": "E2E Recovery Control",
            "category": "Hardware",
            "location": "E2E Recovery Shelf",
            "quantity": 6,
            "unit": "pieces",
            "minimum": 2,
            "cost": 4.25,
            "supplier": "E2E Recovery Supplier",
            "notes": "Persisted before the simulated outage.",
        }
        failed_item = {
            "name": "E2E Failed Offline Write",
            "category": "Hardware",
            "location": "E2E Offline Shelf",
            "quantity": 3,
            "unit": "pieces",
            "minimum": 1,
            "cost": 7.50,
            "supplier": "E2E Offline Supplier",
            "notes": "This record must never be persisted.",
        }

        self.app.open("inventory")
        self.inventory.create_item(control_item)

        self.inventory.open_add_dialog()
        self.inventory.fill_form(failed_item)
        self.assertTrue(self.inventory.dialog_is_open())

        self.deployment.disconnect_frontend_from_backend()

        self.inventory.click_submit()
        self.gate.wait_for_state("unavailable")

        self.assertTrue(self.gate.is_displayed())
        self.assertTrue(self.gate.body_is_blocked())
        self.inventory.wait_for_form_error(
            "No browser-local fallback write was made."
        )
        self.assertTrue(self.inventory.dialog_is_open())

        # An explicitly visible update notice must yield to the
        # higher-priority availability gate.
        self.driver.execute_script(
            """
            const notice = document.getElementById("pwa-update-notice");
            notice.hidden = false;
            """
        )
        self.assertFalse(
            self.driver.find_element(
                "id",
                "pwa-update-notice",
            ).is_displayed()
        )

        # Retry while still disconnected remains fail-closed.
        self.gate.click_retry()
        self.gate.wait_for_state("unavailable")

        unavailable_reason = self.gate.reason()
        self.assertTrue(
            unavailable_reason.startswith("Last check:"),
            unavailable_reason,
        )
        self.assertTrue(
            any(
                expected in unavailable_reason
                for expected in (
                    "HTTP 502",
                    "could not be reached",
                    "timed out",
                )
            ),
            unavailable_reason,
        )
        self.assertTrue(self.inventory.dialog_is_open())

        self.deployment.reconnect_frontend_to_backend()

        # Recovery never resumes operations in the stale document.
        self.gate.click_retry()
        self.gate.wait_for_state("restored-reload-required")

        self.assertTrue(self.gate.is_displayed())
        self.assertTrue(self.gate.body_is_blocked())

        document_token = "e2e-reload-must-be-blocked"
        self.driver.execute_script(
            "window.__foremanE2EDocumentToken = arguments[0];",
            document_token,
        )

        # The open dirty dialog prevents an unsafe reload.
        self.gate.click_reload()
        self.gate.wait_for_reason(
            "Complete, cancel, or close the active form or dialog"
        )

        self.assertEqual(
            self.driver.execute_script(
                "return window.__foremanE2EDocumentToken;"
            ),
            document_token,
        )
        self.assertTrue(self.inventory.dialog_is_open())

        # Escape remains available even though the application is hidden.
        self.inventory.close_dialog_with_escape()
        self.assertFalse(self.inventory.dialog_is_open())

        self.gate.click_reload()

        WebDriverWait(
            self.driver,
            self.config.timeout_seconds,
        ).until(
            lambda driver: driver.execute_script(
                "return window.__foremanE2EDocumentToken || null;"
            ) is None
        )

        self.app.wait_for_document()
        self.app.wait_until_operational()
        self.app.wait_for_route("inventory")

        # HardHead retained the committed record and rejected the
        # interrupted write without a browser-local fallback.
        self.assertIsNotNone(
            self.inventory.find_row(control_item["name"])
        )
        self.assertIsNone(
            self.inventory.find_row(failed_item["name"])
        )
        self.assertEqual(self.inventory.summary_total(), "1")

        self.inventory.delete_item(control_item["name"])
        self.inventory.wait_for_item_absent(control_item["name"])


if __name__ == "__main__":
    unittest.main()
