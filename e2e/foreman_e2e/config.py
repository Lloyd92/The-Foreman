"""Validated configuration for the isolated Foreman browser harness."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS_ROOT = REPOSITORY_ROOT / "artifacts" / "e2e"
SNAP_FIREFOX_BINARY = Path(
    "/snap/firefox/current/usr/lib/firefox/firefox"
)
FORBIDDEN_PORTS = frozenset({80, 443, 3000, 5000})
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class HarnessConfigurationError(RuntimeError):
    """Raised when E2E configuration could reach live or unsafe resources."""


def _environment_flag(
    environment: dict[str, str],
    name: str,
    default: bool,
) -> bool:
    raw = environment.get(name)

    if raw is None:
        return default

    normalized = raw.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise HarnessConfigurationError(
        f"{name} must be a boolean flag."
    )


def _resolve_executable(
    environment: dict[str, str],
    name: str,
    default_command: str,
) -> str:
    configured = environment.get(name, "").strip()
    candidate = configured or shutil.which(default_command)

    if not candidate:
        raise HarnessConfigurationError(
            f"{name} could not be resolved."
        )

    path = Path(
        os.path.abspath(os.path.expanduser(candidate))
    )

    if not path.is_file() or not os.access(path, os.X_OK):
        raise HarnessConfigurationError(
            f"{name} is not an executable file."
        )

    return str(path)


def _resolve_firefox_binary(
    environment: dict[str, str],
) -> str:
    configured = environment.get(
        "FOREMAN_E2E_FIREFOX_BINARY",
        "",
    ).strip()

    if configured:
        return _resolve_executable(
            environment,
            "FOREMAN_E2E_FIREFOX_BINARY",
            "firefox",
        )

    if (
        SNAP_FIREFOX_BINARY.is_file()
        and os.access(SNAP_FIREFOX_BINARY, os.X_OK)
    ):
        return str(SNAP_FIREFOX_BINARY)

    return _resolve_executable(
        environment,
        "FOREMAN_E2E_FIREFOX_BINARY",
        "firefox",
    )


def validate_origin(origin: str) -> str:
    parsed = urlsplit(origin)

    if parsed.scheme != "http":
        raise HarnessConfigurationError(
            "The isolated E2E origin must use HTTP."
        )

    if parsed.hostname != "127.0.0.1":
        raise HarnessConfigurationError(
            "The isolated E2E origin must bind only to 127.0.0.1."
        )

    try:
        port = parsed.port
    except ValueError as error:
        raise HarnessConfigurationError(
            "The isolated E2E origin has an invalid port."
        ) from error

    if port is None or not 1024 <= port <= 65535:
        raise HarnessConfigurationError(
            "The isolated E2E origin requires an unprivileged port."
        )

    if port in FORBIDDEN_PORTS:
        raise HarnessConfigurationError(
            f"Port {port} is reserved for a live or internal Foreman service."
        )

    if (
        parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise HarnessConfigurationError(
            "The isolated E2E origin must contain only scheme, host, and port."
        )

    return f"http://127.0.0.1:{port}"


@dataclass(frozen=True)
class HarnessConfig:
    """Runtime configuration that has passed the isolation boundary."""

    origin: str
    artifacts_root: Path
    run_id: str
    firefox_binary: str
    geckodriver_binary: str
    headless: bool
    keep_artifacts: bool
    timeout_seconds: float

    @classmethod
    def from_environment(
        cls,
        environment: dict[str, str] | None = None,
    ) -> "HarnessConfig":
        values = dict(os.environ if environment is None else environment)
        origin = validate_origin(
            values.get("FOREMAN_E2E_ORIGIN", "")
        )

        run_id = values.get("FOREMAN_E2E_RUN_ID", "").strip()

        if not SAFE_RUN_ID.fullmatch(run_id):
            raise HarnessConfigurationError(
                "FOREMAN_E2E_RUN_ID is missing or unsafe."
            )

        artifacts_root = Path(
            values.get(
                "FOREMAN_E2E_ARTIFACTS_ROOT",
                str(DEFAULT_ARTIFACTS_ROOT),
            )
        ).expanduser().resolve()

        expected_root = DEFAULT_ARTIFACTS_ROOT.resolve()

        if (
            artifacts_root != expected_root
            and expected_root not in artifacts_root.parents
        ):
            raise HarnessConfigurationError(
                "E2E diagnostics must stay under artifacts/e2e."
            )

        timeout_raw = values.get(
            "FOREMAN_E2E_TIMEOUT_SECONDS",
            "20",
        )

        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as error:
            raise HarnessConfigurationError(
                "FOREMAN_E2E_TIMEOUT_SECONDS must be numeric."
            ) from error

        if not 1 <= timeout_seconds <= 120:
            raise HarnessConfigurationError(
                "E2E timeout must be between 1 and 120 seconds."
            )

        return cls(
            origin=origin,
            artifacts_root=artifacts_root,
            run_id=run_id,
            firefox_binary=_resolve_firefox_binary(values),
            geckodriver_binary=_resolve_executable(
                values,
                "FOREMAN_E2E_GECKODRIVER_BINARY",
                "geckodriver",
            ),
            headless=_environment_flag(
                values,
                "FOREMAN_E2E_HEADLESS",
                True,
            ),
            keep_artifacts=_environment_flag(
                values,
                "FOREMAN_E2E_KEEP_ARTIFACTS",
                False,
            ),
            timeout_seconds=timeout_seconds,
        )
