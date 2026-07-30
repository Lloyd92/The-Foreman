import { hasActiveEditingState } from "./pwa.js";

export const CONNECTION_STATES = Object.freeze({
    checking: "checking",
    online: "online",
    unavailable: "unavailable",
    restoredReloadRequired: "restored-reload-required"
});

export const HEALTH_CHECK_PATH = "/api/health";
export const HEALTH_CHECK_TIMEOUT_MS = 5000;

const TRANSPORT_STATUSES = new Set([502, 503, 504]);
let activeConnectionController = null;


export class HardHeadAvailabilityError extends Error {
    constructor(
        message = "HardHead is unavailable.",
        { state = CONNECTION_STATES.unavailable, cause = null } = {}
    ) {
        super(message, cause ? { cause } : undefined);
        this.name = "HardHeadAvailabilityError";
        this.code = "HARDHEAD_UNAVAILABLE";
        this.state = state;
    }
}


export function isTransportStatus(status) {
    return TRANSPORT_STATUSES.has(status);
}


export function isTransportError(error) {
    return error?.name === "AbortError" ||
        error?.name === "TimeoutError" ||
        error instanceof TypeError;
}


export function setActiveConnectionController(controller) {
    activeConnectionController = controller;
}


export function getActiveConnectionController() {
    return activeConnectionController;
}


export function assertBusinessRequestAllowed() {
    if (!activeConnectionController) {
        return;
    }

    if (!activeConnectionController.isBusinessAvailable()) {
        throw new HardHeadAvailabilityError(
            "HardHead is unavailable. Operational requests are blocked.",
            { state: activeConnectionController.getState() }
        );
    }
}


export async function verifyTransportFailure(failure) {
    if (!activeConnectionController) {
        return true;
    }

    const result = await activeConnectionController.verifyTransportFailure(
        failure
    );

    if (!result.online) {
        throw new HardHeadAvailabilityError(
            result.reason,
            {
                state: activeConnectionController.getState(),
                cause: failure?.error || null
            }
        );
    }

    return true;
}


function getAvailabilityElements(documentRef) {
    return {
        gate: documentRef?.getElementById("hardhead-availability"),
        title: documentRef?.getElementById("hardhead-availability-title"),
        message: documentRef?.getElementById(
            "hardhead-availability-message"
        ),
        reason: documentRef?.getElementById("hardhead-availability-reason"),
        retryButton: documentRef?.getElementById(
            "hardhead-availability-retry"
        ),
        reloadButton: documentRef?.getElementById(
            "hardhead-availability-reload"
        )
    };
}


export function createAvailabilityUi({
    documentRef = globalThis.document,
    windowRef = globalThis.window
} = {}) {
    const elements = getAvailabilityElements(documentRef);
    let retryHandler = null;
    let reloadHandler = null;
    let focusedState = null;

    elements.retryButton?.addEventListener("click", () => {
        retryHandler?.();
    });
    elements.reloadButton?.addEventListener("click", () => {
        reloadHandler?.();
    });

    function focusAction(state, button) {
        if (focusedState === state) {
            return;
        }

        focusedState = state;
        windowRef?.setTimeout?.(() => button?.focus(), 0);
    }

    return {
        bind({ onRetry, onReload }) {
            retryHandler = onRetry;
            reloadHandler = onReload;
        },

        render({ state, reason = "" }) {
            const blocked = state !== CONNECTION_STATES.online;

            documentRef?.body?.classList.toggle(
                "connection-blocked",
                blocked
            );

            if (elements.gate) {
                elements.gate.hidden = !blocked;
                elements.gate.setAttribute("data-connection-state", state);
            }

            if (state === CONNECTION_STATES.online) {
                focusedState = null;
                return;
            }

            if (elements.retryButton) {
                elements.retryButton.hidden =
                    state !== CONNECTION_STATES.unavailable;
                elements.retryButton.disabled =
                    state !== CONNECTION_STATES.unavailable;
            }
            if (elements.reloadButton) {
                elements.reloadButton.hidden =
                    state !== CONNECTION_STATES.restoredReloadRequired;
                elements.reloadButton.disabled =
                    state !== CONNECTION_STATES.restoredReloadRequired;
            }

            if (state === CONNECTION_STATES.checking) {
                if (elements.title) {
                    elements.title.textContent = "Checking HardHead…";
                }
                if (elements.message) {
                    elements.message.textContent =
                        "Confirming that HardHead and its database are healthy.";
                }
                if (elements.reason) {
                    elements.reason.textContent =
                        reason || "Waiting for the health check.";
                }
                return;
            }

            if (state === CONNECTION_STATES.unavailable) {
                if (elements.title) {
                    elements.title.textContent =
                        "HardHead is unavailable";
                }
                if (elements.message) {
                    elements.message.textContent =
                        "Operational data cannot safely load because " +
                        "HardHead is the source of truth.";
                }
                if (elements.reason) {
                    elements.reason.textContent =
                        `Last check: ${reason}`;
                }
                focusAction(state, elements.retryButton);
                return;
            }

            if (elements.title) {
                elements.title.textContent =
                    "HardHead connection restored";
            }
            if (elements.message) {
                elements.message.textContent =
                    "HardHead connection restored. Reload The Foreman " +
                    "to refresh operational data safely.";
            }
            if (elements.reason) {
                elements.reason.textContent = reason;
            }
            focusAction(state, elements.reloadButton);
        },

        showReloadBlocked() {
            if (elements.reason) {
                elements.reason.textContent =
                    "Complete, cancel, or close the active form or dialog " +
                    "before reloading.";
            }
            elements.reloadButton?.focus();
        }
    };
}


