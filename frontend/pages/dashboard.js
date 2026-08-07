import {
    listInventoryItems
} from "../utils/inventoryApi.js";
import {
    getInventoryStockLevelFact,
    getOperationalFacts
} from "../utils/operationsApi.js";

let dashboardInventoryItems = [];
let dashboardInventoryRevision = 0;
let dashboardOperationalFacts = null;
let dashboardInitialized = false;

function getGreeting(hour) {
    if (hour < 12) {
        return "Good morning";
    }

    if (hour < 18) {
        return "Good afternoon";
    }

    return "Good evening";
}

function formatCurrentDate(date) {
    return new Intl.DateTimeFormat("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric"
    }).format(date);
}

function formatQuantity(item) {
    return `${item.quantity} ${item.unit}`;
}

function initializeGreeting() {
    const greetingElement =
        document.getElementById("greeting");

    const dateElement =
        document.getElementById("current-date");

    if (!greetingElement || !dateElement) {
        return;
    }

    const now = new Date();

    greetingElement.textContent =
        `${getGreeting(now.getHours())}, Tyler.`;

    dateElement.textContent =
        formatCurrentDate(now);
}

export function getDashboardInventoryEntries(
    items,
    operationalFacts
) {
    return items.map(item => {
        const fact = operationalFacts
            ? getInventoryStockLevelFact(
                operationalFacts,
                item.id
            )
            : null;

        return {
            item,
            fact,
            state: fact?.state ?? "unknown"
        };
    });
}

function inventoryAttentionLabel(state) {
    if (state === "out-of-stock") {
        return "OUT OF STOCK";
    }
    if (state === "low-stock") {
        return "LOW STOCK";
    }
    if (state === "invalid") {
        return "INVALID STOCK DATA";
    }

    return "STATUS UNAVAILABLE";
}

function renderDashboardInventory(items, operationalFacts) {
    const countElement = document.getElementById(
        "dashboard-inventory-count"
    );

    const statusElement = document.getElementById(
        "dashboard-inventory-status"
    );

    const messageElement = document.getElementById(
        "dashboard-inventory-message"
    );

    const listElement = document.getElementById(
        "dashboard-low-stock-list"
    );

    if (
        !countElement ||
        !statusElement ||
        !messageElement ||
        !listElement
    ) {
        return;
    }

    const entries = getDashboardInventoryEntries(
        items,
        operationalFacts
    );
    const attentionEntries = entries
        .filter(entry => entry.state !== "in-stock")
        .sort((a, b) => a.item.name.localeCompare(b.item.name));
    const summary = operationalFacts?.summary.inventory ?? null;

    countElement.textContent = summary?.total ?? "—";
    listElement.innerHTML = "";

    if (!summary) {
        statusElement.textContent = "UNAVAILABLE";
        messageElement.textContent =
            "Inventory status could not be verified.";
        return;
    }

    if (summary.total === 0) {
        statusElement.textContent = "NO INVENTORY";
        messageElement.textContent =
            "No inventory items are currently tracked.";
        return;
    }

    if (
        items.length !== summary.total ||
        entries.some(entry => !entry.fact)
    ) {
        statusElement.textContent = "STATUS UNAVAILABLE";
        messageElement.textContent =
            "Inventory records and operational facts could not be matched.";
        return;
    }

    if (attentionEntries.length === 0) {
        statusElement.textContent = "ALL STOCKED";
        messageElement.textContent =
            `${summary.total} items tracked. No stock alerts.`;
        return;
    }

    statusElement.textContent = [
        summary.outOfStock
            ? `${summary.outOfStock} OUT`
            : "",
        summary.lowStock
            ? `${summary.lowStock} LOW`
            : "",
        summary.invalid
            ? `${summary.invalid} INVALID`
            : ""
    ].filter(Boolean).join(" · ") || "STATUS UNAVAILABLE";

    messageElement.textContent =
        "These items need attention:";

    attentionEntries.slice(0, 4).forEach(({ item, state }) => {
        const alertRow = document.createElement("div");

        alertRow.className = "dashboard-low-stock-item";

        const name = document.createElement("strong");
        name.textContent =
            `${item.name} — ${inventoryAttentionLabel(state)}`;

        const quantity = document.createElement("span");
        quantity.textContent =
            `${formatQuantity(item)} remaining`;

        alertRow.append(name, quantity);
        listElement.appendChild(alertRow);
    });

    if (attentionEntries.length > 4) {
        const remainingMessage =
            document.createElement("p");

        remainingMessage.className =
            "dashboard-low-stock-more";

        remainingMessage.textContent =
            `+${attentionEntries.length - 4} more stock alerts`;

        listElement.appendChild(remainingMessage);
    }
}

