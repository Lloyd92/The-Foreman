"""Stable browser interactions for backend Care Plan workflows."""

from __future__ import annotations

from typing import Any


class CarePage:
    """Drive Care Plan CRUD through stable public UI selectors."""

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
                    "care-empty-state",
                ).is_displayed()
                and not driver.find_elements(
                    "css selector",
                    "#care-table-body tr",
                )
            )
        )

    def _wait_for_dialog(self, title: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "care-dialog-backdrop",
                ).is_displayed()
                and driver.find_element(
                    "id",
                    "care-dialog-title",
                ).text == title
            )
        )

    def open_add_dialog(self) -> None:
        self.driver.find_element(
            "id",
            "add-care-plan",
        ).click()
        self._wait_for_dialog("Add Care Plan")

    def open_edit_dialog(self, name: str) -> None:
        row = self.wait_for_row(name)
        row.find_element(
            "css selector",
            '[data-action="edit"]',
        ).click()
        self._wait_for_dialog("Edit Care Plan")

    def fill_form(self, values: dict[str, object]) -> None:
        from selenium.webdriver.support.ui import Select

        fields = {
            "name": "care-name",
            "careType": "care-type",
            "description": "care-description",
            "frequencyValue": "care-frequency-value",
            "frequencyUnit": "care-frequency-unit",
            "notes": "care-notes",
        }

        for key, element_id in fields.items():
            element = self.driver.find_element(
                "id",
                element_id,
            )
            element.clear()
            element.send_keys(str(values.get(key, "")))

        tool_value = values.get("toolId")

        if tool_value is not None:
            Select(
                self.driver.find_element(
                    "id",
                    "care-tool",
                )
            ).select_by_value(str(tool_value))

    def submit_form(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.find_element(
            "id",
            "save-care-plan",
        ).click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: not driver.find_element(
                "id",
                "care-dialog-backdrop",
            ).is_displayed()
        )

    def create_plan(self, values: dict[str, object]) -> None:
        self.open_add_dialog()
        self.fill_form(values)
        self.submit_form()
        self.wait_for_row(str(values["name"]))

    def edit_plan(
        self,
        current_name: str,
        values: dict[str, object],
    ) -> None:
        self.open_edit_dialog(current_name)
        self.fill_form(values)
        self.submit_form()
        self.wait_for_row(str(values["name"]))
        self.wait_for_plan_absent(current_name)

    def delete_plan(self, name: str) -> None:
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

        self.wait_for_plan_absent(name)

    def find_row(self, name: str) -> Any | None:
        for row in self.driver.find_elements(
            "css selector",
            "#care-table-body tr",
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

    def wait_for_plan_absent(self, name: str) -> None:
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
            "careType": text(".care-type-value"),
            "tool": text(".care-tool-value"),
            "frequency": text(".care-frequency-value"),
        }
