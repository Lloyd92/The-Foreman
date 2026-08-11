let resourcesInitialized = false;


function validCount(value) {
    return (
        Number.isInteger(value) &&
        value >= 0
    )
        ? value
        : null;
}


export function summarizeTools(tools) {
    return {
        total: Array.isArray(tools)
            ? tools.length
            : null
    };
}


export function summarizeInventory(
    items,
    operationalFacts
) {
    const summary = operationalFacts?.summary?.inventory;

    return {
        total: Array.isArray(items)
            ? items.length
            : null,
        lowOrOutOfStock: validCount(
            summary?.lowOrOutOfStock
        )
    };
}


export function summarizeCarePlans(carePlans) {
    if (!Array.isArray(carePlans)) {
        return {
            total: null,
            linkedToTool: null
        };
    }

    return {
        total: carePlans.length,
        linkedToTool: carePlans.filter(
            carePlan => (
                typeof carePlan?.toolId === "string" &&
                carePlan.toolId.trim() !== ""
            )
        ).length
    };
}


function metricText(
    status,
    value
) {
    if (status === "disabled") {
        return "Disabled";
    }

    if (status === "loading") {
        return "Loading…";
    }

    return value === null
        ? "Unavailable"
        : String(value);
}


function setMetric(
    id,
    status,
    value
) {
    const element = document.getElementById(id);

    if (!element) {
        return;
    }

    element.textContent = metricText(status, value);
    element.dataset.state = (
        status === "complete" && value !== null
            ? "available"
            : status
    );
}


function createInitialState(enabled) {
    return {
        status: enabled ? "loading" : "disabled",
        records: null
    };
}


function renderResourcesOverview(state) {
    const tools = summarizeTools(state.tools.records);
    const inventory = summarizeInventory(
        state.inventory.records,
        state.inventory.operationalFacts
    );
    const care = summarizeCarePlans(state.care.records);

    setMetric(
        "resources-tools-total",
        state.tools.status,
        tools.total
    );

    setMetric(
        "resources-inventory-total",
        state.inventory.status,
        inventory.total
    );

    setMetric(
        "resources-inventory-attention",
        state.inventory.status,
        inventory.lowOrOutOfStock
    );

    setMetric(
        "resources-care-total",
        state.care.status,
        care.total
    );

    setMetric(
        "resources-care-linked",
        state.care.status,
        care.linkedToTool
    );
}


function applyToolsResult(
    state,
    result
) {
    if (result?.status !== "complete") {
        state.tools = {
            status: "unavailable",
            records: null
        };
        return;
    }

    state.tools = {
        status: "complete",
        records: Array.isArray(result.tools)
            ? result.tools
            : null
    };
}


function applyInventoryResult(
    state,
    result
) {
    if (result?.status !== "complete") {
        state.inventory = {
            status: "unavailable",
            records: null,
            operationalFacts: null
        };
        return;
    }

    state.inventory = {
        status: "complete",
        records: Array.isArray(result.items)
            ? result.items
            : null,
        operationalFacts:
            result.operationalFacts ?? null
    };
}


function applyCareResult(
    state,
    result
) {
    if (result?.status !== "complete") {
        state.care = {
            status: "unavailable",
            records: null
        };
        return;
    }

    state.care = {
        status: "complete",
        records: Array.isArray(result.carePlans)
            ? result.carePlans
            : null
    };
}


async function resolveInitialization(
    initialization,
    applyResult,
    state
) {
    try {
        const result = await initialization;
        applyResult(state, result);
    } catch (error) {
        console.error(
            "Resources overview source initialization failed:",
            error
        );
        applyResult(
            state,
            {
                status: "unavailable",
                error
            }
        );
    }

    renderResourcesOverview(state);
}


export function initializeResourcesPage({
    toolsEnabled = false,
    inventoryEnabled = false,
    careEnabled = false,
    toolsInitialization = null,
    inventoryInitialization = null,
    careInitialization = null
} = {}) {
    if (resourcesInitialized) {
        return Promise.resolve({
            status: "already-initialized"
        });
    }

    resourcesInitialized = true;

    const state = {
        tools: createInitialState(toolsEnabled),
        inventory: {
            ...createInitialState(inventoryEnabled),
            operationalFacts: null
        },
        care: createInitialState(careEnabled)
    };

    renderResourcesOverview(state);

    if (toolsEnabled) {
        document.addEventListener(
            "tools:updated",
            event => {
                state.tools = {
                    status:
                        event.detail?.status === "unavailable"
                            ? "unavailable"
                            : "complete",
                    records: Array.isArray(event.detail?.tools)
                        ? event.detail.tools
                        : null
                };

                renderResourcesOverview(state);
            }
        );
    }

    if (inventoryEnabled) {
        document.addEventListener(
            "inventory:updated",
            event => {
                state.inventory = {
                    status: "complete",
                    records: Array.isArray(event.detail?.items)
                        ? event.detail.items
                        : null,
                    operationalFacts:
                        event.detail?.operationalFacts ?? null
                };

                renderResourcesOverview(state);
            }
        );
    }

    if (careEnabled) {
        document.addEventListener(
            "care:updated",
            event => {
                state.care = {
                    status:
                        event.detail?.status === "unavailable"
                            ? "unavailable"
                            : "complete",
                    records: Array.isArray(
                        event.detail?.carePlans
                    )
                        ? event.detail.carePlans
                        : null
                };

                renderResourcesOverview(state);
            }
        );
    }

    const initializations = [];

    if (toolsEnabled) {
        initializations.push(
            resolveInitialization(
                toolsInitialization,
                applyToolsResult,
                state
            )
        );
    }

    if (inventoryEnabled) {
        initializations.push(
            resolveInitialization(
                inventoryInitialization,
                applyInventoryResult,
                state
            )
        );
    }

    if (careEnabled) {
        initializations.push(
            resolveInitialization(
                careInitialization,
                applyCareResult,
                state
            )
        );
    }

    return Promise.all(initializations).then(() => ({
        status: "complete"
    }));
}
