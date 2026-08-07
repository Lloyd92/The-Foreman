import assert from "node:assert/strict";
import test from "node:test";

import {
    renderModuleSettings
} from "../pages/settings.js";


class TestElement {
    constructor(tagName = "div") {
        this.tagName = tagName;
        this.children = [];
        this.dataset = {};
        this.className = "";
        this.textContent = "";
        this.type = "";
        this.disabled = false;
        this.listeners = new Map();
    }

    append(...children) {
        this.children.push(...children);
    }

    appendChild(child) {
        this.children.push(child);
        return child;
    }

    replaceChildren(...children) {
        this.children = [...children];
    }

    addEventListener(type, listener) {
        this.listeners.set(type, listener);
    }

    dispatch(type) {
        const listener = this.listeners.get(type);

        if (!listener) {
            throw new Error(`No ${type} listener registered.`);
        }

        return listener();
    }
}


function moduleRecord({
    moduleId,
    name,
    enabled,
    dependencies = [],
    contributionLocations = []
}) {
    return {
        moduleId,
        name,
        description: `${name} description`,
        dependencies,
        contributionLocations,
        safeEnableRule: "dependencies-satisfied",
        safeDisableRule: "no-enabled-dependents",
        dataRetentionBehavior: "retain",
        defaultEnabled: true,
        enabled,
        health: "ready"
    };
}


function createDocumentHarness() {
    const list = new TestElement("div");
    const message = new TestElement("p");
    const previousDocument = globalThis.document;

    globalThis.document = {
        createElement(tagName) {
            return new TestElement(tagName);
        },
        getElementById(id) {
            if (id === "module-settings-list") {
                return list;
            }

            if (id === "module-settings-message") {
                return message;
            }

            return null;
        }
    };

    return {
        list,
        message,
        restore() {
            globalThis.document = previousDocument;
        }
    };
}


function findChild(element, predicate) {
    for (const child of element.children) {
        if (predicate(child)) {
            return child;
        }

        const nested = findChild(child, predicate);

        if (nested) {
            return nested;
        }
    }

    return null;
}


test("Settings renders authoritative module state and retention policy", () => {
    const harness = createDocumentHarness();

    try {
        renderModuleSettings([
            moduleRecord({
                moduleId: "work",
                name: "Work",
                enabled: true,
                contributionLocations: ["today", "work"]
            }),
            moduleRecord({
                moduleId: "inventory",
                name: "Inventory",
                enabled: false,
                contributionLocations: ["today", "resources"]
            })
        ]);

        assert.equal(harness.list.children.length, 2);

        const work = harness.list.children[0];
        const inventory = harness.list.children[1];

        assert.equal(work.dataset.moduleId, "work");
        assert.equal(inventory.dataset.moduleId, "inventory");

        assert.ok(
            findChild(
                work,
                child => child.textContent === "ENABLED"
            )
        );
        assert.ok(
            findChild(
                inventory,
                child => child.textContent === "DISABLED"
            )
        );
        assert.ok(
            findChild(
                inventory,
                child => child.textContent === "Data retained"
            )
        );

        assert.equal(harness.message.textContent, "");
    } finally {
        harness.restore();
    }
});


test("successful module mutation reloads only after validated response", async () => {
    const harness = createDocumentHarness();
    const calls = [];
    let reloads = 0;

    try {
        renderModuleSettings(
            [
                moduleRecord({
                    moduleId: "work",
                    name: "Work",
                    enabled: true
                })
            ],
            {
                async updateModule(moduleId, enabled) {
                    calls.push([moduleId, enabled]);

                    return {
                        moduleId,
                        enabled
                    };
                },
                reload() {
                    reloads += 1;
                }
            }
        );

        const button = findChild(
            harness.list,
            child => child.tagName === "button"
        );

        assert.equal(button.textContent, "Disable");

        await button.dispatch("click");

        assert.deepEqual(calls, [["work", false]]);
        assert.equal(reloads, 1);
        assert.equal(button.disabled, true);
        assert.equal(
            harness.message.textContent,
            "Work disabled. Reloading…"
        );
        assert.equal(harness.message.dataset.state, "success");
    } finally {
        harness.restore();
    }
});


test("malformed mutation response fails closed without reload", async () => {
    const harness = createDocumentHarness();
    let reloads = 0;

    try {
        renderModuleSettings(
            [
                moduleRecord({
                    moduleId: "inventory",
                    name: "Inventory",
                    enabled: false
                })
            ],
            {
                async updateModule() {
                    return {
                        moduleId: "inventory",
                        enabled: false
                    };
                },
                reload() {
                    reloads += 1;
                }
            }
        );

        const button = findChild(
            harness.list,
            child => child.tagName === "button"
        );

        await button.dispatch("click");

        assert.equal(reloads, 0);
        assert.equal(button.disabled, false);
        assert.equal(
            harness.message.textContent,
            "Backend returned an invalid module-state response."
        );
        assert.equal(harness.message.dataset.state, "error");
    } finally {
        harness.restore();
    }
});


test("backend mutation errors remain visible and retryable", async () => {
    const harness = createDocumentHarness();
    let reloads = 0;

    try {
        renderModuleSettings(
            [
                moduleRecord({
                    moduleId: "work",
                    name: "Work",
                    enabled: true
                })
            ],
            {
                async updateModule() {
                    throw new Error(
                        "Module has enabled dependents."
                    );
                },
                reload() {
                    reloads += 1;
                }
            }
        );

        const button = findChild(
            harness.list,
            child => child.tagName === "button"
        );

        await button.dispatch("click");

        assert.equal(reloads, 0);
        assert.equal(button.disabled, false);
        assert.equal(
            harness.message.textContent,
            "Module has enabled dependents."
        );
        assert.equal(harness.message.dataset.state, "error");
    } finally {
        harness.restore();
    }
});


test("empty registry reports unavailable modules without controls", () => {
    const harness = createDocumentHarness();

    try {
        renderModuleSettings([]);

        assert.equal(harness.list.children.length, 0);
        assert.equal(
            harness.message.textContent,
            "No registered modules are available."
        );
        assert.equal(harness.message.dataset.state, "error");
    } finally {
        harness.restore();
    }
});
