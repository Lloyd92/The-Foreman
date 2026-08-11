import {
    createInventoryItem,
    deleteInventoryItem,
    listInventoryItems,
    migrateBrowserInventory,
    updateInventoryItem
} from "../utils/inventoryApi.js";
import {
    getBrowserInventoryRecords
} from "../utils/inventoryStorage.js";
import {
    getInventoryStockLevelFact,
    getOperationalFacts
} from "../utils/operationsApi.js";
import {
    inventoryMigrationReport
} from "../utils/migrationReporting.js";

let editingItemId = null;
let inventoryItems = [];
let inventoryOperationalFacts = null;
let persistenceMode = "initializing";
let inventoryInitialized = false;

function formPayload(formData) {
    return {
        name: formData.get("name").trim(),
        category: formData.get("category"),
        quantity: Number(formData.get("quantity")),
        unit: formData.get("unit").trim(),
        minimum: Number(formData.get("minimum")),
        location: formData.get("location").trim(),
        cost: Number(formData.get("cost") || 0),
        supplier: formData.get("supplier").trim(),
        notes: formData.get("notes").trim()
    };
}

export function getInventoryOperationalState(
    operationalFacts,
    itemId
) {
    return operationalFacts
        ? getInventoryStockLevelFact(
            operationalFacts,
            itemId
        )?.state ?? "unknown"
        : "unknown";
}

export function getInventoryStockPresentation(state) {
    if (state === "in-stock") {
        return {
            label: "IN STOCK",
            className: "stock-badge-available",
            attention: false
        };
    }
    if (state === "low-stock") {
        return {
            label: "LOW STOCK",
            className: "stock-badge-low",
            attention: true
        };
    }
    if (state === "out-of-stock") {
        return {
            label: "OUT OF STOCK",
            className: "stock-badge-low",
            attention: true
        };
    }
    if (state === "invalid") {
        return {
            label: "INVALID STOCK DATA",
            className: "stock-badge-low",
            attention: true
        };
    }

    return {
        label: "STATUS UNAVAILABLE",
        className: "stock-badge-low",
        attention: true
    };
}

function formatQuantity(item) {
    return `${item.quantity} ${item.unit}`;
}

function getItemById(itemId) {
    return inventoryItems.find(item => item.id === itemId);
}

function showPageMessage(message, isError = false) {
    const element = document.getElementById("inventory-page-message");

    if (element) {
        element.textContent = message;
        element.classList.toggle("error", isError);
    }
}

async function removeInventoryItem(itemId) {
    const item = getItemById(itemId);

    if (!item || !window.confirm(`Delete "${item.name}" from inventory?`)) {
        return;
    }

    try {
        if (persistenceMode !== "backend") {
            throw new Error(
                "HardHead Inventory is unavailable"
            );
        }

        await deleteInventoryItem(itemId);
        inventoryItems = inventoryItems.filter(current => current.id !== itemId);
        inventoryOperationalFacts = null;

        try {
            inventoryOperationalFacts = await getOperationalFacts();
        } catch (factsError) {
            console.error(
                "Unable to refresh operational facts after deletion:",
                factsError
            );
        }
        renderInventory();
    } catch (error) {
        console.error("Unable to delete inventory item:", error);
        showPageMessage(
            "The item was not deleted. Backend data and browser-local data were unchanged.",
            true
        );
    }
}

function populateInventoryForm(item) {
    document.getElementById("inventory-name").value = item.name;
    document.getElementById("inventory-category").value = item.category;
    document.getElementById("inventory-location").value = item.location;
    document.getElementById("inventory-quantity").value = item.quantity;
    document.getElementById("inventory-unit").value = item.unit;
    document.getElementById("inventory-minimum").value = item.minimum;
    document.getElementById("inventory-cost").value = item.cost || "";
    document.getElementById("inventory-supplier").value = item.supplier || "";
    document.getElementById("inventory-notes").value = item.notes || "";
}

function openInventoryDialog(isNewItem = true) {
    const backdrop = document.getElementById("inventory-dialog-backdrop");
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
    window.setTimeout(() => nameInput?.focus(), 0);
}

function openEditInventoryDialog(itemId) {
    const item = getItemById(itemId);

    if (!item) {
        return;
    }

    editingItemId = itemId;
    const title = document.getElementById("inventory-dialog-title");

    if (title) {
        title.textContent = "Edit Inventory Item";
    }

    populateInventoryForm(item);
    openInventoryDialog(false);
}

function closeInventoryDialog() {
    const backdrop = document.getElementById("inventory-dialog-backdrop");

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    document.body.classList.remove("dialog-open");
    document.getElementById("inventory-form")?.reset();
    editingItemId = null;

    const error = document.getElementById("inventory-form-error");
    const title = document.getElementById("inventory-dialog-title");

    if (error) {
        error.textContent = "";
    }

    if (title) {
        title.textContent = "Add Inventory Item";
    }
}

