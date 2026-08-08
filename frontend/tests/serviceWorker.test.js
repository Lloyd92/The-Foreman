import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const frontendDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    ".."
);
const workerPath = path.join(frontendDirectory, "service-worker.js");
const workerSource = await readFile(workerPath, "utf8");

const expectedShellAssets = [
    "/",
    "/index.html",
    "/styles.css",
    "/app.js",
    "/pages/dashboard.js",
    "/pages/inventory.js",
    "/pages/projects.js",
    "/pages/recovery.js",
    "/pages/settings.js",
    "/pages/tasks.js",
    "/pages/work.js",
    "/utils/api.js",
    "/utils/connectionState.js",
    "/utils/spaceApi.js",
    "/utils/spaceContext.js",
    "/utils/spaceSelection.js",
    "/utils/spacesApi.js",
    "/utils/modulesApi.js",
    "/utils/moduleContext.js",
    "/utils/modulePresentation.js",
    "/utils/inventoryApi.js",
    "/utils/inventoryStorage.js",
    "/utils/migrationOrchestrator.js",
    "/utils/migrationReporting.js",
    "/utils/projectMigration.js",
    "/utils/operationsApi.js",
    "/utils/recoveryApi.js",
    "/utils/projectRuntime.js",
    "/utils/projectStorage.js",
    "/utils/projectsApi.js",
    "/utils/pwa.js",
    "/utils/router.js",
    "/utils/storage.js",
    "/utils/tasksApi.js",
    "/utils/workApi.js",
    "/manifest.webmanifest",
    "/assets/icons/favicon.ico",
    "/assets/icons/icon-192.png",
    "/assets/icons/icon-512.png",
    "/assets/icons/icon-maskable-192.png",
    "/assets/icons/icon-maskable-512.png",
    "/assets/icons/apple-touch-icon.png"
];

function createWorkerHarness({
    addAllError = null,
    cacheNames = [],
    cachedResponses = {}
} = {}) {
    const listeners = new Map();
    const calls = {
        addAll: [],
        cacheDeletes: [],
        cacheMatches: [],
        cacheOpens: [],
        fetches: [],
        skipWaiting: 0
    };
    const cache = {
        async addAll(assets) {
            calls.addAll.push([...assets]);

            if (addAllError) {
                throw addAllError;
            }
        },
        async match(key) {
            const cacheKey = typeof key === "string" ? key : key.url;
            calls.cacheMatches.push(cacheKey);
            return cachedResponses[cacheKey];
        }
    };
    const context = {
        URL,
        caches: {
            async delete(cacheName) {
                calls.cacheDeletes.push(cacheName);
                return true;
            },
            async keys() {
                return [...cacheNames];
            },
            async open(cacheName) {
                calls.cacheOpens.push(cacheName);
                return cache;
            }
        },
        fetch: async request => {
            calls.fetches.push(request);
            return { source: "network" };
        },
        self: {
            location: { origin: "https://hardhead.home.arpa" },
            addEventListener(type, listener) {
                listeners.set(type, listener);
            },
            async skipWaiting() {
                calls.skipWaiting += 1;
            }
        }
    };

    vm.runInNewContext(workerSource, context, {
        filename: workerPath
    });

    function dispatch(type, properties = {}) {
        let responsePromise;
        let waitPromise;
        const event = {
            ...properties,
            respondWith(value) {
                responsePromise = Promise.resolve(value);
            },
            waitUntil(value) {
                waitPromise = Promise.resolve(value);
            }
        };

        listeners.get(type)(event);

        return { event, responsePromise, waitPromise };
    }

    return { calls, dispatch };
}

function request(pathname, {
    method = "GET",
    mode = "same-origin",
    origin = "https://hardhead.home.arpa"
} = {}) {
    return {
        method,
        mode,
        url: `${origin}${pathname}`
    };
}

