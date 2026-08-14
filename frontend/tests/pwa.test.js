import assert from "node:assert/strict";
import test from "node:test";

import {
    hasActiveEditingState,
    initializePwa,
    SERVICE_WORKER_OPTIONS,
    SERVICE_WORKER_URL
} from "../utils/pwa.js";

class FakeEventTarget {
    constructor() {
        this.listeners = new Map();
    }

    addEventListener(type, listener) {
        const listeners = this.listeners.get(type) || [];
        listeners.push(listener);
        this.listeners.set(type, listeners);
    }

    dispatch(type) {
        (this.listeners.get(type) || []).forEach(listener => listener());
    }
}

function button() {
    return {
        disabled: false,
        listeners: new Map(),
        addEventListener(type, listener) {
            this.listeners.set(type, listener);
        },
        click() {
            this.listeners.get("click")?.();
        }
    };
}

function createPwaHarness({
    secure = true,
    supported = true,
    registrationFailure = null,
    waiting = true,
    activeDialog = false,
    forms = []
} = {}) {
    const notice = { hidden: true };
    const message = { textContent: "" };
    const updateButton = button();
    const dismissButton = button();
    const elements = new Map([
        ["pwa-update-notice", notice],
        ["pwa-update-message", message],
        ["pwa-update-action", updateButton],
        ["pwa-update-dismiss", dismissButton]
    ]);
    const waitingWorker = {
        messages: [],
        postMessage(value) {
            this.messages.push(value);
        }
    };
    const installingWorker = new FakeEventTarget();
    installingWorker.state = "installing";
    const registration = new FakeEventTarget();
    registration.waiting = waiting ? waitingWorker : null;
    registration.installing = installingWorker;
    registration.updateCalls = 0;
    registration.update = async () => {
        registration.updateCalls += 1;
    };
    const serviceWorker = new FakeEventTarget();
    serviceWorker.registerCalls = [];
    serviceWorker.register = async (...args) => {
        serviceWorker.registerCalls.push(args);

        if (registrationFailure) {
            throw registrationFailure;
        }

        return registration;
    };
    const navigatorRef = supported ? { serviceWorker } : {};
    const windowRef = {
        isSecureContext: secure,
        location: {
            reloadCalls: 0,
            reload() {
                this.reloadCalls += 1;
            }
        }
    };
    const documentRef = Object.assign(
        new FakeEventTarget(),
        {
            visibilityState: "visible",
            getElementById(id) {
                return elements.get(id) || null;
            },
            querySelector() {
                return activeDialog ? {} : null;
            },
            querySelectorAll(selector) {
                return selector === "form" ? forms : [];
            }
        }
    );
    const logger = {
        errors: [],
        error(...args) {
            this.errors.push(args);
        }
    };

    return {
        dismissButton,
        documentRef,
        installingWorker,
        logger,
        message,
        navigatorRef,
        notice,
        registration,
        serviceWorker,
        updateButton,
        waitingWorker,
        windowRef
    };
}

function dirtyTextControl(value = "Changed") {
    return {
        defaultValue: "",
        disabled: false,
        name: "title",
        tagName: "INPUT",
        type: "text",
        value
    };
}

test("registration is skipped outside secure supported contexts", async () => {
    const insecure = createPwaHarness({ secure: false });
    const insecureResult = await initializePwa(insecure);

    assert.equal(insecureResult.status, "skipped");
    assert.deepEqual(insecure.serviceWorker.registerCalls, []);

    const unsupported = createPwaHarness({ supported: false });
    const unsupportedResult = await initializePwa(unsupported);

    assert.equal(unsupportedResult.status, "skipped");
});

test("registration uses the root worker with cache bypass", async () => {
    const harness = createPwaHarness({ waiting: false });
    const result = await initializePwa(harness);

    assert.equal(result.status, "registered");
    assert.equal(SERVICE_WORKER_URL, "/service-worker.js");
    assert.deepEqual(
        SERVICE_WORKER_OPTIONS,
        { scope: "/", updateViaCache: "none" }
    );
    assert.deepEqual(
        harness.serviceWorker.registerCalls,
        [[
            "/service-worker.js",
            { scope: "/", updateViaCache: "none" }
        ]]
    );
    assert.equal(harness.registration.updateCalls, 1);
});

