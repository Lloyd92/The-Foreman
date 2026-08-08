"""Stable browser interactions for local module registration."""

from __future__ import annotations

from typing import Any

from .application import ForemanApplication


class ModuleSettings:
    """Drive module state through the visible Settings workspace."""

    def __init__(
        self,
        driver: Any,
        app: ForemanApplication,
        *,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.app = app
        self.timeout_seconds = timeout_seconds

    def _card(self, module_id: str) -> Any:
        from selenium.webdriver.support.ui import WebDriverWait

        selector = (
            "#module-settings-list "
            f'article[data-module-id="{module_id}"]'
        )

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: (
                driver.find_element("css selector", selector)
            )
        )

    def state(self, module_id: str) -> str:
        return (
            self._card(module_id)
            .find_element(
                "css selector",
                ".module-setting-state",
            )
            .get_attribute("data-state")
        )

    def set_enabled(
        self,
        module_id: str,
        enabled: bool,
    ) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        expected_state = "enabled" if enabled else "disabled"

        if self.state(module_id) == expected_state:
            return

        card = self._card(module_id)
        action = card.find_element(
            "css selector",
            ".module-setting-action",
        )

        token = f"foreman-e2e-module-{module_id}-reload"
        self.driver.execute_script(
            "window.__foremanE2EModuleReload = arguments[0];",
            token,
        )

        action.click()

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: driver.execute_script(
                "return window.__foremanE2EModuleReload || null;"
            ) is None
        )

        self.app.wait_for_document()
        self.app.wait_until_operational()
        self.app.wait_for_route("settings")

        if self.state(module_id) != expected_state:
            raise AssertionError(
                f"Module {module_id!r} did not become {expected_state}."
            )

    def reset_enabled(self, module_id: str) -> None:
        """Restore a built-in module after an interrupted E2E workflow."""

        self.app.api_request(
            f"/api/modules/{module_id}",
            method="PATCH",
            body={"enabled": True},
        )

    def route_link_is_displayed(self, route: str) -> bool:
        elements = self.driver.find_elements(
            "css selector",
            f'.secondary-navigation a[href="#{route}"]',
        )
        return bool(elements) and any(
            element.is_displayed()
            for element in elements
        )

    def visible_contribution_count(self, module_id: str) -> int:
        elements = self.driver.find_elements(
            "css selector",
            "[data-module-contribution]",
        )
        return sum(
            1
            for element in elements
            if (
                element.get_attribute(
                    "data-module-contribution"
                ) == module_id
                and element.is_displayed()
            )
        )