test("install atomically precaches the exact versioned shell", async () => {
    const harness = createWorkerHarness();
    const install = harness.dispatch("install");

    await install.waitPromise;

    assert.equal(expectedShellAssets.length, 42);
    assert.equal(
        expectedShellAssets.includes("/utils/operationsApi.js"),
        true
    );
    assert.equal(
        expectedShellAssets.includes("/utils/recoveryApi.js"),
        true
    );
    assert.equal(
        expectedShellAssets.includes("/pages/recovery.js"),
        true
    );
    assert.equal(
        expectedShellAssets.includes("/utils/projectReadiness.js"),
        false
    );
    assert.equal(expectedShellAssets.includes("/index.html"), true);
    assert.deepEqual(
        harness.calls.cacheOpens,
        ["foreman-shell-v0.8.1-c1"]
    );
    assert.deepEqual(
        harness.calls.addAll,
        [expectedShellAssets]
    );
    assert.equal(
        expectedShellAssets.some(asset => asset.startsWith("/api/")),
        false
    );
    assert.equal(expectedShellAssets.includes("/service-worker.js"), false);

    for (const asset of expectedShellAssets) {
        const relativePath = asset === "/"
            ? "index.html"
            : asset.replace(/^\//, "");
        await access(path.join(frontendDirectory, relativePath));
    }
});

test("shell allowlist contains the complete startup ES-module graph", async () => {
    const shellAssets = new Set(expectedShellAssets);
    const moduleAssets = expectedShellAssets.filter(
        asset => asset.endsWith(".js")
    );

    for (const moduleAsset of moduleAssets) {
        const modulePath = path.join(
            frontendDirectory,
            moduleAsset.replace(/^\//, "")
        );
        const source = await readFile(modulePath, "utf8");
        const imports = [
            ...source.matchAll(/\bfrom\s+["']([^"']+)["']/g)
        ].map(match => match[1]);

        imports
            .filter(importPath => importPath.startsWith("."))
            .forEach(importPath => {
                const resolved = path.posix.normalize(
                    path.posix.join(
                        path.posix.dirname(moduleAsset),
                        importPath
                    )
                );

                assert.equal(
                    shellAssets.has(resolved),
                    true,
                    `${moduleAsset} imports missing shell asset ${resolved}`
                );
            });
    }
});

test("missing required asset rejects the atomic install", async () => {
    const harness = createWorkerHarness({
        addAllError: new Error("required asset missing")
    });
    const install = harness.dispatch("install");

    await assert.rejects(
        install.waitPromise,
        /required asset missing/
    );
    assert.equal(harness.calls.addAll.length, 1);
});

test("activate removes only stale Foreman shell caches", async () => {
    const harness = createWorkerHarness({
        cacheNames: [
            "foreman-shell-v0.7.1",
            "foreman-shell-v0.7.2",
            "foreman-shell-v0.7.2-c3",
            "foreman-shell-v0.7.2-c4",
            "foreman-shell-v0.7.2-c5",
            "foreman-shell-v0.7.3-c1",
            "foreman-shell-v0.7.3-c2",
            "foreman-shell-v0.7.3-c3",
            "foreman-shell-v0.7.3-c4",
            "foreman-shell-v0.7.3-c5",
            "foreman-shell-v0.7.4-c1",
            "foreman-shell-v0.7.5-c1",
            "foreman-shell-v0.7.5-c2",
            "foreman-shell-v0.7.5-c3",
            "foreman-shell-v0.7.5-c4",
            "foreman-shell-v0.7.5-c5",
            "unrelated-cache"
        ]
    });
    const activation = harness.dispatch("activate");

    await activation.waitPromise;

    assert.deepEqual(
        harness.calls.cacheDeletes,
        [
            "foreman-shell-v0.7.1",
            "foreman-shell-v0.7.2",
            "foreman-shell-v0.7.2-c3",
            "foreman-shell-v0.7.2-c4",
            "foreman-shell-v0.7.2-c5",
            "foreman-shell-v0.7.3-c1",
            "foreman-shell-v0.7.3-c2",
            "foreman-shell-v0.7.3-c3",
            "foreman-shell-v0.7.3-c4",
            "foreman-shell-v0.7.3-c5",
            "foreman-shell-v0.7.4-c1",
            "foreman-shell-v0.7.5-c1",
            "foreman-shell-v0.7.5-c2",
            "foreman-shell-v0.7.5-c3",
            "foreman-shell-v0.7.5-c4",
            "foreman-shell-v0.7.5-c5"
        ]
    );
    assert.equal(harness.calls.skipWaiting, 0);
    assert.doesNotMatch(workerSource, /clients\.claim/);
});

test("v0.7.5 c1 shell updates to the current v0.8.1 release shell", async () => {
    const installedC1Index = `
        <nav class="nav">
            <a href="#dashboard" data-route="dashboard">Dashboard</a>
        </nav>
        <span id="footer-version">0.7.5</span>
    `;
    const indexSource = await readFile(
        path.join(frontendDirectory, "index.html"),
        "utf8"
    );
    const harness = createWorkerHarness({
        cacheNames: [
            "foreman-shell-v0.7.5-c1",
            "unrelated-cache"
        ]
    });
    const install = harness.dispatch("install");

    assert.match(
        installedC1Index,
        /data-route="dashboard">Dashboard<\/a>/
    );
    assert.doesNotMatch(
        installedC1Index,
        /data-route="today">Today<\/a>/
    );

    await install.waitPromise;

    const activation = harness.dispatch("activate");
    await activation.waitPromise;

    assert.match(
        indexSource,
        /id="footer-version">\s*0\.8\.1\s*<\/span>/
    );
    assert.match(indexSource, /data-route="today"/);
    assert.doesNotMatch(indexSource, /data-route="dashboard"/);
    assert.deepEqual(
        harness.calls.cacheOpens,
        ["foreman-shell-v0.8.1-c1"]
    );
    assert.equal(
        harness.calls.addAll[0].includes("/pages/recovery.js"),
        true
    );
    assert.deepEqual(
        harness.calls.cacheDeletes,
        ["foreman-shell-v0.7.5-c1"]
    );
    assert.equal(harness.calls.skipWaiting, 0);
});

test("worker skips waiting only after explicit activation message", async () => {
    const harness = createWorkerHarness();

    harness.dispatch("message", { data: { type: "OTHER" } });
    assert.equal(harness.calls.skipWaiting, 0);

    const activation = harness.dispatch("message", {
        data: { type: "ACTIVATE_UPDATE" }
    });
    await activation.waitPromise;

    assert.equal(harness.calls.skipWaiting, 1);
});

test("API, migration, mutation, worker, unknown, and cross-origin requests are network-only", () => {
    const harness = createWorkerHarness();
    const requests = [
        request("/api/projects"),
        request("/api/project-migrations/browser"),
        request("/api/tasks", { method: "POST" }),
        request("/api/inventory/item", { method: "PATCH" }),
        request("/somewhere", { method: "PUT" }),
        request("/somewhere", { method: "DELETE" }),
        request("/service-worker.js"),
        request("/unknown.js"),
        request("/external.js", {
            origin: "https://example.com"
        })
    ];

    requests.forEach(currentRequest => {
        const fetchEvent = harness.dispatch("fetch", {
            request: currentRequest
        });

        assert.equal(fetchEvent.responsePromise, undefined);
    });

    assert.deepEqual(harness.calls.cacheMatches, []);
    assert.deepEqual(harness.calls.fetches, []);
    assert.doesNotMatch(workerSource, /Background Sync|indexedDB|sync\.register/);
    assert.doesNotMatch(workerSource, /\.put\(|\.add\(/);
});

test("exact shell assets are served only from the current cache", async () => {
    const cachedResponse = { source: "shell-cache" };
    const harness = createWorkerHarness({
        cachedResponses: {
            "/app.js": cachedResponse
        }
    });
    const fetchEvent = harness.dispatch("fetch", {
        request: request("/app.js")
    });

    assert.equal(await fetchEvent.responsePromise, cachedResponse);
    assert.deepEqual(
        harness.calls.cacheOpens,
        ["foreman-shell-v0.8.1-c1"]
    );
    assert.deepEqual(harness.calls.cacheMatches, ["/app.js"]);
    assert.deepEqual(harness.calls.fetches, []);
});

test("missing current-cache shell asset fails instead of mixing versions", async () => {
    const harness = createWorkerHarness();
    const fetchEvent = harness.dispatch("fetch", {
        request: request("/styles.css")
    });

    await assert.rejects(
        fetchEvent.responsePromise,
        /Required shell asset missing/
    );
    assert.deepEqual(harness.calls.fetches, []);
});

test("navigation uses cached index and falls back to network only when absent", async () => {
    const cachedIndex = { source: "cached-index" };
    const cachedHarness = createWorkerHarness({
        cachedResponses: { "/index.html": cachedIndex }
    });
    const cachedNavigation = cachedHarness.dispatch("fetch", {
        request: request("/projects", { mode: "navigate" })
    });

    assert.equal(await cachedNavigation.responsePromise, cachedIndex);
    assert.deepEqual(
        cachedHarness.calls.cacheMatches,
        ["/index.html"]
    );
    assert.deepEqual(cachedHarness.calls.fetches, []);

    const networkHarness = createWorkerHarness();
    const networkRequest = request("/projects", { mode: "navigate" });
    const networkNavigation = networkHarness.dispatch("fetch", {
        request: networkRequest
    });

    assert.deepEqual(
        await networkNavigation.responsePromise,
        { source: "network" }
    );
    assert.deepEqual(networkHarness.calls.fetches, [networkRequest]);
});
