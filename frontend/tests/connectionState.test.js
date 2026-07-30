import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
    CONNECTION_STATES,
    createConnectionController,
    HardHeadAvailabilityError,
    HEALTH_CHECK_PATH,
    HEALTH_CHECK_TIMEOUT_MS,
    setActiveConnectionController
} from "../utils/connectionState.js";
import { apiRequest, BackendApiError } from "../utils/api.js";

const frontendDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    ".."
);


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


function createUi() {
    return {
        bound: null,
        reloadBlocked: 0,
        renders: [],
        bind(handlers) {
            this.bound = handlers;
        },
        render(value) {
            this.renders.push({ ...value });
        },
        showReloadBlocked() {
            this.reloadBlocked += 1;
        }
    };
}


function response(data, { ok = true, status = 200 } = {}) {
    return {
        ok,
        status,
        async json() {
            return data;
        }
    };
}


function healthyResponse() {
    return response({
        status: "healthy",
        database: "online"
    });
}


function abortError() {
    const error = new Error("aborted");
    error.name = "AbortError";
    return error;
}


function createWindow() {
    return {
        location: {
            reloadCalls: 0,
            reload() {
                this.reloadCalls += 1;
            }
        },
        setTimeout(callback) {
            callback();
        }
    };
}


test("initial state is checking and health request is authoritative", async () => {
    const requests = [];
    const timerDelays = [];
    const clearedTimers = [];
    let startupCalls = 0;
    const controller = createConnectionController({
        fetchImpl: async (...args) => {
            requests.push(args);
            return healthyResponse();
        },
        setTimeoutImpl(callback, delay) {
            timerDelays.push(delay);
            return { callback };
        },
        clearTimeoutImpl(timer) {
            clearedTimers.push(timer);
        },
        ui: createUi(),
        operationalStartup: async () => {
            startupCalls += 1;
        }
    });

    assert.equal(controller.getState(), CONNECTION_STATES.checking);
    assert.equal(startupCalls, 0);

    const result = await controller.initialize();

    assert.equal(result.online, true);
    assert.equal(controller.getState(), CONNECTION_STATES.online);
    assert.equal(startupCalls, 1);
    assert.equal(requests.length, 1);
    assert.equal(requests[0][0], HEALTH_CHECK_PATH);
    assert.deepEqual(
        {
            method: requests[0][1].method,
            cache: requests[0][1].cache,
            headers: requests[0][1].headers
        },
        {
            method: "GET",
            cache: "no-store",
            headers: { Accept: "application/json" }
        }
    );
    assert.ok(requests[0][1].signal);
    assert.deepEqual(timerDelays, [HEALTH_CHECK_TIMEOUT_MS]);
    assert.equal(HEALTH_CHECK_TIMEOUT_MS, 5000);
    assert.equal(clearedTimers.length, 1);
});


test("only one health probe and startup run during concurrent retries", async () => {
    let resolveHealth;
    let fetchCalls = 0;
    let startupCalls = 0;
    const controller = createConnectionController({
        fetchImpl: async () => {
            fetchCalls += 1;
            return new Promise(resolve => {
                resolveHealth = resolve;
            });
        },
        ui: createUi(),
        operationalStartup: async () => {
            startupCalls += 1;
        }
    });

    const initialization = controller.initialize();
    const retryOne = controller.retry();
    const retryTwo = controller.retry();

    assert.equal(fetchCalls, 1);
    assert.equal(startupCalls, 0);

    resolveHealth(healthyResponse());
    await Promise.all([initialization, retryOne, retryTwo]);

    assert.equal(fetchCalls, 1);
    assert.equal(startupCalls, 1);
    assert.equal(controller.getState(), CONNECTION_STATES.online);
});


const unavailableCases = [
    {
        name: "network error",
        fetchImpl: async () => {
            throw new TypeError("network unavailable");
        },
        reason: /could not be reached/
    },
    {
        name: "non-success response",
        fetchImpl: async () => response(
            { detail: "unavailable" },
            { ok: false, status: 503 }
        ),
        reason: /HTTP 503/
    },
    {
        name: "invalid JSON",
        fetchImpl: async () => ({
            ok: true,
            status: 200,
            async json() {
                throw new SyntaxError("invalid JSON");
            }
        }),
        reason: /not valid JSON/
    },
    {
        name: "unhealthy application",
        fetchImpl: async () => response({
            status: "unhealthy",
            database: "online"
        }),
        reason: /reported unhealthy/
    },
    {
        name: "offline database",
        fetchImpl: async () => response({
            status: "healthy",
            database: "offline"
        }),
        reason: /reported offline/
    },
    {
        name: "missing fields",
        fetchImpl: async () => response({ status: "healthy" }),
        reason: /missing required fields/
    }
];

for (const currentCase of unavailableCases) {
    test(`${currentCase.name} makes HardHead unavailable`, async () => {
        let startupCalls = 0;
        const controller = createConnectionController({
            fetchImpl: currentCase.fetchImpl,
            ui: createUi(),
            operationalStartup: async () => {
                startupCalls += 1;
            }
        });

        const result = await controller.initialize();

        assert.equal(result.online, false);
        assert.match(result.reason, currentCase.reason);
        assert.equal(
            controller.getState(),
            CONNECTION_STATES.unavailable
        );
        assert.equal(startupCalls, 0);
        assert.equal(
            Object.hasOwn(result, "records"),
            false,
            "availability checks must not fabricate records"
        );
    });
}