export function getDashboardProjectMetrics(operationalFacts) {
    const summary = operationalFacts?.summary.projects;

    if (!summary) {
        return null;
    }

    return {
        active: summary.byStatus.active,
        ready: summary.materialReadiness.ready,
        needsMaterials:
            summary.materialReadiness.needsMaterials,
        notApplicable:
            summary.materialReadiness.notApplicable,
        invalid: summary.materialReadiness.invalid
    };
}

function renderDashboardProjects(operationalFacts) {
    const active = document.getElementById(
        "dashboard-active-projects"
    );
    const ready = document.getElementById(
        "dashboard-ready-projects"
    );
    const needsMaterials = document.getElementById(
        "dashboard-projects-needing-materials"
    );

    if (!active || !ready || !needsMaterials) {
        return;
    }

    const metrics = getDashboardProjectMetrics(
        operationalFacts
    );

    if (!metrics) {
        active.textContent = "—";
        ready.textContent = "—";
        needsMaterials.textContent = "—";
        return;
    }

    active.textContent = metrics.active;
    ready.textContent = metrics.ready;
    needsMaterials.textContent = (
        `${metrics.needsMaterials} / ` +
        `${metrics.notApplicable} / ${metrics.invalid}`
    );
    const label = needsMaterials.parentElement?.querySelector(
        "span"
    );

    if (label) {
        label.textContent = "Needs / N/A / Invalid";
    }
    needsMaterials.title = (
        `${metrics.needsMaterials} need materials; ` +
        `${metrics.notApplicable} not applicable; ` +
        `${metrics.invalid} invalid`
    );
}

async function refreshDashboardOperationalFacts() {
    dashboardOperationalFacts = null;
    renderDashboardInventory(
        dashboardInventoryItems,
        dashboardOperationalFacts
    );
    renderDashboardProjects(dashboardOperationalFacts);

    try {
        dashboardOperationalFacts = await getOperationalFacts();
    } catch (error) {
        console.error(
            "Unable to load backend operational facts for Dashboard:",
            error
        );
    }

    renderDashboardInventory(
        dashboardInventoryItems,
        dashboardOperationalFacts
    );
    renderDashboardProjects(dashboardOperationalFacts);
}

export async function initializeDashboard({
    workEnabled = true,
    inventoryEnabled = true
} = {}) {
    if (dashboardInitialized) {
        return;
    }
    dashboardInitialized = true;

    initializeGreeting();

    if (inventoryEnabled) {
        document.addEventListener(
            "inventory:updated",
            event => {
                dashboardInventoryRevision += 1;
                dashboardInventoryItems = event.detail.items;
                void refreshDashboardOperationalFacts();
            }
        );
    }

    if (workEnabled) {
        document.addEventListener(
            "projects:updated",
            () => {
                void refreshDashboardOperationalFacts();
            }
        );
    }

    if (inventoryEnabled) {
        const startingRevision = dashboardInventoryRevision;

        try {
            const loadedItems = await listInventoryItems();

            if (dashboardInventoryRevision === startingRevision) {
                dashboardInventoryItems = loadedItems;
            }
        } catch (error) {
            console.error(
                "Unable to load backend inventory for Dashboard:",
                error
            );
        }
    }

    if (workEnabled || inventoryEnabled) {
        await refreshDashboardOperationalFacts();
    }
}