function renderInventoryRows(items) {
    const tableBody = document.getElementById("inventory-table-body");
    const emptyState = document.getElementById("inventory-empty-state");

    if (!tableBody || !emptyState) {
        return;
    }

    tableBody.innerHTML = "";
    emptyState.hidden = items.length > 0;

    items.forEach(item => {
        const row = document.createElement("tr");
        const state = getInventoryOperationalState(
            inventoryOperationalFacts,
            item.id
        );
        const stock = getInventoryStockPresentation(state);

        row.innerHTML = `
            <td>
                <strong class="inventory-item-name"></strong>
                <span class="inventory-item-unit-cost"></span>
            </td>
            <td><span class="category-badge"></span></td>
            <td class="inventory-quantity"></td>
            <td class="inventory-minimum"></td>
            <td class="inventory-location"></td>
            <td>
                <span class="stock-badge ${stock.className}"></span>
            </td>
            <td class="inventory-actions-cell">
                <div class="inventory-row-actions">
                    <button class="table-action-button" type="button"
                        data-action="edit" data-id="${item.id}">Edit</button>
                    <button class="table-action-button delete-inventory-button"
                        type="button" data-action="delete"
                        data-id="${item.id}">Delete</button>
                </div>
            </td>
        `;
        row.querySelector(".inventory-item-name").textContent = item.name;
        row.querySelector(".inventory-item-unit-cost").textContent =
            item.cost > 0 ? `$${item.cost.toFixed(2)} each` : "";
        row.querySelector(".category-badge").textContent = item.category;
        row.querySelector(".inventory-quantity").textContent =
            formatQuantity(item);
        row.querySelector(".inventory-minimum").textContent =
            `${item.minimum} ${item.unit}`;
        row.querySelector(".inventory-location").textContent = item.location;
        row.querySelector(".stock-badge").textContent = stock.label;
        tableBody.appendChild(row);
    });
}

function updateInventorySummary(items, operationalFacts) {
    const categories = new Set(items.map(item => item.category));
    const total = document.getElementById("inventory-total-count");
    const low = document.getElementById("inventory-low-count");
    const category = document.getElementById("inventory-category-count");
    const summary = operationalFacts?.summary.inventory;
    const attentionCount = items.filter(item => (
        getInventoryStockPresentation(
            getInventoryOperationalState(
                operationalFacts,
                item.id
            )
        ).attention
    )).length;

    if (total) total.textContent = summary?.total ?? "—";
    if (low) {
        low.textContent = operationalFacts
            ? attentionCount
            : "—";
        const label = low.parentElement?.querySelector(
            ".summary-label"
        );
        if (label) {
            label.textContent = "Stock Alerts";
        }
    }
    if (category) category.textContent = categories.size;
}

function updateCategoryFilter(items) {
    const filter = document.getElementById("inventory-category-filter");

    if (!filter) {
        return;
    }

    const previous = filter.value;
    const categories = [...new Set(items.map(item => item.category))].sort();
    filter.innerHTML = '<option value="all">All Categories</option>';

    categories.forEach(category => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        filter.appendChild(option);
    });

    filter.value = [...filter.options].some(
        option => option.value === previous
    ) ? previous : "all";
}

function filteredInventory(items) {
    const search = document.getElementById("inventory-search")
        ?.value.trim().toLowerCase() || "";
    const category = document.getElementById("inventory-category-filter")
        ?.value || "all";
    const stock = document.getElementById("inventory-stock-filter")
        ?.value || "all";

    return items.filter(item => {
        const matchesSearch = !search || [
            item.name,
            item.category,
            item.location,
            item.supplier || ""
        ].some(value => value.toLowerCase().includes(search));
        const matchesCategory =
            category === "all" || item.category === category;
        const stockPresentation = getInventoryStockPresentation(
            getInventoryOperationalState(
                inventoryOperationalFacts,
                item.id
            )
        );
        const matchesStock =
            stock === "all" ||
            (stock === "low" && stockPresentation.attention) ||
            (
                stock === "available" &&
                !stockPresentation.attention
            );

        return matchesSearch && matchesCategory && matchesStock;
    });
}

function sortedInventory(items) {
    const value = document.getElementById("inventory-sort")
        ?.value || "name-asc";
    const sorted = [...items];

    if (value === "name-desc") {
        return sorted.sort((a, b) => b.name.localeCompare(a.name));
    }
    if (value === "quantity-asc") {
        return sorted.sort((a, b) => a.quantity - b.quantity);
    }
    if (value === "quantity-desc") {
        return sorted.sort((a, b) => b.quantity - a.quantity);
    }
    if (value === "category-asc") {
        return sorted.sort(
            (a, b) => a.category.localeCompare(b.category) ||
                a.name.localeCompare(b.name)
        );
    }
    if (value === "stock") {
        const stockOrder = {
            "out-of-stock": 0,
            "low-stock": 1,
            invalid: 2,
            unknown: 3,
            "in-stock": 4
        };
        return sorted.sort(
            (a, b) => (
                stockOrder[getInventoryOperationalState(
                    inventoryOperationalFacts,
                    a.id
                )] -
                stockOrder[getInventoryOperationalState(
                    inventoryOperationalFacts,
                    b.id
                )]
            ) ||
                a.name.localeCompare(b.name)
        );
    }
    return sorted.sort((a, b) => a.name.localeCompare(b.name));
}

