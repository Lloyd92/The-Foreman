export const SERVICE_WORKER_URL = "/service-worker.js";
export const SERVICE_WORKER_OPTIONS = Object.freeze({
    scope: "/",
    updateViaCache: "none"
});

const UPDATE_MESSAGE =
    "A new Foreman application shell is ready.";
const EDITING_MESSAGE =
    "Finish or close the active form before applying the update.";

function formControlIsDirty(control) {
    if (control.disabled || !control.name) {
        return false;
    }

    const tagName = control.tagName?.toLowerCase();

    if (tagName === "select") {
        return [...control.options].some(
            option => option.selected !== option.defaultSelected
        );
    }

    if (tagName === "input" &&
        (control.type === "checkbox" || control.type === "radio")) {
        return control.checked !== control.defaultChecked;
    }

    if (tagName === "input" && control.type === "file") {
        return control.files.length > 0;
    }

    return "defaultValue" in control &&
        control.value !== control.defaultValue;
}

export function hasActiveEditingState(documentRef = document) {
    if (documentRef.querySelector(
        ".dialog-backdrop:not([hidden]), dialog[open]"
    )) {
        return true;
    }

    return [...documentRef.querySelectorAll("form")].some(form => {
        const backdrop = form.closest?.(".dialog-backdrop");

        if (backdrop?.hidden) {
            return false;
        }

        return [...form.elements].some(formControlIsDirty);
    });
}

function getUpdateElements(documentRef) {
    return {
        notice: documentRef.getElementById("pwa-update-notice"),
        message: documentRef.getElementById("pwa-update-message"),
        updateButton: documentRef.getElementById("pwa-update-action"),
        dismissButton: documentRef.getElementById("pwa-update-dismiss")
    };
}

function showUpdateNotice(elements) {
    if (!elements.notice) {
        return;
    }

    elements.notice.hidden = false;

    if (elements.message) {
        elements.message.textContent = UPDATE_MESSAGE;
    }
    if (elements.updateButton) {
        elements.updateButton.disabled = false;
    }
    if (elements.dismissButton) {
        elements.dismissButton.disabled = false;
    }
}

function watchForWaitingWorker(registration, onWaiting) {
    if (registration.waiting) {
        onWaiting();
    }

    registration.addEventListener("updatefound", () => {
        const installingWorker = registration.installing;

        if (!installingWorker) {
            return;
        }

        installingWorker.addEventListener("statechange", () => {
            if (installingWorker.state === "installed" &&
                registration.waiting) {
                onWaiting();
            }
        });
    });
}

export async function initializePwa(options = {}) {
    const windowRef = options.windowRef ?? globalThis.window;
    const navigatorRef = options.navigatorRef ?? globalThis.navigator;
    const documentRef = options.documentRef ?? globalThis.document;
    const logger = options.logger ?? globalThis.console;

    if (!windowRef?.isSecureContext ||
        !navigatorRef ||
        !("serviceWorker" in navigatorRef)) {
        return { status: "skipped" };
    }

    let registration;

    try {
        registration = await navigatorRef.serviceWorker.register(
            SERVICE_WORKER_URL,
            SERVICE_WORKER_OPTIONS
        );
    } catch (error) {
        logger?.error("Unable to register service worker:", error);
        return { status: "failed", error };
    }

    const elements = getUpdateElements(documentRef);
    let activationRequested = false;
    let reloadTriggered = false;

    watchForWaitingWorker(
        registration,
        () => showUpdateNotice(elements)
    );

    elements.dismissButton?.addEventListener("click", () => {
        if (elements.notice) {
            elements.notice.hidden = true;
        }
    });

    elements.updateButton?.addEventListener("click", () => {
        const waitingWorker = registration.waiting;

        if (!waitingWorker) {
            if (elements.notice) {
                elements.notice.hidden = true;
            }
            return;
        }

        if (hasActiveEditingState(documentRef)) {
            if (elements.message) {
                elements.message.textContent = EDITING_MESSAGE;
            }
            return;
        }

        activationRequested = true;

        if (elements.message) {
            elements.message.textContent = "Applying update…";
        }
        if (elements.updateButton) {
            elements.updateButton.disabled = true;
        }
        if (elements.dismissButton) {
            elements.dismissButton.disabled = true;
        }

        waitingWorker.postMessage({ type: "ACTIVATE_UPDATE" });
    });

    navigatorRef.serviceWorker.addEventListener(
        "controllerchange",
        () => {
            if (!activationRequested || reloadTriggered) {
                return;
            }

            reloadTriggered = true;
            windowRef.location.reload();
        }
    );

    if (typeof registration.update === "function") {
        void registration.update().catch(error => {
            logger?.error("Unable to check for PWA update:", error);
        });
    }

    return { status: "registered", registration };
}
