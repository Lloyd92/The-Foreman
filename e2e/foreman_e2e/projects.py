"""Stable browser interactions for Project and material workflows."""

from __future__ import annotations

from typing import Any


class ProjectsPage:
    """Drive backend-authoritative Project workflows through the UI."""

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
                    "projects-empty-state",
                ).is_displayed()
                and not driver.find_elements(
                    "css selector",
                    "#projects-list .project-card",
                )
            )
        )

    def open_add_dialog(self) -> None:
        self.driver.find_element("id", "add-project").click()
        self._wait_for_project_dialog("Add Project")

    def open_edit_dialog(self, project_name: str) -> None:
        card = self.wait_for_card(project_name)
        card.find_element(
            "css selector",
            '[data-action="edit"]',
        ).click()
        self._wait_for_project_dialog("Edit Project")

    def _wait_for_project_dialog(self, title: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "project-dialog-backdrop",
                ).is_displayed()
                and driver.find_element(
                    "id",
                    "project-dialog-title",
                ).text == title
            )
        )

    def fill_form(self, values: dict[str, object]) -> None:
        from selenium.webdriver.support.ui import Select

        selects = {
            "type": "project-type",
            "status": "project-status",
            "priority": "project-priority",
        }

        for key, element_id in selects.items():
            Select(
                self.driver.find_element("id", element_id)
            ).select_by_value(str(values[key]))

        fields = {
            "name": "project-name",
            "progress": "project-progress",
            "startDate": "project-start-date",
            "targetDate": "project-target-date",
            "estimatedCost": "project-estimated-cost",
            "description": "project-description",
            "notes": "project-notes",
        }

        for key, element_id in fields.items():
            element = self.driver.find_element("id", element_id)
            element.clear()
            element.send_keys(str(values.get(key, "")))

    def submit_form(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.find_element("id", "save-project").click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: not driver.find_element(
                "id",
                "project-dialog-backdrop",
            ).is_displayed()
        )

    def create_project(self, values: dict[str, object]) -> None:
        self.open_add_dialog()
        self.fill_form(values)
        self.submit_form()
        self.wait_for_card(str(values["name"]))

    def edit_project(
        self,
        current_name: str,
        values: dict[str, object],
    ) -> None:
        self.open_edit_dialog(current_name)
        self.fill_form(values)
        self.submit_form()
        self.wait_for_card(str(values["name"]))

        if current_name != values["name"]:
            self.wait_for_project_absent(current_name)

    def find_card(self, project_name: str) -> Any | None:
        for card in self.driver.find_elements(
            "css selector",
            "#projects-list .project-card",
        ):
            names = card.find_elements(
                "css selector",
                ".project-name",
            )
            if names and names[0].text == project_name:
                return card
        return None

    def wait_for_card(self, project_name: str) -> Any:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def locate(_driver: Any) -> Any | bool:
            try:
                return self.find_card(project_name) or False
            except StaleElementReferenceException:
                # Project rendering replaces the card nodes atomically.
                # Retry against the newly rendered DOM.
                return False

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(locate)

    def wait_for_project_absent(self, project_name: str) -> None:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def absent(_driver: Any) -> bool:
            try:
                return self.find_card(project_name) is None
            except StaleElementReferenceException:
                # A stale card means rendering is still changing. Wait
                # for a stable DOM before accepting the absence.
                return False

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(absent)

    def card_values(self, project_name: str) -> dict[str, str]:
        card = self.wait_for_card(project_name)

        def text(selector: str) -> str:
            return card.find_element(
                "css selector",
                selector,
            ).text

        return {
            "name": text(".project-name"),
            "status": text(".project-status"),
            "priority": text(".project-priority"),
            "type": text(".project-type"),
            "progress": text(".project-progress-heading strong"),
            "cost": text(".project-cost"),
            "description": text(".project-description"),
            "readiness": text(".project-readiness-summary strong"),
        }

    def delete_project(self, project_name: str) -> None:
        from selenium.webdriver.support import expected_conditions
        from selenium.webdriver.support.ui import WebDriverWait

        card = self.wait_for_card(project_name)
        card.find_element(
            "css selector",
            '[data-action="delete"]',
        ).click()

        alert = WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(expected_conditions.alert_is_present())
        alert.accept()
        self.wait_for_project_absent(project_name)

    def open_materials(self, project_name: str) -> None:
        card = self.wait_for_card(project_name)
        card.find_element(
            "css selector",
            '[data-action="materials"]',
        ).click()

        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "materials-dialog-backdrop",
                ).is_displayed()
                and driver.find_element(
                    "id",
                    "materials-dialog-project-name",
                ).text == project_name
            )
        )

    def close_materials(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.find_element("id", "done-materials").click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: not driver.find_element(
                "id",
                "materials-dialog-backdrop",
            ).is_displayed()
        )

    def add_material(
        self,
        item_name: str,
        *,
        quantity: object,
        note: str,
    ) -> None:
        from selenium.webdriver.support.ui import Select

        selector = Select(
            self.driver.find_element(
                "id",
                "material-inventory-item",
            )
        )

        matching_option = next(
            (
                option
                for option in selector.options
                if option.text.startswith(f"{item_name} —")
            ),
            None,
        )

        if matching_option is None:
            raise AssertionError(
                f"Inventory option not found for {item_name!r}."
            )

        selector.select_by_value(
            matching_option.get_attribute("value")
        )
        self._fill_material_fields(quantity, note)
        self.driver.find_element(
            "id",
            "add-material-requirement",
        ).click()
        self.wait_for_material(item_name)

    def edit_material(
        self,
        item_name: str,
        *,
        quantity: object,
        note: str,
    ) -> None:
        row = self.wait_for_material(item_name)
        row.find_element(
            "css selector",
            '[data-action="edit-material"]',
        ).click()

        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: driver.find_element(
                "id",
                "add-material-heading",
            ).text == "Edit Material"
        )

        self._fill_material_fields(quantity, note)
        self.driver.find_element(
            "id",
            "add-material-requirement",
        ).click()

        expected_quantity = str(quantity)

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: (
                self.material_values(item_name)["required"]
                .startswith(expected_quantity)
            )
        )

    def _fill_material_fields(
        self,
        quantity: object,
        note: str,
    ) -> None:
        quantity_element = self.driver.find_element(
            "id",
            "material-required-quantity",
        )
        quantity_element.clear()
        quantity_element.send_keys(str(quantity))

        note_element = self.driver.find_element(
            "id",
            "material-note",
        )
        note_element.clear()
        note_element.send_keys(note)

    def remove_material(self, item_name: str) -> None:
        from selenium.webdriver.support import expected_conditions
        from selenium.webdriver.support.ui import WebDriverWait

        row = self.wait_for_material(item_name)
        row.find_element(
            "css selector",
            '[data-action="remove-material"]',
        ).click()

        alert = WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(expected_conditions.alert_is_present())
        alert.accept()
        self.wait_for_material_absent(item_name)

    def find_material(self, item_name: str) -> Any | None:
        for row in self.driver.find_elements(
            "css selector",
            "#materials-requirements-list .material-requirement",
        ):
            names = row.find_elements(
                "css selector",
                ".material-requirement-name",
            )
            if names and names[0].text == item_name:
                return row
        return None

    def wait_for_material(self, item_name: str) -> Any:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def locate(_driver: Any) -> Any | bool:
            try:
                return self.find_material(item_name) or False
            except StaleElementReferenceException:
                # Material rendering replaces requirement rows atomically.
                return False

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(locate)

    def wait_for_material_absent(self, item_name: str) -> None:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def absent(_driver: Any) -> bool:
            try:
                return self.find_material(item_name) is None
            except StaleElementReferenceException:
                # Wait for a stable material list before accepting absence.
                return False

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(absent)

    def wait_for_materials_empty(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "materials-requirements-empty",
                ).is_displayed()
                and not driver.find_elements(
                    "css selector",
                    "#materials-requirements-list .material-requirement",
                )
            )
        )

    def material_values(self, item_name: str) -> dict[str, str]:
        row = self.wait_for_material(item_name)
        quantities = [
            element.text
            for element in row.find_elements(
                "css selector",
                ".material-quantities dd",
            )
        ]

        return {
            "name": row.find_element(
                "css selector",
                ".material-requirement-name",
            ).text,
            "reference": row.find_element(
                "css selector",
                ".material-requirement-reference",
            ).text,
            "status": row.find_element(
                "css selector",
                ".material-requirement-status",
            ).text,
            "available": quantities[0],
            "required": quantities[1],
            "shortage": quantities[2],
            "note": row.find_element(
                "css selector",
                ".material-requirement-note",
            ).text,
        }

    def material_readiness(self) -> str:
        return self.driver.find_element(
            "id",
            "materials-dialog-readiness",
        ).text

    def summary_total(self) -> str:
        element = self.driver.find_element(
            "id",
            "projects-total-count",
        )
        return (
            element.get_attribute("textContent")
            or ""
        ).strip()