test("returning to the foreground checks for a PWA update", async () => {
    const harness = createPwaHarness({ waiting: false });
    await initializePwa(harness);

    assert.equal(harness.registration.updateCalls, 1);

    harness.documentRef.visibilityState = "hidden";
    harness.documentRef.dispatch("visibilitychange");
    assert.equal(harness.registration.updateCalls, 1);

    harness.documentRef.visibilityState = "visible";
    harness.documentRef.dispatch("visibilitychange");
    assert.equal(harness.registration.updateCalls, 2);
});


test("registration failure is reported without throwing", async () => {
    const failure = new Error("registration failed");
    const harness = createPwaHarness({
        registrationFailure: failure
    });
    const result = await initializePwa(harness);

    assert.equal(result.status, "failed");
    assert.equal(result.error, failure);
    assert.equal(harness.logger.errors.length, 1);
});

test("waiting worker shows an accessible deferrable update notice", async () => {
    const harness = createPwaHarness();
    await initializePwa(harness);

    assert.equal(harness.notice.hidden, false);
    assert.match(harness.message.textContent, /new Foreman application shell/);

    harness.dismissButton.click();

    assert.equal(harness.notice.hidden, true);
    assert.deepEqual(harness.waitingWorker.messages, []);
});

test("newly installed waiting worker reveals the update notice", async () => {
    const harness = createPwaHarness({ waiting: false });
    await initializePwa(harness);

    assert.equal(harness.notice.hidden, true);

    harness.registration.dispatch("updatefound");
    harness.registration.waiting = harness.waitingWorker;
    harness.installingWorker.state = "installed";
    harness.installingWorker.dispatch("statechange");

    assert.equal(harness.notice.hidden, false);
});

test("open dialogs and dirty forms are recognized as active editing", () => {
    const dialogHarness = createPwaHarness({ activeDialog: true });
    assert.equal(
        hasActiveEditingState(dialogHarness.documentRef),
        true
    );

    const dirtyFormHarness = createPwaHarness({
        forms: [{ elements: [dirtyTextControl()] }]
    });
    assert.equal(
        hasActiveEditingState(dirtyFormHarness.documentRef),
        true
    );

    const cleanFormHarness = createPwaHarness({
        forms: [{
            elements: [{
                ...dirtyTextControl(""),
                value: ""
            }]
        }]
    });
    assert.equal(
        hasActiveEditingState(cleanFormHarness.documentRef),
        false
    );

    const hiddenDialogForm = {
        closest() {
            return { hidden: true };
        },
        elements: [dirtyTextControl()]
    };
    const hiddenDialogHarness = createPwaHarness({
        forms: [hiddenDialogForm]
    });
    assert.equal(
        hasActiveEditingState(hiddenDialogHarness.documentRef),
        false
    );
});

test("active editing blocks update activation", async () => {
    const harness = createPwaHarness({ activeDialog: true });
    await initializePwa(harness);

    harness.updateButton.click();

    assert.deepEqual(harness.waitingWorker.messages, []);
    assert.match(harness.message.textContent, /Finish or close/);
    assert.equal(harness.updateButton.disabled, false);
});

test("explicit update activates waiting worker and reloads exactly once", async () => {
    const harness = createPwaHarness();
    await initializePwa(harness);

    harness.serviceWorker.dispatch("controllerchange");
    assert.equal(harness.windowRef.location.reloadCalls, 0);

    harness.updateButton.click();

    assert.deepEqual(
        harness.waitingWorker.messages,
        [{ type: "ACTIVATE_UPDATE" }]
    );
    assert.equal(harness.updateButton.disabled, true);
    assert.equal(harness.dismissButton.disabled, true);
    assert.match(harness.message.textContent, /Applying update/);

    harness.serviceWorker.dispatch("controllerchange");
    harness.serviceWorker.dispatch("controllerchange");

    assert.equal(harness.windowRef.location.reloadCalls, 1);
});
