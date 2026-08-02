const SHELL_CACHE_NAME = "foreman-shell-v0.7.3-c5";
const FOREMAN_CACHE_PREFIX = "foreman-shell-";

// This exact, atomic set keeps one frontend release coherent. Runtime fetches
// never add resources to it.
const SHELL_ASSETS = Object.freeze([
    "/",
    "/index.html",
    "/styles.css",
    "/app.js",
    "/pages/dashboard.js",
    "/pages/inventory.js",
    "/pages/projects.js",
    "/pages/recovery.js",
    "/pages/tasks.js",
    "/utils/api.js",
    "/utils/connectionState.js",
    "/utils/inventoryApi.js",
    "/utils/inventoryStorage.js",
    "/utils/migrationOrchestrator.js",
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
    "/manifest.webmanifest",
    "/assets/icons/favicon.ico",
    "/assets/icons/icon-192.png",
    "/assets/icons/icon-512.png",
    "/assets/icons/icon-maskable-192.png",
    "/assets/icons/icon-maskable-512.png",
    "/assets/icons/apple-touch-icon.png"
]);
const SHELL_ASSET_PATHS = new Set(SHELL_ASSETS);

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(SHELL_CACHE_NAME).then(cache => (
            cache.addAll(SHELL_ASSETS)
        ))
    );
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(cacheNames => Promise.all(
            cacheNames
                .filter(cacheName => (
                    cacheName.startsWith(FOREMAN_CACHE_PREFIX) &&
                    cacheName !== SHELL_CACHE_NAME
                ))
                .map(cacheName => caches.delete(cacheName))
        ))
    );
});

self.addEventListener("message", event => {
    if (event.data?.type !== "ACTIVATE_UPDATE") {
        return;
    }

    const activation = self.skipWaiting();

    if (typeof event.waitUntil === "function") {
        event.waitUntil(activation);
    }
});

self.addEventListener("fetch", event => {
    const request = event.request;
    const url = new URL(request.url);

    // Business APIs and migrations are always owned by the network/backend.
    if (url.origin === self.location.origin &&
        url.pathname.startsWith("/api/")) {
        return;
    }

    // Writes are never cached, queued, synchronized, or replayed.
    if (request.method !== "GET") {
        return;
    }

    if (url.origin !== self.location.origin) {
        return;
    }

    if (url.pathname === "/service-worker.js") {
        return;
    }

    if (SHELL_ASSET_PATHS.has(url.pathname) && !url.search) {
        event.respondWith(
            caches.open(SHELL_CACHE_NAME).then(cache => (
                cache.match(url.pathname).then(response => {
                    if (!response) {
                        throw new Error(
                            `Required shell asset missing: ${url.pathname}`
                        );
                    }

                    return response;
                })
            ))
        );
        return;
    }

    if (request.mode === "navigate") {
        event.respondWith(
            caches.open(SHELL_CACHE_NAME).then(cache => (
                cache.match("/index.html").then(response => (
                    response || fetch(request)
                ))
            ))
        );
    }
});