function notifyInventoryUpdated(items) {
    document.dispatchEvent(
        new CustomEvent(
            "inventory:updated",
            {
                detail: {
                    items: [...items],
                    operationalFacts: inventoryOperationalFacts
                }
            }
        )
    );
}

function renderInventory() {
    renderInventoryRows(sortedInventory(filteredInventory(inventoryItems)));
    updateInventorySummary(
        inventoryItems,
        inventoryOperationalFacts
    );
    updateCategoryFilter(inventoryItems);
    notifyInventoryUpdated(inventoryItems);
}

async function handleInventorySubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = formPayload(new FormData(form));
    const errorMessage = document.getElementById("inventory-form-error");

    if (!data.name || !data.category || !data.location || !data.unit) {
        if (errorMessage) {
            errorMessage.textContent = "Complete all required fields.";
        }
        return;
    }

    try {
        if (persistenceMode !== "backend") {
            throw new Error(
                "HardHead Inventory is unavailable"
            );
        }

        const saved = editingItemId
            ? await updateInventoryItem(editingItemId, data)
            : await createInventoryItem(data);
        inventoryItems = editingItemId
            ? inventoryItems.map(item => item.id === saved.id ? saved : item)
            : [...inventoryItems, saved];
        inventoryOperationalFacts = null;

        try {
            inventoryOperationalFacts = await getOperationalFacts();
        } catch (factsError) {
            console.error(
                "Unable to refresh operational facts after save:",
                factsError
            );
        }

        closeInventoryDialog();
        renderInventory();
    } catch (error) {
        console.error("Unable to save inventory item:", error);

        if (errorMessage) {
            errorMessage.textContent =
                `${error.message}. No browser-local fallback write was made.`;
        }
    }
}

export async function migrateLegacyInventory() {
    const browserRecords = getBrowserInventoryRecords();
    const migration = await migrateBrowserInventory(browserRecords);

    return {
        browserRecordCount: browserRecords.length,
        migration
    };
}

async function initializePersistence(inventoryMigration) {
    try {
        const {
            browserRecordCount = 0,
            migration = null
        } = await inventoryMigration;
        [
            inventoryItems,
            inventoryOperationalFacts
        ] = await Promise.all([
            listInventoryItems(),
            getOperationalFacts()
        ]);
        persistenceMode = "backend";

        const report = inventoryMigrationReport({
            browserRecordCount,
            migration
        });

        if (report) {
            showPageMessage(
                report.message,
                report.severity === "error"
            );
        }

        renderInventory();
        return {
            status: "complete",
            migration,
            items: inventoryItems,
            operationalFacts: inventoryOperationalFacts
        };
    } catch (error) {
        console.error("Inventory backend unavailable:", error);
        persistenceMode = "unavailable";
        showPageMessage(
            "HardHead Inventory is unavailable. Browser-local records " +
            "were not loaded as operational data.",
            true
        );
        return {
            status: "unavailable",
            error
        };
    }
}

function handleInventoryTableAction(event) {
    const button = event.target.closest("[data-action][data-id]");

    if (button?.dataset.action === "edit") {
        openEditInventoryDialog(button.dataset.id);
    } else if (button?.dataset.action === "delete") {
        void removeInventoryItem(button.dataset.id);
    }
}

export function initializeInventoryPage(
    inventoryMigration = Promise.resolve({
        browserRecordCount: 0,
        migration: null
    })
) {
    if (inventoryInitialized) {
        return Promise.resolve({
            status: "already-initialized",
            items: inventoryItems,
            operationalFacts: inventoryOperationalFacts
        });
    }
    inventoryInitialized = true;

    document.getElementById("add-inventory-item")?.addEventListener(
        "click",
        () => openInventoryDialog(true)
    );
    document.getElementById("empty-state-add-item")?.addEventListener(
        "click",
        () => openInventoryDialog(true)
    );
    document.getElementById("close-inventory-dialog")?.addEventListener(
        "click",
        closeInventoryDialog
    );
    document.getElementById("cancel-inventory-item")?.addEventListener(
        "click",
        closeInventoryDialog
    );
    document.getElementById("inventory-form")?.addEventListener(
        "submit",
        event => void handleInventorySubmit(event)
    );
    document.getElementById("inventory-dialog-backdrop")?.addEventListener(
        "click",
        event => {
            if (event.target.id === "inventory-dialog-backdrop") {
                closeInventoryDialog();
            }
        }
    );
    document.getElementById("inventory-table-body")?.addEventListener(
        "click",
        handleInventoryTableAction
    );

    ["inventory-search", "inventory-category-filter",
        "inventory-stock-filter", "inventory-sort"].forEach(id => {
        const eventName = id === "inventory-search" ? "input" : "change";
        document.getElementById(id)?.addEventListener(eventName, renderInventory);
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeInventoryDialog();
        }
    });

    return initializePersistence(inventoryMigration);
}
