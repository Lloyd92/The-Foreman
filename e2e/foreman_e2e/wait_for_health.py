"""Bounded wait for the isolated Foreman health endpoint."""

from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import HarnessConfigurationError, validate_origin


def wait_for_health(
    origin: str,
    *,
    timeout_seconds: float = 60,
    interval_seconds: float = 0.5,
) -> dict[str, str]:
    deadline = time.monotonic() + timeout_seconds
    url = f"{validate_origin(origin)}/api/health"
    last_error: BaseException | None = None

    while time.monotonic() < deadline:
        try:
            request = Request(
                url,
                headers={"Accept": "application/json"},
            )

            with urlopen(request, timeout=2) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Health endpoint returned HTTP {response.status}."
                    )

                payload = json.loads(
                    response.read().decode("utf-8")
                )

            if (
                payload.get("status") == "healthy"
                and payload.get("database") == "online"
            ):
                return payload

            last_error = RuntimeError(
                "Health payload did not report an online database."
            )
        except (
            HTTPError,
            URLError,
            OSError,
            TimeoutError,
            json.JSONDecodeError,
            RuntimeError,
        ) as error:
            last_error = error

        time.sleep(interval_seconds)

    detail = type(last_error).__name__ if last_error else "unknown"
    raise RuntimeError(
        f"Isolated Foreman did not become healthy ({detail})."
    )


def main() -> None:
    origin = os.environ.get("FOREMAN_E2E_ORIGIN", "")

    try:
        payload = wait_for_health(origin)
    except HarnessConfigurationError:
        raise

    print(
        "Isolated Foreman healthy: "
        f"{payload['status']}; database={payload['database']}."
    )


if __name__ == "__main__":
    main()