function unavailableResult(reason, error = null) {
    return {
        online: false,
        reason,
        error
    };
}


export function createConnectionController(options = {}) {
    const fetchImpl = options.fetchImpl ?? globalThis.fetch;
    const AbortControllerImpl =
        options.AbortControllerImpl ?? globalThis.AbortController;
    const setTimeoutImpl = options.setTimeoutImpl ?? globalThis.setTimeout;
    const clearTimeoutImpl =
        options.clearTimeoutImpl ?? globalThis.clearTimeout;
    const windowRef = options.windowRef ?? globalThis.window;
    const documentRef = options.documentRef ?? globalThis.document;
    const logger = options.logger ?? globalThis.console;
    const timeoutMs = options.timeoutMs ?? HEALTH_CHECK_TIMEOUT_MS;
    const operationalStartup =
        options.operationalStartup ?? (async () => {});
    const editingStateCheck =
        options.editingStateCheck ?? hasActiveEditingState;
    const ui = options.ui ?? createAvailabilityUi({
        documentRef,
        windowRef
    });

    let state = CONNECTION_STATES.checking;
    let lastReason = "Waiting for the health check.";
    let healthProbe = null;
    let healthCheck = null;
    let startupPromise = null;
    let operationalStartupOccurred = false;
    let initialized = false;
    let reloadTriggered = false;

    function render() {
        ui.render({ state, reason: lastReason });
    }

    function transition(nextState, reason) {
        state = nextState;
        lastReason = reason;
        render();
    }

    function probeHealth() {
        if (healthProbe) {
            return healthProbe;
        }

        healthProbe = (async () => {
            const controller = new AbortControllerImpl();
            let timedOut = false;
            const timeoutId = setTimeoutImpl(() => {
                timedOut = true;
                controller.abort();
            }, timeoutMs);

            try {
                const response = await fetchImpl(HEALTH_CHECK_PATH, {
                    method: "GET",
                    cache: "no-store",
                    headers: {
                        Accept: "application/json"
                    },
                    signal: controller.signal
                });

                if (!response.ok) {
                    return unavailableResult(
                        `Health check returned HTTP ${response.status}.`
                    );
                }

                let data;

                try {
                    data = await response.json();
                } catch (error) {
                    return unavailableResult(
                        "Health response was not valid JSON.",
                        error
                    );
                }

                if (!data ||
                    typeof data.status !== "string" ||
                    typeof data.database !== "string") {
                    return unavailableResult(
                        "Health response was missing required fields."
                    );
                }

                if (data.status !== "healthy") {
                    return unavailableResult(
                        `HardHead reported ${data.status}.`
                    );
                }

                if (data.database !== "online") {
                    return unavailableResult(
                        `HardHead database reported ${data.database}.`
                    );
                }

                return {
                    online: true,
                    reason: "HardHead and its database are healthy.",
                    data
                };
            } catch (error) {
                if (timedOut) {
                    return unavailableResult(
                        "Health check timed out.",
                        error
                    );
                }

                return unavailableResult(
                    "HardHead could not be reached.",
                    error
                );
            } finally {
                clearTimeoutImpl(timeoutId);
            }
        })();

        void healthProbe.then(
            () => {
                healthProbe = null;
            },
            () => {
                healthProbe = null;
            }
        );

        return healthProbe;
    }

    function beginOperationalStartup() {
        if (startupPromise) {
            return startupPromise;
        }

        operationalStartupOccurred = true;
        startupPromise = Promise.resolve().then(operationalStartup);
        startupPromise.catch(error => {
            logger?.error(
                "Unable to initialize operational Foreman features:",
                error
            );

            if (state === CONNECTION_STATES.online) {
                transition(
                    CONNECTION_STATES.unavailable,
                    "Operational startup could not complete safely."
                );
            }
        });
        return startupPromise;
    }

    function checkHealth({ showChecking = true } = {}) {
        if (healthCheck) {
            return healthCheck;
        }

        healthCheck = (async () => {
            const stateBeforeCheck = state;

            if (showChecking && state !== CONNECTION_STATES.online) {
                transition(
                    CONNECTION_STATES.checking,
                    "Checking HardHead and its database."
                );
            }

            const result = await probeHealth();

            if (!result.online) {
                transition(CONNECTION_STATES.unavailable, result.reason);
                return result;
            }

            if (operationalStartupOccurred) {
                if (
                    stateBeforeCheck === CONNECTION_STATES.unavailable ||
                    stateBeforeCheck === CONNECTION_STATES.checking
                ) {
                    transition(
                        CONNECTION_STATES.restoredReloadRequired,
                        "A reload is required before operations can resume."
                    );
                } else {
                    transition(CONNECTION_STATES.online, result.reason);
                }
                return result;
            }

            transition(CONNECTION_STATES.online, result.reason);
            await beginOperationalStartup();
            return result;
        })();

        void healthCheck.then(
            () => {
                healthCheck = null;
            },
            () => {
                healthCheck = null;
            }
        );
        return healthCheck;
    }

    async function retry() {
        if (
            state !== CONNECTION_STATES.unavailable &&
            state !== CONNECTION_STATES.checking
        ) {
            return {
                online: state === CONNECTION_STATES.online,
                reason: lastReason
            };
        }

        return checkHealth({ showChecking: true });
    }

    async function verifyAfterTransportFailure() {
        if (state !== CONNECTION_STATES.online) {
            return unavailableResult(lastReason);
        }

        const result = await probeHealth();

        if (!result.online) {
            transition(CONNECTION_STATES.unavailable, result.reason);
        }

        return result;
    }

    function requestReload() {
        if (
            state !== CONNECTION_STATES.restoredReloadRequired ||
            reloadTriggered
        ) {
            return false;
        }

        if (editingStateCheck(documentRef)) {
            ui.showReloadBlocked();
            return false;
        }

        reloadTriggered = true;
        windowRef?.location?.reload();
        return true;
    }

    function handleBrowserOnline() {
        if (state === CONNECTION_STATES.unavailable) {
            void retry();
        }
    }

    async function initialize() {
        if (initialized) {
            return startupPromise || healthProbe;
        }

        initialized = true;
        ui.bind({
            onRetry: () => void retry(),
            onReload: requestReload
        });
        windowRef?.addEventListener?.("online", handleBrowserOnline);
        render();
        return checkHealth({ showChecking: false });
    }

    return {
        getState: () => state,
        getLastReason: () => lastReason,
        hasOperationalStartupOccurred: () =>
            operationalStartupOccurred,
        initialize,
        isBusinessAvailable: () =>
            state === CONNECTION_STATES.online,
        requestReload,
        retry,
        verifyTransportFailure: verifyAfterTransportFailure
    };
}
