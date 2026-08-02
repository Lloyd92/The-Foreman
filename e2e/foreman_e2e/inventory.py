"""Stable browser interactions for backend Inventory workflows."""

from __future__ import annotations

from typing import Any


class InventoryPage:
    """Drive Inventory CRUD through stable public UI selectors."""

    def __init__(
        self,
        driver: Any,
        *,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.timeout_seconds = timeout_seconds

    def wait_for_empty_state(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "inventory-empty-state",
                ).is_displayed()
                and not driver.find_elements(
                    "css selector",
                    "#inventory-table-body tr",
                )
            )
        )

    def open_add_dialog(self) -> None:
        self.driver.find_element(
            "id",
            "add-inventory-item",
        ).click()
        self._wait_for_dialog("Add Inventory Item")

    def open_edit_dialog(self, item_name: str) -> None:
        row = self.wait_for_row(item_name)
        row.find_element(
            "css selector",
            '[data-action="edit"]',
        ).click()
        self._wait_for_dialog("Edit Inventory Item")

    def _wait_for_dialog(self, expected_title: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "inventory-dialog-backdrop",
                ).is_displayed()
                and driver.find_element(
                    "id",
                    "inventory-dialog-title",
                ).text == expected_title
            )
        )

    def fill_form(self, values: dict[str, object]) -> None:
        from selenium.webdriver.support.ui import Select

        Select(
            self.driver.find_element(
                "id",
                "inventory-category",
            )
        ).select_by_value(str(values["category"]))

        field_ids = {
            "name": "inventory-name",
            "location": "inventory-location",
            "quantity": "inventory-quantity",
            "unit": "inventory-unit",
            "minimum": "inventory-minimum",
            "cost": "inventory-cost",
            "supplier": "inventory-supplier",
            "notes": "inventory-notes",
        }

        for key, element_id in field_ids.items():
            element = self.driver.find_element("id", element_id)
            element.clear()
            element.send_keys(str(values.get(key, "")))

    def submit_form(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.find_element(
            "css selector",
            '#inventory-form button[type="submit"]',
        ).click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: not driver.find_element(
                "id",
                "inventory-dialog-backdrop",
            ).is_displayed()
        )

    def create_item(self, values: dict[str, object]) -> None:
        self.open_add_dialog()
        self.fill_form(values)
        self.submit_form()
        self.wait_for_row(str(values["name"]))

    def edit_item(
        self,
        current_name: str,
        values: dict[str, object],
    ) -> None:
        self.open_edit_dialog(current_name)
        self.fill_form(values)
        self.submit_form()
        self.wait_for_row(str(values["name"]))
        self.wait_for_item_absent(current_name)

    def delete_item(self, item_name: str) -> None:
        from selenium.webdriver.support import expected_conditions
        from selenium.webdriver.support.ui import WebDriverWait

        row = self.wait_for_row(item_name)
        row.find_element(
            "css selector",
            '[data-action="delete"]',
        ).click()

        alert = WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(expected_conditions.alert_is_present())
        alert.accept()

        self.wait_for_item_absent(item_name)

    def find_row(self, item_name: str) -> Any | None:
        for row in self.driver.find_elements(
            "css selector",
            "#inventory-table-body tr",
        ):
            names = row.find_elements(
                "css selector",
                ".inventory-item-name",
            )
            if names and names[0].text == item_name:
                return row
        return None

    def wait_for_row(self, item_name: str) -> Any:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def locate(_driver: Any) -> Any | bool:
            try:
                return self.find_row(item_name) or False
            except StaleElementReferenceException:
                # Inventory rendering replaces table rows atomically.
                return False

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(locate)

    def wait_for_item_absent(self, item_name: str) -> None:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def absent(_driver: Any) -> bool:
            try:
                return self.find_row(item_name) is None
            except StaleElementReferenceException:
                # Wait for a stable table before accepting absence.
                return False

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(absent)

    def row_values(self, item_name: str) -> dict[str, str]:
        row = self.wait_for_row(item_name)

        def text(selector: str) -> str:
            return row.find_element(
                "css selector",
                selector,
            ).text

        return {
            "name": text(".inventory-item-name"),
            "cost": text(".inventory-item-unit-cost"),
            "category": text(".category-badge"),
            "quantity": text(".inventory-quantity"),
            "minimum": text(".inventory-minimum"),
            "location": text(".inventory-location"),
            "stock": text(".stock-badge"),
        }

    def summary_total(self) -> str:
        element = self.driver.find_element(
            "id",
            "inventory-total-count",
        )
        return (
            element.get_attribute("textContent")
            or ""
        ).strip()
