import {
    getInventoryItems,
    saveInventoryItems
} from "../utils/inventoryStorage.js";

function createInventoryItem(formData) {
    return {
        id: crypto.randomUUID(),
        name: formData.get("name").trim(),
        category: formData.get("category"),
        quantity: Number(formData.get("quantity")),
        unit: formData.get("unit").trim(),
        minimum: Number(formData.get("minimum")),
        location: formData.get("location").trim(),
        cost: Number(formData.get("cost") || 0),
        supplier: formData.get("supplier").trim(),
        notes: formData.get("notes").trim(),
        createdAt: new Date().toISOString()
    };
}

function isLowStock(item) {
    return item.quantity <= item.minimum;
}

function formatQuantity(item) {
    return `${item.quantity} ${item.unit}`;
}

function renderInventoryRows(items) {
    const tableBody = document.getElementById(
        "inventory-table-body"
    );

    const emptyState = document.getElementById(
        "inventory-empty-state"
    );

    if (!tableBody || !emptyState) {
        return;
    }

    tableBody.innerHTML = "";

    emptyState.hidden = items.length > 0;

    items.forEach(item => {
        const row = document.createElement("tr");
        const lowStock = isLowStock(item);

        row.innerHTML = `
            <td>
                <strong class="inventory-item-name"></strong>
                <span class="inventory-item-unit-cost"></span>
            </td>

            <td>
                <span class="category-badge"></span>
            </td>

            <td class="inventory-quantity"></td>
            <td class="inventory-minimum"></td>
            <td class="inventory-location"></td>

            <td>
                <span
                    class="stock-badge ${
                        lowStock
                            ? "stock-badge-low"
                            : "stock-badge-available"
                    }"
                >
                    ${lowStock ? "LOW STOCK" : "IN STOCK"}
                </span>
            </td>

            <td class="inventory-actions-cell">
                <button
                    class="table-action-button"
                    type="button"
                    disabled
                    title="Editing arrives in v0.5.3"
                >
                    Edit
                </button>
            </td>
        `;

        row.querySelector(
            ".inventory-item-name"
        ).textContent = item.name;

        row.querySelector(
            ".inventory-item-unit-cost"
        ).textContent =
            item.cost > 0
                ? `$${item.cost.toFixed(2)} each`
                : "";

        row.querySelector(
            ".category-badge"
        ).textContent = item.category;

        row.querySelector(
            ".inventory-quantity"
        ).textContent = formatQuantity(item);

        row.querySelector(
            ".inventory-minimum"
        ).textContent =
            `${item.minimum} ${item.unit}`;

        row.querySelector(
            ".inventory-location"
        ).textContent = item.location;

        tableBody.appendChild(row);
    });
}

function updateInventorySummary(items) {
    const totalCount = document.getElementById(
        "inventory-total-count"
    );

    const lowCount = document.getElementById(
        "inventory-low-count"
    );

    const categoryCount = document.getElementById(
        "inventory-category-count"
    );

    const categories = new Set(
        items.map(item => item.category)
    );

    if (totalCount) {
        totalCount.textContent = items.length;
    }

    if (lowCount) {
        lowCount.textContent =
            items.filter(isLowStock).length;
    }

    if (categoryCount) {
        categoryCount.textContent = categories.size;
    }
}

function updateCategoryFilter(items) {
    const filter = document.getElementById(
        "inventory-category-filter"
    );

    if (!filter) {
        return;
    }

    const previousValue = filter.value;

    const categories = [
        ...new Set(items.map(item => item.category))
    ].sort();

    filter.innerHTML = `
        <option value="all">All Categories</option>
    `;

    categories.forEach(category => {
        const option = document.createElement("option");

        option.value = category;
        option.textContent = category;

        filter.appendChild(option);
    });

    if (
        [...filter.options].some(
            option => option.value === previousValue
        )
    ) {
        filter.value = previousValue;
    }
}

function renderInventory() {
    const items = getInventoryItems();

    renderInventoryRows(items);
    updateInventorySummary(items);
    updateCategoryFilter(items);
}

function openInventoryDialog() {
    const backdrop = document.getElementById(
        "inventory-dialog-backdrop"
    );

    const nameInput = document.getElementById(
        "inventory-name"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    window.setTimeout(() => {
        nameInput?.focus();
    }, 0);
}

function closeInventoryDialog() {
    const backdrop = document.getElementById(
        "inventory-dialog-backdrop"
    );

    const form = document.getElementById(
        "inventory-form"
    );

    const errorMessage = document.getElementById(
        "inventory-form-error"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    document.body.classList.remove("dialog-open");

    form?.reset();

    if (errorMessage) {
        errorMessage.textContent = "";
    }
}

function handleInventorySubmit(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);

    const name = formData.get("name").trim();
    const category = formData.get("category");
    const location = formData.get("location").trim();
    const unit = formData.get("unit").trim();

    const errorMessage = document.getElementById(
        "inventory-form-error"
    );

    if (!name || !category || !location || !unit) {
        if (errorMessage) {
            errorMessage.textContent =
                "Complete all required fields.";
        }

        return;
    }

    const items = getInventoryItems();
    const newItem = createInventoryItem(formData);

    items.push(newItem);
    saveInventoryItems(items);

    closeInventoryDialog();
    renderInventory();
}

function handleDialogBackdropClick(event) {
    if (event.target.id === "inventory-dialog-backdrop") {
        closeInventoryDialog();
    }
}

function handleEscapeKey(event) {
    if (event.key === "Escape") {
        closeInventoryDialog();
    }
}

export function initializeInventoryPage() {
    const addButton = document.getElementById(
        "add-inventory-item"
    );

    const emptyStateButton = document.getElementById(
        "empty-state-add-item"
    );

    const closeButton = document.getElementById(
        "close-inventory-dialog"
    );

    const cancelButton = document.getElementById(
        "cancel-inventory-item"
    );

    const form = document.getElementById(
        "inventory-form"
    );

    const backdrop = document.getElementById(
        "inventory-dialog-backdrop"
    );

    addButton?.addEventListener(
        "click",
        openInventoryDialog
    );

    emptyStateButton?.addEventListener(
        "click",
        openInventoryDialog
    );

    closeButton?.addEventListener(
        "click",
        closeInventoryDialog
    );

    cancelButton?.addEventListener(
        "click",
        closeInventoryDialog
    );

    form?.addEventListener(
        "submit",
        handleInventorySubmit
    );

    backdrop?.addEventListener(
        "click",
        handleDialogBackdropClick
    );

    document.addEventListener(
        "keydown",
        handleEscapeKey
    );

    renderInventory();
}