"""Firefox WebDriver session lifecycle for Foreman browser tests."""

from __future__ import annotations

import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .config import HarnessConfig
from .diagnostics import create_test_directory


@dataclass
class BrowserSession:
    driver: Any
    directory: Path
    preserve_artifacts: bool = False

    def mark_failed(self) -> None:
        self.preserve_artifacts = True


@contextmanager
def firefox_session(
    config: HarnessConfig,
    *,
    test_name: str,
) -> Iterator[BrowserSession]:
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
    except ImportError as error:
        raise RuntimeError(
            "Selenium is not installed. Run "
            "./scripts/bootstrap_browser_e2e.sh."
        ) from error

    directory = create_test_directory(
        config.artifacts_root,
        config.run_id,
        test_name,
    )
    options = Options()
    options.binary_location = config.firefox_binary

    if config.headless:
        options.add_argument("-headless")

    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.shell.checkDefaultBrowser", False)
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("startup.homepage_welcome_url", "about:blank")

    service = Service(
        executable_path=config.geckodriver_binary,
        log_output=str(directory / "geckodriver.log"),
    )
    driver = webdriver.Firefox(
        options=options,
        service=service,
    )
    driver.set_page_load_timeout(config.timeout_seconds)
    driver.set_script_timeout(config.timeout_seconds)
    driver.set_window_size(1440, 1100)
    session = BrowserSession(driver=driver, directory=directory)

    try:
        yield session
    except BaseException:
        session.mark_failed()
        raise
    finally:
        try:
            driver.quit()
        finally:
            retain_artifacts = (
                session.preserve_artifacts or config.keep_artifacts
            )

            if retain_artifacts:
                from .diagnostics import finalize_driver_log

                finalize_driver_log(directory)
            else:
                shutil.rmtree(directory, ignore_errors=True)