test("health probe timeout is finite and becomes unavailable", async () => {
    let timeoutDelay = null;
    const controller = createConnectionController({
        fetchImpl: async (path, options) => {
            assert.equal(path, HEALTH_CHECK_PATH);

            if (options.signal.aborted) {
                throw abortError();
            }

            return new Promise((resolve, reject) => {
                options.signal.addEventListener(
                    "abort",
                    () => reject(abortError())
                );
            });
        },
        setTimeoutImpl(callback, delay) {
            timeoutDelay = delay;
            callback();
            return 1;
        },
        clearTimeoutImpl() {},
        ui: createUi()
    });

    const result = await controller.initialize();

    assert.equal(timeoutDelay, 5000);
    assert.equal(result.online, false);
    assert.match(result.reason, /timed out/);
    assert.equal(
        controller.getState(),
        CONNECTION_STATES.unavailable
    );
});


test("browser online event performs a real probe and cannot mark online", async () => {
    const windowRef = new FakeEventTarget();
    let fetchCalls = 0;
    let resolveRecovery;
    const controller = createConnectionController({
        windowRef,
        fetchImpl: async () => {
            fetchCalls += 1;

            if (fetchCalls === 1) {
                throw new TypeError("offline");
            }

            return new Promise(resolve => {
                resolveRecovery = resolve;
            });
        },
        ui: createUi()
    });

    await controller.initialize();
    assert.equal(
        controller.getState(),
        CONNECTION_STATES.unavailable
    );

    windowRef.dispatch("online");

    assert.equal(fetchCalls, 2);
    assert.equal(controller.getState(), CONNECTION_STATES.checking);

    resolveRecovery(healthyResponse());
    await new Promise(resolve => setTimeout(resolve, 0));

    assert.equal(controller.getState(), CONNECTION_STATES.online);
});


test("retry recovers initial startup once without duplicate initialization", async () => {
    let fetchCalls = 0;
    let startupCalls = 0;
    const controller = createConnectionController({
        fetchImpl: async () => {
            fetchCalls += 1;
            return fetchCalls === 1
                ? response({}, { ok: false, status: 503 })
                : healthyResponse();
        },
        ui: createUi(),
        operationalStartup: async () => {
            startupCalls += 1;
        }
    });

    await controller.initialize();
    assert.equal(startupCalls, 0);

    await controller.retry();
    await controller.retry();

    assert.equal(fetchCalls, 2);
    assert.equal(startupCalls, 1);
    assert.equal(controller.getState(), CONNECTION_STATES.online);
});


test("confirmed mid-session loss blocks business requests and mutations", async t => {
    let healthCalls = 0;
    let businessFetchCalls = 0;
    const controller = createConnectionController({
        fetchImpl: async () => {
            healthCalls += 1;
            return healthCalls === 1
                ? healthyResponse()
                : response({}, { ok: false, status: 503 });
        },
        ui: createUi()
    });
    await controller.initialize();
    await controller.verifyTransportFailure({
        error: new TypeError("business network failure")
    });
    setActiveConnectionController(controller);

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
        businessFetchCalls += 1;
        return healthyResponse();
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
        setActiveConnectionController(null);
    });

    await assert.rejects(
        apiRequest("/api/tasks", {
            method: "POST",
            body: JSON.stringify({ title: "must not queue" })
        }),
        error => {
            assert.ok(error instanceof HardHeadAvailabilityError);
            assert.equal(error.code, "HARDHEAD_UNAVAILABLE");
            return true;
        }
    );
    assert.equal(businessFetchCalls, 0);
    assert.equal(
        controller.getState(),
        CONNECTION_STATES.unavailable
    );
});


test("business network failure verifies health before global loss", async t => {
    let healthCalls = 0;
    const controller = createConnectionController({
        fetchImpl: async () => {
            healthCalls += 1;
            return healthCalls === 1
                ? healthyResponse()
                : response({}, { ok: false, status: 503 });
        },
        ui: createUi()
    });
    await controller.initialize();
    setActiveConnectionController(controller);

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
        throw new TypeError("network failure");
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
        setActiveConnectionController(null);
    });

    await assert.rejects(
        apiRequest("/api/projects"),
        HardHeadAvailabilityError
    );
    assert.equal(healthCalls, 2);
    assert.equal(
        controller.getState(),
        CONNECTION_STATES.unavailable
    );
});


