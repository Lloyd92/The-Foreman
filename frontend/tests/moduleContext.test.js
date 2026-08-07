import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    clearModuleContext,
    getModule,
    getModules,
    isModuleEnabled,
    setModuleRegistry
} from "../utils/moduleContext.js";
import {
    applyModuleContributions,
    isModuleRouteAvailable
} from "../utils/modulePresentation.js";


function moduleRecord({
    moduleId,
    name,
    enabled = true,
    dependencies = [],
    contributionLocations = []
}) {
    return {
        moduleId,
        name,
        description: `${name} module`,
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


function approvedRegistry({
    workEnabled = true,
    inventoryEnabled = true
} = {}) {
    return [
        moduleRecord({
            moduleId: "work",
            name: "Work",
            enabled: workEnabled,
            contributionLocations: ["today", "work"]
        }),
        moduleRecord({
            moduleId: "inventory",
            name: "Inventory",
            enabled: inventoryEnabled,
            contributionLocations: ["today", "resources"]
        })
    ];
}


test("validated registry becomes authoritative in-memory state", () => {
    try {
        const modules = setModuleRegistry(approvedRegistry());

        assert.equal(modules.length, 2);
        assert.equal(getModules().length, 2);
        assert.equal(getModule(" WORK ").moduleId, "work");
        assert.equal(isModuleEnabled("work"), true);
        assert.equal(isModuleEnabled("inventory"), true);
        assert.equal(isModuleEnabled("missing"), false);
        assert.equal(Object.isFrozen(getModule("work")), true);
        assert.equal(
            Object.isFrozen(getModule("work").contributionLocations),
            true
        );
    } finally {
        clearModuleContext();
    }
});


test("malformed registry contracts fail closed", () => {
    const invalidRegistries = [
        null,
        [
            ...approvedRegistry(),
            moduleRecord({
                moduleId: "WORK",
                name: "Duplicate Work"
            })
        ],
        [
            moduleRecord({
                moduleId: "work",
                name: "Work",
                dependencies: ["missing"]
            })
        ],
        [
            moduleRecord({
                moduleId: "work",
                name: "Work",
                dependencies: ["Inventory", "inventory"]
            }),
            moduleRecord({
                moduleId: "inventory",
                name: "Inventory"
            })
        ],
        [
            {
                ...moduleRecord({
                    moduleId: "work",
                    name: "Work"
                }),
                health: "unknown"
            }
        ]
    ];

    try {
        for (const value of invalidRegistries) {
            assert.throws(
                () => setModuleRegistry(value),
                TypeError
            );
        }
    } finally {
        clearModuleContext();
    }
});


test("disabled modules hide only their owned contributions", () => {
    try {
        setModuleRegistry(approvedRegistry({
            workEnabled: false,
            inventoryEnabled: true
        }));

        const work = {
            dataset: { moduleContribution: "work" },
            hidden: false
        };
        const inventory = {
            dataset: { moduleContribution: "inventory" },
            hidden: true
        };

        applyModuleContributions({
            querySelectorAll(selector) {
                assert.equal(
                    selector,
                    "[data-module-contribution]"
                );
                return [work, inventory];
            }
        });

        assert.equal(work.hidden, true);
        assert.equal(inventory.hidden, false);
    } finally {
        clearModuleContext();
    }
});


test("module-owned routes follow effective enablement", () => {
    try {
        setModuleRegistry(approvedRegistry({
            workEnabled: false,
            inventoryEnabled: false
        }));

        assert.equal(isModuleRouteAvailable("tasks"), false);
        assert.equal(isModuleRouteAvailable("projects"), false);
        assert.equal(isModuleRouteAvailable("inventory"), false);

        for (const route of [
            "today",
            "work",
            "resources",
            "mealworms",
            "budget",
            "recovery"
        ]) {
            assert.equal(
                isModuleRouteAvailable(route),
                true,
                `${route} remains outside disabled module ownership`
            );
        }
    } finally {
        clearModuleContext();
    }
});


test("module API remains installation-wide and generic", async () => {
    const source = await readFile(
        new URL("../utils/modulesApi.js", import.meta.url),
        "utf8"
    );

    assert.match(
        source,
        /import \{ apiRequest \} from "\.\/api\.js";/
    );
    assert.doesNotMatch(source, /spaceApiRequest/);
    assert.doesNotMatch(source, /X-Foreman-Space-Id/);
    assert.match(source, /apiRequest\("\/api\/modules"\)/);
    assert.match(
        source,
        /`\/api\/modules\/\$\{encodeURIComponent\(moduleId\)\}`/
    );
    assert.match(source, /method: "PATCH"/);
});
