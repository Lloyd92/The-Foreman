import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    summarizeCarePlans,
    summarizeInventory,
    summarizeTools
} from "../pages/resources.js";


const [
    resourcesSource,
    inventorySource,
    toolsSource,
    careSource,
    html,
    app
] = await Promise.all([
    readFile(
        new URL("../pages/resources.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../pages/inventory.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../pages/tools.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../pages/care.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../index.html", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../app.js", import.meta.url),
        "utf8"
    )
]);


test("Resources counts factual Tool records only", () => {
    assert.deepEqual(
        summarizeTools([
            {
                id: "tool-1",
                condition: "Needs service",
                availability: "Unknown"
            },
            {
                id: "tool-2",
                condition: "Excellent",
                availability: "Available"
            }
        ]),
        { total: 2 }
    );

    assert.deepEqual(
        summarizeTools(null),
        { total: null }
    );
});


test(
    "Resources Inventory uses normalized stock summary without deriving stock",
    () => {
        const items = [
            {
                id: "inventory-1",
                quantity: 999,
                minimum: 0
            },
            {
                id: "inventory-2",
                quantity: 999,
                minimum: 0
            }
        ];

        assert.deepEqual(
            summarizeInventory(
                items,
                {
                    summary: {
                        inventory: {
                            total: 2,
                            lowOrOutOfStock: 1
                        }
                    }
                }
            ),
            {
                total: 2,
                lowOrOutOfStock: 1
            }
        );

        assert.deepEqual(
            summarizeInventory(items, null),
            {
                total: 2,
                lowOrOutOfStock: null
            }
        );

        assert.deepEqual(
            summarizeInventory(null, null),
            {
                total: null,
                lowOrOutOfStock: null
            }
        );
    }
);


test(
    "Resources Care counts only persisted Tool references",
    () => {
        assert.deepEqual(
            summarizeCarePlans([
                {
                    id: "care-1",
                    toolId: "tool-1"
                },
                {
                    id: "care-2",
                    toolId: null
                },
                {
                    id: "care-3",
                    toolId: ""
                }
            ]),
            {
                total: 3,
                linkedToTool: 1
            }
        );

        assert.deepEqual(
            summarizeCarePlans(null),
            {
                total: null,
                linkedToTool: null
            }
        );
    }
);


test(
    "Resources receives existing authoritative page state instead of refetching",
    () => {
        assert.match(
            app,
            /initializeResourcesPage\(\{[\s\S]*toolsInitialization[\s\S]*inventoryInitialization[\s\S]*careInitialization/
        );

        assert.match(
            inventorySource,
            /operationalFacts:\s*inventoryOperationalFacts/
        );
        assert.match(
            toolsSource,
            /new CustomEvent\([\s\S]*"tools:updated"/
        );
        assert.match(
            careSource,
            /new CustomEvent\([\s\S]*"care:updated"/
        );

        assert.doesNotMatch(
            resourcesSource,
            /getOperationalFacts|listInventoryItems|listTools|listCarePlans/
        );
        assert.doesNotMatch(
            resourcesSource,
            /\bfetch\s*\(/
        );
    }
);


test(
    "Resources overview preserves unavailable rather than fabricating zero",
    () => {
        assert.match(
            resourcesSource,
            /value === null[\s\S]*"Unavailable"/
        );

        assert.doesNotMatch(
            resourcesSource,
            /quantity\s*(?:<=|<|===)\s*minimum/
        );
        assert.doesNotMatch(
            resourcesSource,
            /availability\s*===|condition\s*===/
        );
    }
);


test(
    "Resources overview remains factual and outside decision-engine authority",
    () => {
        const combined = [
            resourcesSource,
            inventorySource,
            toolsSource,
            careSource
        ].join("\n");

        assert.doesNotMatch(
            resourcesSource,
            /\/api\/resources\b|resource_items|resourceItems/
        );
        assert.doesNotMatch(
            resourcesSource,
            /localStorage|sessionStorage|indexedDB/
        );
        assert.doesNotMatch(
            resourcesSource,
            /\bcapacity\b|\bpriority\b|\brecommendations?\b/i
        );

        for (const id of [
            "resources-tools-total",
            "resources-inventory-total",
            "resources-inventory-attention",
            "resources-care-total",
            "resources-care-linked"
        ]) {
            assert.match(
                html,
                new RegExp(`id="${id}"`)
            );
        }

        assert.doesNotMatch(
            combined,
            /careDue|overdueCare|toolReadiness/
        );
    }
);
