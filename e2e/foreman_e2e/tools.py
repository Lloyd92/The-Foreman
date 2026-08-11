"""Stable browser interactions for backend Tool workflows."""

from __future__ import annotations

from typing import Any


class ToolsPage:
    """Drive Tool and maintenance CRUD through public UI selectors."""

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
                    "tools-empty-state",
                ).is_displayed()
                and not driver.find_elements(
                    "css selector",
                    "#tools-table-body tr",
                )
            )
        )

    def _wait_for_tool_dialog(self, title: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "tool-dialog-backdrop",
                ).is_displayed()
                and driver.find_element(
                    "id",
                    "tool-dialog-title",
                ).text == title
            )
        )

    def open_add_dialog(self) -> None:
        self.driver.find_element(
            "id",
            "add-tool",
        ).click()
        self._wait_for_tool_dialog("Add Tool")

    def open_edit_dialog(self, name: str) -> None:
        row = self.wait_for_row(name)
        row.find_element(
            "css selector",
            '[data-action="edit"]',
        ).click()
        self._wait_for_tool_dialog("Edit Tool")

    def fill_form(self, values: dict[str, object]) -> None:
        fields = {
            "name": "tool-name",
            "category": "tool-category",
            "condition": "tool-condition",
            "location": "tool-location",
            "availability": "tool-availability",
            "notes": "tool-notes",
        }

        for key, element_id in fields.items():
            element = self.driver.find_element(
                "id",
                element_id,
            )
            element.clear()
            element.send_keys(str(values.get(key, "")))

    def submit_form(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.find_element(
            "id",
            "save-tool",
        ).click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: not driver.find_element(
                "id",
                "tool-dialog-backdrop",
            ).is_displayed()
        )

    def create_tool(self, values: dict[str, object]) -> None:
        self.open_add_dialog()
        self.fill_form(values)
        self.submit_form()
        self.wait_for_row(str(values["name"]))

    def edit_tool(
        self,
        current_name: str,
        values: dict[str, object],
    ) -> None:
        self.open_edit_dialog(current_name)
        self.fill_form(values)
        self.submit_form()
        self.wait_for_row(str(values["name"]))
        self.wait_for_tool_absent(current_name)

    def delete_tool(self, name: str) -> None:
        from selenium.webdriver.support import expected_conditions
        from selenium.webdriver.support.ui import WebDriverWait

        row = self.wait_for_row(name)
        row.find_element(
            "css selector",
            '[data-action="delete"]',
        ).click()

        alert = WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(expected_conditions.alert_is_present())
        alert.accept()

        self.wait_for_tool_absent(name)

    def find_row(self, name: str) -> Any | None:
        for row in self.driver.find_elements(
            "css selector",
            "#tools-table-body tr",
        ):
            names = row.find_elements(
                "css selector",
                ".resource-record-name",
            )

            if names and names[0].text == name:
                return row

        return None

    def wait_for_row(self, name: str) -> Any:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def locate(_driver: Any) -> Any | bool:
            try:
                return self.find_row(name) or False
            except StaleElementReferenceException:
                return False

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(locate)

    def wait_for_tool_absent(self, name: str) -> None:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def absent(_driver: Any) -> bool:
            try:
                return self.find_row(name) is None
            except StaleElementReferenceException:
                return False

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(absent)

    def row_values(self, name: str) -> dict[str, str]:
        row = self.wait_for_row(name)

        def text(selector: str) -> str:
            return row.find_element(
                "css selector",
                selector,
            ).text

        return {
            "name": text(".resource-record-name"),
            "category": text(".tool-category"),
            "condition": text(".tool-condition"),
            "location": text(".tool-location"),
            "availability": text(".tool-availability"),
        }

    def open_maintenance(self, tool_name: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        row = self.wait_for_row(tool_name)
        row.find_element(
            "css selector",
            '[data-action="maintenance"]',
        ).click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "maintenance-dialog-backdrop",
                ).is_displayed()
                and tool_name in driver.find_element(
                    "id",
                    "maintenance-dialog-title",
                ).text
            )
        )

    def add_maintenance(
        self,
        *,
        maintenance_type: str,
        performed_at: str,
        notes: str,
    ) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        values = {
            "maintenance-type": maintenance_type,
            "maintenance-performed-at": performed_at,
            "maintenance-notes": notes,
        }

        for element_id, value in values.items():
            element = self.driver.find_element(
                "id",
                element_id,
            )
            element.clear()
            element.send_keys(value)

        self.driver.find_element(
            "id",
            "save-maintenance",
        ).click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: maintenance_type in (
                driver.find_element(
                    "id",
                    "maintenance-list",
                ).get_attribute("textContent")
                or ""
            )
        )

    def maintenance_text(self) -> str:
        return (
            self.driver.find_element(
                "id",
                "maintenance-list",
            ).get_attribute("textContent")
            or ""
        ).strip()

    def close_maintenance(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.find_element(
            "id",
            "close-maintenance-dialog",
        ).click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: not driver.find_element(
                "id",
                "maintenance-dialog-backdrop",
            ).is_displayed()
        )
