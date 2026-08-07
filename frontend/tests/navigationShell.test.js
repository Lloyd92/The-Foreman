import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    clearModuleContext,
    setModuleRegistry
} from "../utils/moduleContext.js";

const html = await readFile(
    new URL("../index.html", import.meta.url),
    "utf8"
);
const routerSource = await readFile(
    new URL("../utils/router.js", import.meta.url),
    "utf8"
);

function getNavigationMarkup(className) {
    const match = html.match(new RegExp(
        `<nav\\b[^>]*class="${className}"[^>]*>([\\s\\S]*?)<\\/nav>`
    ));

    assert.ok(match, `${className} must exist`);
    return match[1];
}

function getLinkLabels(markup) {
    return [...markup.matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/g)]
        .map(match => match[1].replace(/<[^>]+>/g, ""))
        .map(label => label.replace(/&amp;/g, "&"))
        .map(label => label.replace(/\s+/g, " ").trim());
}

function getPageMarkup(route) {
    const match = html.match(new RegExp(
        `<main\\b[^>]*data-page="${route}"[^>]*>` +
        `([\\s\\S]*?)<\\/main>`
    ));

    assert.ok(match, `${route} page must exist`);
    return match[1];
}

test("primary navigation contains only the permanent categories in order", () => {
    const labels = getLinkLabels(getNavigationMarkup("primary-nav"));

    assert.deepEqual(labels, [
        "Today",
        "Calendar",
        "Work",
        "Resources",
        "Money",
        "Library"
    ]);

    for (const legacyLabel of [
        "Dashboard",
        "Tasks",
        "Inventory",
        "Projects",
        "Mealworms",
        "Budget"
    ]) {
        assert.equal(labels.includes(legacyLabel), false);
    }
});

test("Settings and Account are separate utility navigation entries", () => {
    assert.deepEqual(
        getLinkLabels(getNavigationMarkup("utility-nav")),
        ["Settings", "Account"]
    );
});

test("permanent and secondary route pages exist exactly once", () => {
    const routes = [...html.matchAll(/data-page="([^"]+)"/g)]
        .map(match => match[1]);

    for (const route of [
        "today",
        "calendar",
        "work",
        "resources",
        "money",
        "library",
        "settings",
        "account",
        "tasks",
        "projects",
        "inventory",
        "mealworms",
        "budget",
        "recovery"
    ]) {
        assert.equal(
            routes.filter(currentRoute => currentRoute === route).length,
            1,
            `${route} must have one page`
        );
    }

    assert.equal(routes.includes("dashboard"), false);
    assert.equal(routes.length, new Set(routes).size);
    assert.equal(
        (html.match(/<main\b/g) || []).length,
        (html.match(/<\/main>/g) || []).length
    );
});

test("category pages link to their preserved secondary workspaces", () => {
    const expectedLinks = {
        work: ["tasks", "projects"],
        resources: ["inventory", "mealworms"],
        money: ["budget"],
        settings: ["recovery"]
    };

    for (const [route, links] of Object.entries(expectedLinks)) {
        const page = getPageMarkup(route);

        for (const link of links) {
            assert.match(page, new RegExp(`href="#${link}"`));
        }
    }
});

test("shell wording is neutral while preserving The Foreman identity", () => {
    assert.match(html, /<h1>The Foreman<\/h1>/);
    assert.doesNotMatch(html, /workshop command center/i);
    assert.doesNotMatch(html, /At-a-glance operations for HardHead Works/);
});

function setTestModuleRegistry({
    workEnabled = true,
    inventoryEnabled = true
} = {}) {
    setModuleRegistry([
        {
            moduleId: "work",
            name: "Work",
            description: "Work module",
            dependencies: [],
            contributionLocations: ["today", "work"],
            safeEnableRule: "dependencies-satisfied",
            safeDisableRule: "no-enabled-dependents",
            dataRetentionBehavior: "retain",
            defaultEnabled: true,
            enabled: workEnabled,
            health: "ready"
        },
        {
            moduleId: "inventory",
            name: "Inventory",
            description: "Inventory module",
            dependencies: [],
            contributionLocations: ["today", "resources"],
            safeEnableRule: "dependencies-satisfied",
            safeDisableRule: "no-enabled-dependents",
            dataRetentionBehavior: "retain",
            defaultEnabled: true,
            enabled: inventoryEnabled,
            health: "ready"
        }
    ]);
}


function createElement(dataName, route) {
    const classes = new Set();
    const attributes = new Map();

    return {
        dataset: { [dataName]: route },
        hidden: false,
        classList: {
            contains(name) {
                return classes.has(name);
            },
            toggle(name, enabled) {
                if (enabled) {
                    classes.add(name);
                } else {
                    classes.delete(name);
                }
            }
        },
        getAttribute(name) {
            return attributes.get(name) ?? null;
        },
        removeAttribute(name) {
            attributes.delete(name);
        },
        setAttribute(name, value) {
            attributes.set(name, value);
        }
    };
}

