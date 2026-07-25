import {
    getInventoryItems,
    saveInventoryItems
} from "../utils/inventoryStorage.js";

let editingItemId = null;

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

function getItemById(itemId) {
    return getInventoryItems().find(item => item.id === itemId);
}

function deleteInventoryItem(itemId) {
    const item = getItemById(itemId);

    if (!item) {
        return;
    }

    const confirmed = window.confirm(
        `Delete "${item.name}" from inventory?`
    );

    if (!confirmed) {
        return;
    }

    const updatedItems = getInventoryItems().filter(
        inventoryItem => inventoryItem.id !== itemId
    );

    saveInventoryItems(updatedItems);
    renderInventory();
}

function populateInventoryForm(item) {
    document.getElementById("inventory-name").value = item.name;
    document.getElementById("inventory-category").value = item.category;
    document.getElementById("inventory-location").value = item.location;
    document.getElementById("inventory-quantity").value = item.quantity;
    document.getElementById("inventory-unit").value = item.unit;
    document.getElementById("inventory-minimum").value = item.minimum;
    document.getElementById("inventory-cost").value = item.cost || "";
    document.getElementById("inventory-supplier").value =
        item.supplier || "";
    document.getElementById("inventory-notes").value =
        item.notes || "";
}

function openInventoryDialog(isNewItem = true) {
    const backdrop = document.getElementById(
        "inventory-dialog-backdrop"
    );

    const form = document.getElementById("inventory-form");
    const title = document.getElementById("inventory-dialog-title");
    const nameInput = document.getElementById("inventory-name");

    if (!backdrop) {
        return;
    }

    if (isNewItem) {
        editingItemId = null;
        form?.reset();

        if (title) {
            title.textContent = "Add Inventory Item";
        }
    }

    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    window.setTimeout(() => {
        nameInput?.focus();
    }, 0);
}

function openEditInventoryDialog(itemId) {
    const item = getItemById(itemId);

    if (!item) {
        return;
    }

    editingItemId = itemId;

    const title = document.getElementById(
        "inventory-dialog-title"
    );

    if (title) {
        title.textContent = "Edit Inventory Item";
    }

    populateInventoryForm(item);
    openInventoryDialog(false);
}

