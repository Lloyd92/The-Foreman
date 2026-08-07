import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    setActiveConnectionController
} from "../utils/connectionState.js";
import {
    ACTIVE_SPACE_STORAGE_KEY,
    clearActiveSpace,
    getActiveSpaceId,
    setActiveSpace,
    SPACE_CONTEXT_HEADER
} from "../utils/spaceContext.js";
import { spaceApiRequest } from "../utils/spaceApi.js";
import {
    initializeSpaceSelection
} from "../utils/spaceSelection.js";


const defaultSpace = {
    id: "space-default",
    name: "HardHead Works"
};

const workshopSpace = {
    id: "space-workshop",
    name: "Workshop"
};


function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" }
    });
}


function createStorage(initial = {}) {
    const values = new Map(Object.entries(initial));

    return {
        getItem(key) {
            return values.has(key) ? values.get(key) : null;
        },
        setItem(key, value) {
            values.set(key, String(value));
        },
        removeItem(key) {
            values.delete(key);
        }
    };
}


function createSelectorDocument() {
    const listeners = new Map();
    let innerHTML = "";

    const selector = {
        dataset: {},
        disabled: true,
        options: [],
        value: "",

        get innerHTML() {
            return innerHTML;
        },

        set innerHTML(value) {
            innerHTML = value;

            if (value === "") {
                this.options = [];
            }
        },

        appendChild(option) {
            this.options.push(option);
        },

        addEventListener(type, listener) {
            listeners.set(type, listener);
        },

        dispatchChange() {
            listeners.get("change")?.({
                currentTarget: this
            });
        }
    };

    return {
        selector,

        documentRef: {
            getElementById(id) {
                return id === "active-space-select"
                    ? selector
                    : null;
            },

            createElement(tagName) {
                assert.equal(tagName, "option");

                return {
                    value: "",
                    textContent: ""
                };
            }
        }
    };
}


test(
    "Space-scoped requests omit unresolved context and replace stale headers",
    async t => {
        const originalFetch = globalThis.fetch;
        const observedSpaceIds = [];

        setActiveConnectionController(null);
        clearActiveSpace();

        globalThis.fetch = async (path, options = {}) => {
            assert.equal(path, "/api/tasks");

            observedSpaceIds.push(
                new Headers(options.headers || {})
                    .get(SPACE_CONTEXT_HEADER)
            );

            return jsonResponse([]);
        };

        t.after(() => {
            globalThis.fetch = originalFetch;
            clearActiveSpace();
            setActiveConnectionController(null);
        });

        await spaceApiRequest("/api/tasks", {
            headers: {
                [SPACE_CONTEXT_HEADER]: "caller-stale-space"
            }
        });

        setActiveSpace(workshopSpace);

        await spaceApiRequest("/api/tasks", {
            headers: {
                [SPACE_CONTEXT_HEADER]: "caller-stale-space"
            }
        });

        assert.deepEqual(
            observedSpaceIds,
            [null, workshopSpace.id]
        );
    }
);


test(
    "persisted Space resolves before rendering and reload is a hard boundary",
    async t => {
        const originalFetch = globalThis.fetch;
        const requests = [];
        const storage = createStorage({
            [ACTIVE_SPACE_STORAGE_KEY]: workshopSpace.id
        });
        const { selector, documentRef } =
            createSelectorDocument();
        const windowRef = {
            location: {
                reloadCalls: 0,
                reload() {
                    this.reloadCalls += 1;
                }
            }
        };

        setActiveConnectionController(null);
        clearActiveSpace();

        globalThis.fetch = async (path, options = {}) => {
            const spaceId = new Headers(options.headers || {})
                .get(SPACE_CONTEXT_HEADER);

            requests.push({ path, spaceId });

            if (path === "/api/spaces/active") {
                assert.equal(spaceId, workshopSpace.id);
                return jsonResponse(workshopSpace);
            }

            if (path === "/api/spaces") {
                assert.equal(spaceId, null);
                return jsonResponse([
                    defaultSpace,
                    workshopSpace
                ]);
            }

            throw new Error(`Unexpected request: ${path}`);
        };

        t.after(() => {
            globalThis.fetch = originalFetch;
            clearActiveSpace();
            setActiveConnectionController(null);
        });

        const result = await initializeSpaceSelection({
            storage,
            documentRef,
            windowRef
        });

        assert.equal(result.activeSpace.id, workshopSpace.id);
        assert.equal(getActiveSpaceId(), workshopSpace.id);
        assert.equal(selector.disabled, false);
        assert.equal(selector.value, workshopSpace.id);
        assert.deepEqual(
            selector.options.map(option => [
                option.value,
                option.textContent
            ]),
            [
                [defaultSpace.id, defaultSpace.name],
                [workshopSpace.id, workshopSpace.name]
            ]
        );
        assert.deepEqual(
            requests.map(request => request.path),
            [
                "/api/spaces/active",
                "/api/spaces"
            ]
        );

        selector.value = defaultSpace.id;
        selector.dispatchChange();

        assert.equal(
            storage.getItem(ACTIVE_SPACE_STORAGE_KEY),
            defaultSpace.id
        );
        assert.equal(selector.disabled, true);
        assert.equal(windowRef.location.reloadCalls, 1);

        // The old document remains authoritative until reload.
        assert.equal(getActiveSpaceId(), workshopSpace.id);
    }
);


test(
    "deleted persisted Space falls back to backend default",
    async t => {
        const originalFetch = globalThis.fetch;
        const requestedActiveSpaceIds = [];
        const storage = createStorage({
            [ACTIVE_SPACE_STORAGE_KEY]: "deleted-space"
        });
        const { selector, documentRef } =
            createSelectorDocument();

        setActiveConnectionController(null);
        clearActiveSpace();

        globalThis.fetch = async (path, options = {}) => {
            const spaceId = new Headers(options.headers || {})
                .get(SPACE_CONTEXT_HEADER);

            if (path === "/api/spaces/active") {
                requestedActiveSpaceIds.push(spaceId);

                if (spaceId === "deleted-space") {
                    return jsonResponse(
                        { detail: "Space not found." },
                        404
                    );
                }

                return jsonResponse(defaultSpace);
            }

            if (path === "/api/spaces") {
                return jsonResponse([
                    defaultSpace,
                    workshopSpace
                ]);
            }

            throw new Error(`Unexpected request: ${path}`);
        };

        t.after(() => {
            globalThis.fetch = originalFetch;
            clearActiveSpace();
            setActiveConnectionController(null);
        });

        const result = await initializeSpaceSelection({
            storage,
            documentRef,
            windowRef: {
                location: { reload() {} }
            }
        });

        assert.deepEqual(
            requestedActiveSpaceIds,
            ["deleted-space", null]
        );
        assert.equal(result.activeSpace.id, defaultSpace.id);
        assert.equal(selector.value, defaultSpace.id);
        assert.equal(
            storage.getItem(ACTIVE_SPACE_STORAGE_KEY),
            defaultSpace.id
        );
    }
);


test(
    "operational wrappers explicitly use the Space-scoped request helper",
    async () => {
        for (const fileName of [
            "tasksApi.js",
            "inventoryApi.js",
            "projectsApi.js",
            "operationsApi.js"
        ]) {
            const source = await readFile(
                new URL(
                    `../utils/${fileName}`,
                    import.meta.url
                ),
                "utf8"
            );

            assert.match(
                source,
                /import \{ spaceApiRequest \} from "\.\/spaceApi\.js";/
            );
            assert.doesNotMatch(
                source,
                /import \{ apiRequest \} from "\.\/api\.js";/
            );
        }
    }
);