test("502 through 504 trigger verification while domain errors do not", async t => {
    let verifyCalls = 0;
    const controller = {
        getState: () => CONNECTION_STATES.online,
        isBusinessAvailable: () => true,
        async verifyTransportFailure() {
            verifyCalls += 1;
            return {
                online: true,
                reason: "HardHead and its database are healthy."
            };
        }
    };
    setActiveConnectionController(controller);

    const originalFetch = globalThis.fetch;
    const statuses = [400, 404, 409, 502, 503, 504];
    const requests = [];
    globalThis.fetch = async (path, options) => {
        requests.push({ path, options });
        const status = statuses.shift();
        return response(
            { detail: `failure-${status}` },
            { ok: false, status }
        );
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
        setActiveConnectionController(null);
    });

    for (const status of [400, 404, 409, 502, 503, 504]) {
        await assert.rejects(
            apiRequest("/api/projects"),
            error => {
                assert.ok(error instanceof BackendApiError);
                assert.equal(error.status, status);
                return true;
            }
        );
    }

    assert.equal(verifyCalls, 3);
    assert.equal(
        requests.every(request => request.options.cache === "no-store"),
        true,
        "business API responses must never be read from cache"
    );
});


test("mid-session restoration requires a deliberate safe reload once", async () => {
    let healthCalls = 0;
    let editing = true;
    const ui = createUi();
    const windowRef = createWindow();
    const documentRef = {};
    const controller = createConnectionController({
        documentRef,
        windowRef,
        fetchImpl: async () => {
            healthCalls += 1;

            if (healthCalls === 2) {
                throw new TypeError("connection lost");
            }

            return healthyResponse();
        },
        editingStateCheck(receivedDocument) {
            assert.equal(receivedDocument, documentRef);
            return editing;
        },
        ui
    });

    await controller.initialize();
    await controller.verifyTransportFailure({
        error: new TypeError("request failed")
    });
    assert.equal(
        controller.getState(),
        CONNECTION_STATES.unavailable
    );

    await controller.retry();
    assert.equal(
        controller.getState(),
        CONNECTION_STATES.restoredReloadRequired
    );
    assert.equal(controller.isBusinessAvailable(), false);

    assert.equal(controller.requestReload(), false);
    assert.equal(ui.reloadBlocked, 1);
    assert.equal(windowRef.location.reloadCalls, 0);

    editing = false;
    assert.equal(controller.requestReload(), true);
    assert.equal(controller.requestReload(), false);
    assert.equal(windowRef.location.reloadCalls, 1);
});


test("availability gate is accessible and retry remains independently usable", async () => {
    const html = await readFile(
        path.join(frontendDirectory, "index.html"),
        "utf8"
    );
    const styles = await readFile(
        path.join(frontendDirectory, "styles.css"),
        "utf8"
    );

    assert.match(html, /id="hardhead-availability"/);
    assert.match(html, /role="alertdialog"/);
    assert.match(html, /aria-modal="true"/);
    assert.match(html, /aria-labelledby="hardhead-availability-title"/);
    assert.match(html, /aria-live="polite"/);
    assert.match(html, /Checking HardHead…/);
    assert.match(html, /id="hardhead-availability-retry"/);
    assert.match(html, /id="hardhead-availability-reload"/);
    assert.match(styles, /\.connection-blocked \.app/);
    assert.match(styles, /\.connection-gate/);
    assert.match(html, /id="pwa-update-notice"/);
    assert.match(html, /id="pwa-update-action"/);
});


test("legacy browser records remain migration-only with no fallback writes", async () => {
    const files = await Promise.all(
        [
            "pages/dashboard.js",
            "pages/inventory.js",
            "pages/tasks.js",
            "utils/inventoryStorage.js",
            "utils/projectStorage.js",
            "utils/storage.js"
        ].map(async file => [
            file,
            await readFile(path.join(frontendDirectory, file), "utf8")
        ])
    );
    const sources = Object.fromEntries(files);

    assert.doesNotMatch(
        sources["pages/dashboard.js"],
        /localStorage|getInventoryItems/
    );
    assert.doesNotMatch(
        sources["pages/inventory.js"],
        /persistenceMode === "browser"|saveInventoryItems|createBrowser/
    );
    assert.doesNotMatch(
        sources["pages/tasks.js"],
        /saveTasks|createBrowser|currentTasks\s*=\s*browserTasks/
    );
    assert.doesNotMatch(
        sources["utils/inventoryStorage.js"],
        /localStorage\.setItem/
    );
    assert.doesNotMatch(
        sources["utils/projectStorage.js"],
        /localStorage\.(?:getItem|setItem)/
    );
    assert.doesNotMatch(
        sources["utils/storage.js"],
        /localStorage\.setItem/
    );
});


test("frontend contains no business queue, replay, or runtime cache", async () => {
    const worker = await readFile(
        path.join(frontendDirectory, "service-worker.js"),
        "utf8"
    );
    const api = await readFile(
        path.join(frontendDirectory, "utils/api.js"),
        "utf8"
    );
    const connection = await readFile(
        path.join(frontendDirectory, "utils/connectionState.js"),
        "utf8"
    );

    assert.doesNotMatch(
        `${worker}\n${api}\n${connection}`,
        /indexedDB|sync\.register|Background Sync|mutation replay/
    );
    assert.doesNotMatch(worker, /\.put\(|\.add\(/);
    assert.match(api, /requestOptions\.cache = "no-store"/);
    assert.doesNotMatch(connection, /localStorage|indexedDB/);
});
