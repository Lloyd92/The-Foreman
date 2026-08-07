import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    HardHeadAvailabilityError,
    setActiveConnectionController
} from "../utils/connectionState.js";
import {
    getInventoryStockLevelFact,
    getOperationalFacts,
    getProjectMaterialReadinessFact,
    indexFactsById,
    indexFactsByTypeAndSubject,
    OperationalFactsContractError,
    validateOperationalFactsResponse
} from "../utils/operationsApi.js";


function summary() {
    return {
        projects: {
            byStatus: {
                planning: 1,
                active: 0,
                onHold: 0,
                completed: 0,
                archived: 0,
                invalid: 0
            },
            materialReadiness: {
                ready: 0,
                needsMaterials: 1,
                notApplicable: 0,
                invalid: 0
            }
        },
        tasks: {
            open: 0,
            completed: 0,
            byPriority: {
                high: 0,
                medium: 0,
                low: 0
            }
        },
        inventory: {
            total: 1,
            inStock: 0,
            lowStock: 1,
            outOfStock: 0,
            lowOrOutOfStock: 1,
            invalid: 0
        }
    };
}


function projectReadinessFact(overrides = {}) {
    return {
        factId: "project/project-1/material-readiness",
        factType: "project.material-readiness",
        subjectType: "project",
        subjectId: "project-1",
        state: "needs-materials",
        reasonCodes: [
            "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"
        ],
        evidence: {
            requirements: [
                {
                    inventoryItemId: "inventory-1",
                    itemName: "Fasteners",
                    unit: "boxes",
                    requiredQuantity: 3,
                    availableQuantity: 1,
                    shortageQuantity: 2,
                    reasonCode: (
                        "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"
                    )
                }
            ]
        },
        sourceRecords: [],
        ...overrides
    };
}


function inventoryFact(overrides = {}) {
    return {
        factId: "inventory/inventory-1/stock-level",
        factType: "inventory.stock-level",
        subjectType: "inventory",
        subjectId: "inventory-1",
        state: "low-stock",
        reasonCodes: ["INVENTORY_AT_OR_BELOW_MINIMUM"],
        evidence: {
            quantity: 1,
            minimum: 2,
            unit: "boxes"
        },
        sourceRecords: [],
        ...overrides
    };
}


function response(overrides = {}) {
    return {
        schemaVersion: 1,
        facts: [
            projectReadinessFact(),
            inventoryFact()
        ],
        summary: summary(),
        activeProjects: [],
        completedTasks: [],
        incompleteTasks: [],
        inventory: [],
        projectStatusCounts: {},
        taskPriorityCounts: {
            high: 0,
            medium: 0,
            low: 0
        },
        ...overrides
    };
}


test("requests operational facts through the centralized API helper", async t => {
    const originalFetch = globalThis.fetch;
    let request;

    globalThis.fetch = async (path, options) => {
        request = { path, options };
        return new Response(JSON.stringify(response()), {
            status: 200,
            headers: { "Content-Type": "application/json" }
        });
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const result = await getOperationalFacts();

    assert.equal(request.path, "/api/operational-facts");
    assert.equal(request.options.cache, "no-store");
    assert.equal(result.schemaVersion, 1);
    assert.equal(result.facts.length, 2);
});


test("requires schema version, facts array, and complete summary", () => {
    assert.throws(
        () => validateOperationalFactsResponse(
            response({ schemaVersion: "1" })
        ),
        OperationalFactsContractError
    );
    assert.throws(
        () => validateOperationalFactsResponse(
            response({ facts: {} })
        ),
        /facts must be an array/
    );

    const incompleteSummary = summary();
    delete incompleteSummary.projects.materialReadiness.invalid;

    assert.throws(
        () => validateOperationalFactsResponse(
            response({ summary: incompleteSummary })
        ),
        /materialReadiness\.invalid/
    );
});


test("rejects duplicate IDs, unknown types, and malformed facts", () => {
    assert.throws(
        () => validateOperationalFactsResponse(response({
            facts: [
                projectReadinessFact(),
                projectReadinessFact()
            ]
        })),
        /factId must be unique/
    );
    assert.throws(
        () => validateOperationalFactsResponse(response({
            facts: [
                inventoryFact({
                    factType: "inventory.browser-guess"
                })
            ]
        })),
        /factType is unsupported/
    );
    assert.throws(
        () => validateOperationalFactsResponse(response({
            facts: [
                inventoryFact({ subjectId: "" })
            ]
        })),
        /subjectId must be a nonempty string/
    );
});


test("malformed normalized data never falls back to legacy fields", () => {
    const legacyOnly = response({
        schemaVersion: 2,
        facts: null,
        activeProjects: [{ id: "legacy-project" }],
        inventory: [{ recordId: "legacy-inventory" }]
    });

    assert.throws(
        () => validateOperationalFactsResponse(legacyOnly),
        /schemaVersion must equal numeric 1/
    );
});


test("indexing helpers return exact facts and deliberate null misses", () => {
    const operationalFacts = response();
    const byId = indexFactsById(operationalFacts);
    const bySubject = indexFactsByTypeAndSubject(
        operationalFacts
    );

    assert.equal(
        byId.get(
            "project/project-1/material-readiness"
        ),
        operationalFacts.facts[0]
    );
    assert.equal(
        getProjectMaterialReadinessFact(
            bySubject,
            "project-1"
        ),
        operationalFacts.facts[0]
    );
    assert.equal(
        getInventoryStockLevelFact(
            operationalFacts,
            "inventory-1"
        ),
        operationalFacts.facts[1]
    );
    assert.equal(
        getProjectMaterialReadinessFact(
            operationalFacts,
            "missing"
        ),
        null
    );
    assert.equal(
        getInventoryStockLevelFact(
            operationalFacts,
            "missing"
        ),
        null
    );
});


test("API failures are preserved and never fabricate empty facts", async t => {
    const originalFetch = globalThis.fetch;
    const failure = new TypeError("network unavailable");

    globalThis.fetch = async () => {
        throw failure;
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    await assert.rejects(
        getOperationalFacts(),
        error => error === failure
    );
});


test("connection availability errors remain distinguishable", async t => {
    setActiveConnectionController({
        isBusinessAvailable: () => false,
        getState: () => "unavailable"
    });
    t.after(() => {
        setActiveConnectionController(null);
    });

    await assert.rejects(
        getOperationalFacts(),
        error => (
            error instanceof HardHeadAvailabilityError &&
            error.code === "HARDHEAD_UNAVAILABLE"
        )
    );
});


test("module has no browser storage, direct fetch, or legacy fallback", async () => {
    const source = await readFile(
        new URL("../utils/operationsApi.js", import.meta.url),
        "utf8"
    );

    assert.match(source, /import \{ spaceApiRequest \} from "\.\/spaceApi\.js"/);
    assert.doesNotMatch(source, /\bfetch\s*\(/);
    assert.doesNotMatch(source, /localStorage|indexedDB/i);
    assert.doesNotMatch(
        source,
        /activeProjects|completedTasks|incompleteTasks|projectStatusCounts|taskPriorityCounts/
    );
});
