import { apiRequest } from "./api.js";

export function listInventoryItems(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            query.set(key, value);
        }
    });

    const suffix = query.size ? `?${query.toString()}` : "";
    return apiRequest(`/api/inventory${suffix}`);
}

export function createInventoryItem(data) {
    return apiRequest("/api/inventory", {
        method: "POST",
        body: JSON.stringify(data)
    });
}

export function updateInventoryItem(itemId, data) {
    return apiRequest(`/api/inventory/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(data)
    });
}

export function deleteInventoryItem(itemId) {
    return apiRequest(`/api/inventory/${itemId}`, {
        method: "DELETE"
    });
}

export function migrateBrowserInventory(records) {
    return apiRequest("/api/inventory-migrations/browser", {
        method: "POST",
        body: JSON.stringify({ records })
    });
}
