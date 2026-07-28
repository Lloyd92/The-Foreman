import {
    getInventoryItems
} from "../utils/inventoryStorage.js";
import {
    listInventoryItems
} from "../utils/inventoryApi.js";

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

export async function initializeDashboard() {
    initializeGreeting();

    try {
        renderDashboardInventory(await listInventoryItems());
    } catch (error) {
        console.error(
            "Unable to load backend inventory for Dashboard:",
            error
        );
        renderDashboardInventory(getInventoryItems());
    }

    document.addEventListener(
        "inventory:updated",
        event => {
            renderDashboardInventory(
                event.detail.items
            );
        }
    );
}