test("router defaults and canonicalizes while preserving secondary routes", async () => {
    const pageRoutes = [
        "today",
        "calendar",
        "work",
        "resources",
        "money",
        "library",
        "settings",
        "account",
        "tasks",
        "projects",
        "inventory",
        "mealworms",
        "budget",
        "recovery"
    ];
    const navigationRoutes = [
        "today",
        "calendar",
        "work",
        "resources",
        "money",
        "library",
        "settings",
        "account"
    ];
    const pages = pageRoutes.map(route => createElement("page", route));
    const links = navigationRoutes.map(route => createElement("route", route));
    const listeners = new Map();
    const replacementUrls = [];
    const location = {
        hash: "",
        pathname: "/index.html",
        search: "?source=test"
    };
    const previousWindow = globalThis.window;
    const previousDocument = globalThis.document;

    globalThis.window = {
        location,
        history: {
            replaceState(_state, _title, url) {
                replacementUrls.push(url);
                location.hash = url.slice(url.indexOf("#"));
            }
        },
        addEventListener(type, listener) {
            listeners.set(type, listener);
        }
    };
    globalThis.document = {
        querySelectorAll(selector) {
            if (selector === "[data-page]") {
                return pages;
            }
            if (selector === "[data-route]") {
                return links;
            }
            return [];
        }
    };

    function assertRoute(visibleRoute, activeRoute) {
        assert.deepEqual(
            pages.filter(page => !page.hidden)
                .map(page => page.dataset.page),
            [visibleRoute]
        );
        assert.deepEqual(
            links.filter(link => link.classList.contains("active"))
                .map(link => link.dataset.route),
            [activeRoute]
        );
        assert.equal(
            links.find(link => link.dataset.route === activeRoute)
                .getAttribute("aria-current"),
            "page"
        );
    }

    try {
        setTestModuleRegistry();

        const router = await import(
            `../utils/router.js?navigation-shell=${Date.now()}`
        );
        router.initializeRouter();

        assertRoute("today", "today");

        location.hash = "#dashboard";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#today");
        assertRoute("today", "today");

        location.hash = "#does-not-exist";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#today");
        assertRoute("today", "today");

        location.hash = "#tasks";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#tasks");
        assertRoute("tasks", "work");

        location.hash = "#recovery";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#recovery");
        assertRoute("recovery", "settings");

        assert.deepEqual(replacementUrls, [
            "/index.html?source=test#today",
            "/index.html?source=test#today"
        ]);
    } finally {
        clearModuleContext();
        globalThis.window = previousWindow;
        globalThis.document = previousDocument;
    }
});

test("disabled module routes return to their permanent category", async () => {
    const pageRoutes = [
        "today",
        "work",
        "resources",
        "money",
        "settings",
        "tasks",
        "projects",
        "inventory",
        "mealworms",
        "budget",
        "recovery"
    ];
    const navigationRoutes = [
        "today",
        "work",
        "resources",
        "money",
        "settings"
    ];
    const pages = pageRoutes.map(route => createElement("page", route));
    const links = navigationRoutes.map(route => createElement("route", route));
    const listeners = new Map();
    const replacementUrls = [];
    const location = {
        hash: "#tasks",
        pathname: "/index.html",
        search: "?source=modules"
    };
    const previousWindow = globalThis.window;
    const previousDocument = globalThis.document;

    globalThis.window = {
        location,
        history: {
            replaceState(_state, _title, url) {
                replacementUrls.push(url);
                location.hash = url.slice(url.indexOf("#"));
            }
        },
        addEventListener(type, listener) {
            listeners.set(type, listener);
        }
    };

    globalThis.document = {
        querySelectorAll(selector) {
            if (selector === "[data-page]") {
                return pages;
            }
            if (selector === "[data-route]") {
                return links;
            }
            return [];
        }
    };

    function assertRoute(visibleRoute, activeRoute) {
        assert.deepEqual(
            pages.filter(page => !page.hidden)
                .map(page => page.dataset.page),
            [visibleRoute]
        );
        assert.deepEqual(
            links.filter(link => link.classList.contains("active"))
                .map(link => link.dataset.route),
            [activeRoute]
        );
    }

    try {
        setTestModuleRegistry({
            workEnabled: false,
            inventoryEnabled: false
        });

        const router = await import(
            `../utils/router.js?disabled-modules=${Date.now()}`
        );
        router.initializeRouter();

        assert.equal(location.hash, "#work");
        assertRoute("work", "work");

        location.hash = "#projects";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#work");
        assertRoute("work", "work");

        location.hash = "#inventory";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#resources");
        assertRoute("resources", "resources");

        location.hash = "#mealworms";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#mealworms");
        assertRoute("mealworms", "resources");

        location.hash = "#budget";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#budget");
        assertRoute("budget", "money");

        location.hash = "#recovery";
        listeners.get("hashchange")();
        assert.equal(location.hash, "#recovery");
        assertRoute("recovery", "settings");

        assert.deepEqual(replacementUrls, [
            "/index.html?source=modules#work",
            "/index.html?source=modules#work",
            "/index.html?source=modules#resources"
        ]);
    } finally {
        clearModuleContext();
        globalThis.window = previousWindow;
        globalThis.document = previousDocument;
    }
});

test("router source declares Today and the Dashboard alias explicitly", () => {
    assert.match(routerSource, /const DEFAULT_ROUTE = "today";/);
    assert.match(routerSource, /dashboard:\s*DEFAULT_ROUTE/);
});
