"""Stable browser interactions for The Foreman application shell."""

from __future__ import annotations

from typing import Any


ROUTE_HEADINGS = {
    "dashboard": ", Tyler.",
    "tasks": "Tasks",
    "inventory": "Inventory",
    "projects": "Projects",
    "mealworms": "Mealworm Production",
    "budget": "Budget",
    "recovery": "Backup & Recovery",
}


class ForemanApplication:
    """Drive the application through stable public browser selectors."""

    def __init__(
        self,
        driver: Any,
        *,
        origin: str,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.origin = origin.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def open(
        self,
        route: str = "dashboard",
        *,
        expected_route: str | None = None,
    ) -> None:
        target = f"{self.origin}/#{route}"

        # A fragment-only Selenium navigation may reuse the existing
        # document. Leave the origin first so deep-link tests exercise
        # a genuine application startup for every route.
        self.driver.get("about:blank")
        self.driver.get(target)
        self.wait_for_document()
        self.wait_until_operational()
        self.wait_for_route(expected_route or route)

    def wait_for_document(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def wait_until_operational(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(
            self.driver,
            self.timeout_seconds,
        )

        wait.until(
            lambda driver: (
                "connection-blocked"
                not in (
                    driver.find_element(
                        "tag name",
                        "body",
                    ).get_attribute("class")
                    or ""
                ).split()
            )
        )
        wait.until(
            lambda driver: driver.find_element(
                "id",
                "hardhead-availability",
            ).get_attribute("data-connection-state") == "online"
        )
        wait.until(
            lambda driver: not driver.find_element(
                "id",
                "hardhead-availability",
            ).is_displayed()
        )
        wait.until(
            lambda driver: driver.find_element(
                "id",
                "system-status",
            ).text == "System online"
        )
        wait.until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "api-status",
                ).get_attribute("textContent")
                or ""
            ).strip() == "ONLINE"
        )

    def navigate(self, route: str) -> None:
        self.driver.find_element(
            "css selector",
            f'[data-route="{route}"]',
        ).click()
        self.wait_for_route(route)

    def wait_for_route(self, route: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: self.visible_routes() == [route]
            and self.active_route() == route
        )

    def visible_routes(self) -> list[str]:
        return [
            page.get_attribute("data-page")
            for page in self.driver.find_elements(
                "css selector",
                "[data-page]",
            )
            if page.is_displayed()
        ]

    def active_route(self) -> str | None:
        active_links = self.driver.find_elements(
            "css selector",
            '[data-route].active[aria-current="page"]',
        )
        if len(active_links) != 1:
            return None
        return active_links[0].get_attribute("data-route")

    def heading(self, route: str) -> str:
        if route == "dashboard":
            selector = "#greeting"
        else:
            selector = f'[data-page="{route}"] h2'

        return self.driver.find_element(
            "css selector",
            selector,
        ).text

    def text_by_id(self, element_id: str) -> str:
        element = self.driver.find_element(
            "id",
            element_id,
        )
        return (
            element.get_attribute("textContent")
            or ""
        ).strip()
