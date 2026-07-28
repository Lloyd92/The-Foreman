import {
    getInventoryItems
} from "../utils/inventoryStorage.js";
import {
    listInventoryItems
} from "../utils/inventoryApi.js";
import {
    getProjects
} from "../utils/projectStorage.js";
import {
    evaluateProjectReadiness,
    PROJECT_READINESS
} from "../utils/projectReadiness.js";

let dashboardInventoryItems = [];
let dashboardInventoryRevision = 0;

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

function isLowStock(item) {
    return item.isLow ?? item.quantity <= item.minimum;
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

function renderDashboardInventory(items) {
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

    const lowStockItems = items
        .filter(isLowStock)
        .sort((a, b) => a.name.localeCompare(b.name));

    countElement.textContent = items.length;
    listElement.innerHTML = "";

    if (items.length === 0) {
        statusElement.textContent = "READY";
        messageElement.textContent =
            "No inventory items are currently tracked.";
        return;
    }

    if (lowStockItems.length === 0) {
        statusElement.textContent = "ALL STOCKED";
        messageElement.textContent =
            `${items.length} items tracked. No purchasing alerts.`;
        return;
    }

    statusElement.textContent =
        `${lowStockItems.length} LOW`;

    messageElement.textContent =
        "These items need attention:";

    lowStockItems.slice(0, 4).forEach(item => {
        const alertRow = document.createElement("div");

        alertRow.className = "dashboard-low-stock-item";

        const name = document.createElement("strong");
        name.textContent = item.name;

        const quantity = document.createElement("span");
        quantity.textContent =
            `${formatQuantity(item)} remaining`;

        alertRow.append(name, quantity);
        listElement.appendChild(alertRow);
    });

    if (lowStockItems.length > 4) {
        const remainingMessage =
            document.createElement("p");

        remainingMessage.className =
            "dashboard-low-stock-more";

        remainingMessage.textContent =
            `+${lowStockItems.length - 4} more low-stock items`;

        listElement.appendChild(remainingMessage);
    }
}

function renderDashboardProjects(projects, inventoryItems) {
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

    const readinessProjects = projects.filter(
        project =>
            project.status === "planning" ||
            project.status === "active"
    );

    active.textContent = projects.filter(
        project => project.status === "active"
    ).length;
    ready.textContent = readinessProjects.filter(
        project =>
            evaluateProjectReadiness(project, inventoryItems)
                .status === PROJECT_READINESS.ready
    ).length;
    needsMaterials.textContent = readinessProjects.filter(
        project =>
            evaluateProjectReadiness(project, inventoryItems)
                .status === PROJECT_READINESS.needsMaterials
    ).length;
}

export async function initializeDashboard() {
    initializeGreeting();

    document.addEventListener(
        "inventory:updated",
        event => {
            dashboardInventoryRevision += 1;
            dashboardInventoryItems = event.detail.items;
            renderDashboardInventory(dashboardInventoryItems);
            renderDashboardProjects(
                getProjects(),
                dashboardInventoryItems
            );
        }
    );
    document.addEventListener(
        "projects:updated",
        event => {
            renderDashboardProjects(
                event.detail.projects,
                dashboardInventoryItems
            );
        }
    );

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

        if (dashboardInventoryRevision === startingRevision) {
            dashboardInventoryItems = getInventoryItems();
        }
    }

    renderDashboardInventory(dashboardInventoryItems);
    renderDashboardProjects(
        getProjects(),
        dashboardInventoryItems
    );

}