function closeInventoryDialog() {
    const backdrop = document.getElementById(
        "inventory-dialog-backdrop"
    );

    const form = document.getElementById("inventory-form");

    const errorMessage = document.getElementById(
        "inventory-form-error"
    );

    const title = document.getElementById(
        "inventory-dialog-title"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    document.body.classList.remove("dialog-open");

    form?.reset();
    editingItemId = null;

    if (errorMessage) {
        errorMessage.textContent = "";
    }

    if (title) {
        title.textContent = "Add Inventory Item";
    }
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
                <div class="inventory-row-actions">
                    <button
                        class="table-action-button"
                        type="button"
                        data-action="edit"
                        data-id="${item.id}"
                    >
                        Edit
                    </button>

                    <button
                        class="table-action-button delete-inventory-button"
                        type="button"
                        data-action="delete"
                        data-id="${item.id}"
                    >
                        Delete
                    </button>
                </div>
            </td>
        `;

        row.querySelector(".inventory-item-name").textContent =
            item.name;

        row.querySelector(".inventory-item-unit-cost").textContent =
            item.cost > 0
                ? `$${item.cost.toFixed(2)} each`
                : "";

        row.querySelector(".category-badge").textContent =
            item.category;

        row.querySelector(".inventory-quantity").textContent =
            formatQuantity(item);

        row.querySelector(".inventory-minimum").textContent =
            `${item.minimum} ${item.unit}`;

        row.querySelector(".inventory-location").textContent =
            item.location;

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

    const stillExists = [...filter.options].some(
        option => option.value === previousValue
    );

    filter.value = stillExists ? previousValue : "all";
}

function getFilteredInventoryItems(items) {
    const searchValue = document
        .getElementById("inventory-search")
        ?.value.trim()
        .toLowerCase() || "";

    const categoryValue = document
        .getElementById("inventory-category-filter")
        ?.value || "all";

    const stockValue = document
        .getElementById("inventory-stock-filter")
        ?.value || "all";

    return items.filter(item => {
        const supplier =
            (item.supplier || "").toLowerCase();

        const matchesSearch =
            !searchValue ||
            item.name.toLowerCase().includes(searchValue) ||
            item.category.toLowerCase().includes(searchValue) ||
            item.location.toLowerCase().includes(searchValue) ||
            supplier.includes(searchValue);

        const matchesCategory =
            categoryValue === "all" ||
            item.category === categoryValue;

        const matchesStock =
            stockValue === "all" ||
            (stockValue === "low" && isLowStock(item)) ||
            (stockValue === "available" && !isLowStock(item));

        return (
            matchesSearch &&
            matchesCategory &&
            matchesStock
        );
    });
}

function sortInventoryItems(items) {
    const sortValue = document
        .getElementById("inventory-sort")
        ?.value || "name-asc";

    const sortedItems = [...items];

    switch (sortValue) {
        case "name-desc":
            return sortedItems.sort((a, b) =>
                b.name.localeCompare(a.name)
            );

        case "quantity-asc":
            return sortedItems.sort(
                (a, b) => a.quantity - b.quantity
            );

        case "quantity-desc":
            return sortedItems.sort(
                (a, b) => b.quantity - a.quantity
            );

        case "category-asc":
            return sortedItems.sort((a, b) => {
                const categoryComparison =
                    a.category.localeCompare(b.category);

                return categoryComparison !== 0
                    ? categoryComparison
                    : a.name.localeCompare(b.name);
            });

        case "stock":
            return sortedItems.sort((a, b) => {
                const aLow = isLowStock(a);
                const bLow = isLowStock(b);

                if (aLow !== bLow) {
                    return Number(bLow) - Number(aLow);
                }

                return a.name.localeCompare(b.name);
            });

        case "name-asc":
        default:
            return sortedItems.sort((a, b) =>
                a.name.localeCompare(b.name)
            );
    }
}

function notifyInventoryUpdated(items) {
    document.dispatchEvent(
        new CustomEvent("inventory:updated", {
            detail: { items }
        })
    );
}

function renderInventory() {
    const items = getInventoryItems();
    const filteredItems = getFilteredInventoryItems(items);
    const sortedItems = sortInventoryItems(filteredItems);

    renderInventoryRows(sortedItems);
    updateInventorySummary(items);
    updateCategoryFilter(items);
    notifyInventoryUpdated(items);
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

    let items = getInventoryItems();

    if (editingItemId) {
        const updatedItem = createInventoryItem(formData);

        items = items.map(item =>
            item.id === editingItemId
                ? {
                    ...updatedItem,
                    id: item.id,
                    createdAt: item.createdAt,
                    updatedAt: new Date().toISOString()
                }
                : item
        );
    } else {
        items.push(createInventoryItem(formData));
    }

    saveInventoryItems(items);
    closeInventoryDialog();
    renderInventory();
}

function handleInventoryTableAction(event) {
    const button = event.target.closest(
        "[data-action][data-id]"
    );

    if (!button) {
        return;
    }

    const action = button.dataset.action;
    const itemId = button.dataset.id;

    if (action === "edit") {
        openEditInventoryDialog(itemId);
    }

    if (action === "delete") {
        deleteInventoryItem(itemId);
    }
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

    const form = document.getElementById("inventory-form");

    const backdrop = document.getElementById(
        "inventory-dialog-backdrop"
    );

    const tableBody = document.getElementById(
        "inventory-table-body"
    );

    const searchInput = document.getElementById(
        "inventory-search"
    );

    const categoryFilter = document.getElementById(
        "inventory-category-filter"
    );

    const stockFilter = document.getElementById(
        "inventory-stock-filter"
    );

    const sortSelect = document.getElementById(
        "inventory-sort"
    );

    addButton?.addEventListener(
        "click",
        () => openInventoryDialog(true)
    );

    emptyStateButton?.addEventListener(
        "click",
        () => openInventoryDialog(true)
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

    tableBody?.addEventListener(
        "click",
        handleInventoryTableAction
    );

    searchInput?.addEventListener(
        "input",
        renderInventory
    );

    categoryFilter?.addEventListener(
        "change",
        renderInventory
    );

    stockFilter?.addEventListener(
        "change",
        renderInventory
    );

    sortSelect?.addEventListener(
        "change",
        renderInventory
    );

    document.addEventListener(
        "keydown",
        handleEscapeKey
    );

    renderInventory();
}