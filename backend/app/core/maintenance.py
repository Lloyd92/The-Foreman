from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition
from time import monotonic


class DatabaseMaintenanceActive(RuntimeError):
    """Raised when new database work is attempted during maintenance."""


class DatabaseMaintenanceConflict(RuntimeError):
    """Raised when a second maintenance owner attempts to enter."""


class DatabaseMaintenanceDrainTimeout(TimeoutError):
    """Raised when active database work does not drain in time."""


@dataclass(frozen=True)
class DatabaseMaintenanceState:
    maintenance_active: bool
    active_database_operations: int


class DatabaseMaintenanceCoordinator:
    def __init__(self) -> None:
        self._condition = Condition()
        self._maintenance_active = False
        self._active_database_operations = 0

    def snapshot(self) -> DatabaseMaintenanceState:
        with self._condition:
            return DatabaseMaintenanceState(
                maintenance_active=self._maintenance_active,
                active_database_operations=(
                    self._active_database_operations
                ),
            )

    def acquire_database_access(self) -> None:
        with self._condition:
            if self._maintenance_active:
                raise DatabaseMaintenanceActive(
                    "Database maintenance is active."
                )

            self._active_database_operations += 1

    def release_database_access(self) -> None:
        with self._condition:
            if self._active_database_operations <= 0:
                raise RuntimeError(
                    "Database access release has no matching acquisition."
                )

            self._active_database_operations -= 1

            if self._active_database_operations == 0:
                self._condition.notify_all()

    @contextmanager
    def database_access(self) -> Iterator[None]:
        self.acquire_database_access()

        try:
            yield
        finally:
            self.release_database_access()

    def enter_maintenance(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> None:
        if timeout_seconds is not None and timeout_seconds < 0:
            raise ValueError("Maintenance timeout cannot be negative.")

        deadline = (
            None
            if timeout_seconds is None
            else monotonic() + timeout_seconds
        )

        with self._condition:
            if self._maintenance_active:
                raise DatabaseMaintenanceConflict(
                    "Database maintenance is already active."
                )

            self._maintenance_active = True

            while self._active_database_operations > 0:
                if deadline is None:
                    self._condition.wait()
                    continue

                remaining = deadline - monotonic()

                if remaining <= 0:
                    self._maintenance_active = False
                    self._condition.notify_all()
                    raise DatabaseMaintenanceDrainTimeout(
                        "Active database work did not drain before timeout."
                    )

                self._condition.wait(timeout=remaining)

    def exit_maintenance(self) -> None:
        with self._condition:
            if not self._maintenance_active:
                raise RuntimeError("Database maintenance is not active.")

            self._maintenance_active = False
            self._condition.notify_all()

    @contextmanager
    def maintenance(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> Iterator[None]:
        self.enter_maintenance(timeout_seconds=timeout_seconds)

        try:
            yield
        finally:
            self.exit_maintenance()


maintenance_coordinator = DatabaseMaintenanceCoordinator()
