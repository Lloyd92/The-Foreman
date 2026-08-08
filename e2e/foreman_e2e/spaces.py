"""Stable browser interactions for active Space selection."""

from __future__ import annotations

from typing import Any

from .application import ForemanApplication


class SpacesControl:
    """Drive Space selection through the visible application shell."""

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

    def active_space_id(self) -> str:
        return self.driver.find_element(
            "id",
            "active-space-select",
        ).get_attribute("value")

    def option_ids(self) -> list[str]:
        selector = self.driver.find_element(
            "id",
            "active-space-select",
        )
        return [
            option.get_attribute("value")
            for option in selector.find_elements("tag name", "option")
        ]

    def create_space(
        self,
        name: str,
        description: str = "",
    ) -> dict[str, object]:
        payload = self.app.api_request(
            "/api/spaces",
            method="POST",
            body={
                "name": name,
                "description": description,
            },
        )

        if not isinstance(payload, dict):
            raise AssertionError(
                f"Unexpected Space create response: {payload!r}"
            )

        return payload

    def delete_space(self, space_id: str) -> None:
        self.app.api_request(
            f"/api/spaces/{space_id}",
            method="DELETE",
        )

    def select_space(
        self,
        space_id: str,
        *,
        expected_route: str,
    ) -> None:
        from selenium.webdriver.support.ui import Select, WebDriverWait

        selector = self.driver.find_element(
            "id",
            "active-space-select",
        )

        if selector.get_attribute("value") == space_id:
            return

        token = "foreman-e2e-space-reload"
        self.driver.execute_script(
            "window.__foremanE2ESpaceReload = arguments[0];",
            token,
        )

        Select(selector).select_by_value(space_id)

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: driver.execute_script(
                "return window.__foremanE2ESpaceReload || null;"
            ) is None
        )

        self.app.wait_for_document()
        self.app.wait_until_operational()
        self.app.wait_for_route(expected_route)

        if self.active_space_id() != space_id:
            raise AssertionError(
                "Active Space did not survive the required reload."
            )

    def operational_collection(
        self,
        path: str,
        *,
        space_id: str,
    ) -> list[dict[str, object]]:
        payload = self.app.api_request(
            path,
            headers={
                "X-Foreman-Space-Id": space_id,
            },
        )

        if not isinstance(payload, list):
            raise AssertionError(
                f"{path} did not return a collection: {payload!r}"
            )

        return payload
