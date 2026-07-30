import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    getDashboardInventoryEntries,
    getDashboardProjectMetrics
} from "../pages/dashboard.js";
import {
    getInventoryOperationalState,
    getInventoryStockPresentation
} from "../pages/inventory.js";
import {
    getMaterialEvidencePresentation,
    getProjectReadinessPresentation
} from "../pages/projects.js";


function operationalFacts() {
    return {
        facts: [
            {
                factId: "inventory/item-1/stock-level",
                factType: "inventory.stock-level",
                subjectType: "inventory",
                subjectId: "item-1",
                state: "out-of-stock"
            }
        ],
        summary: {
            projects: {
                byStatus: {
                    planning: 4,
                    active: 3,
                    onHold: 2,
                    completed: 1,
                    archived: 0,
                    invalid: 0
                },
                materialReadiness: {
                    ready: 1,
                    needsMaterials: 2,
                    notApplicable: 3,
                    invalid: 1
                }
            },
            inventory: {
                total: 1,
                inStock: 0,
                lowStock: 0,
                outOfStock: 1,
                lowOrOutOfStock: 1,
                invalid: 0
            }
        }
    };
}


test("Dashboard project metrics come directly from normalized summary", () => {
    assert.deepEqual(
        getDashboardProjectMetrics(operationalFacts()),
        {
            active: 3,
            ready: 1,
            needsMaterials: 2,
            notApplicable: 3,
            invalid: 1
        }
    );
    assert.equal(getDashboardProjectMetrics(null), null);
});


test("Dashboard inventory alerts use stock facts instead of quantities", () => {
    const items = [{
        id: "item-1",
        name: "Contradictory display record",
        quantity: 999,
        minimum: 0,
        isLow: false
    }];

    assert.deepEqual(
        getDashboardInventoryEntries(
            items,
            operationalFacts()
        ).map(entry => entry.state),
        ["out-of-stock"]
    );
    assert.equal(
        getDashboardInventoryEntries(items, null)[0].state,
        "unknown"
    );
});


test("Inventory keeps low, out, invalid, and missing states distinct", () => {
    const facts = operationalFacts();

    assert.equal(
        getInventoryOperationalState(facts, "item-1"),
        "out-of-stock"
    );
    assert.equal(
        getInventoryOperationalState(facts, "missing"),
        "unknown"
    );
    assert.deepEqual(
        getInventoryStockPresentation("low-stock"),
        {
            label: "LOW STOCK",
            className: "stock-badge-low",
            attention: true
        }
    );
    assert.equal(
        getInventoryStockPresentation("out-of-stock").label,
        "OUT OF STOCK"
    );
    assert.equal(
        getInventoryStockPresentation("invalid").label,
        "INVALID STOCK DATA"
    );
    assert.equal(
        getInventoryStockPresentation("unknown").label,
        "STATUS UNAVAILABLE"
    );
    assert.equal(
        getInventoryStockPresentation("in-stock").attention,
        false
    );
});


test("Project readiness preserves all backend states", () => {
    for (const [state, label] of [
        ["ready", "READY"],
        ["needs-materials", "NEEDS MATERIALS"],
        ["not-applicable", "NOT APPLICABLE"],
        ["invalid", "INVALID MATERIAL DATA"]
    ]) {
        assert.deepEqual(
            getProjectReadinessPresentation({ state }),
            { state, label }
        );
    }

    assert.deepEqual(
        getProjectReadinessPresentation(null),
        {
            state: "unknown",
            label: "READINESS UNAVAILABLE"
        }
    );
});


test("Project material evidence uses backend availability and shortage", () => {
    const insufficient = getMaterialEvidencePresentation({
        itemName: "Fasteners",
        unit: "boxes",
        requiredQuantity: 5,
        availableQuantity: 2,
        shortageQuantity: 3,
        reasonCode: "PROJECT_MATERIAL_QUANTITY_INSUFFICIENT"
    });
    const missing = getMaterialEvidencePresentation({
        itemName: null,
        unit: null,
        requiredQuantity: 2,
        availableQuantity: null,
        shortageQuantity: null,
        reasonCode: "PROJECT_MATERIAL_INVENTORY_MISSING"
    });
    const invalid = getMaterialEvidencePresentation({
        itemName: "Invalid",
        unit: "units",
        requiredQuantity: "NaN",
        availableQuantity: "Infinity",
        shortageQuantity: null,
        reasonCode: "PROJECT_MATERIAL_DATA_INVALID"
    });
    const unavailable = getMaterialEvidencePresentation({
        itemName: "Display-only record",
        unit: "pieces",
        requiredQuantity: 1,
        availableQuantity: null,
        shortageQuantity: null,
        reasonCode: null
    });

    assert.equal(insufficient.status, "INSUFFICIENT");
    assert.equal(insufficient.shortage, "3");
    assert.equal(missing.status, "MISSING INVENTORY");
    assert.equal(missing.available, "Unknown");
    assert.equal(missing.shortage, "Unknown");
    assert.notEqual(missing.available, "0");
    assert.equal(invalid.status, "INVALID DATA");
    assert.equal(invalid.required, "NaN");
    assert.equal(invalid.available, "Infinity");
    assert.equal(unavailable.status, "EVIDENCE UNAVAILABLE");
    assert.equal(unavailable.available, "Unknown");
});


test("page sources contain no operational numeric or legacy fallback", async () => {
    const [dashboard, projects, inventory] = await Promise.all([
        readFile(
            new URL("../pages/dashboard.js", import.meta.url),
            "utf8"
        ),
        readFile(
            new URL("../pages/projects.js", import.meta.url),
            "utf8"
        ),
        readFile(
            new URL("../pages/inventory.js", import.meta.url),
            "utf8"
        )
    ]);
    const combined = `${dashboard}\n${projects}\n${inventory}`;

    assert.doesNotMatch(combined, /projectReadiness/);
    assert.doesNotMatch(
        combined,
        /quantity\s*(?:<=|===)\s*(?:item\.)?minimum/
    );
    assert.doesNotMatch(combined, /item\.isLow\s*\?\?/);
    assert.doesNotMatch(combined, /localStorage|indexedDB/i);
    assert.match(dashboard, /summary\.materialReadiness/);
    assert.match(dashboard, /"NO INVENTORY"/);
    assert.doesNotMatch(
        dashboard,
        /statusElement\.textContent\s*=\s*"READY"/
    );
    assert.match(projects, /evidence\.shortageQuantity/);
    assert.match(projects, /"READINESS UNAVAILABLE"/);
    assert.match(inventory, /"OUT OF STOCK"/);
    assert.match(inventory, /"INVALID STOCK DATA"/);
});
