import { spaceApiRequest } from "./spaceApi.js";

export function listInventoryItems(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            query.set(key, value);
        }
    });

    const suffix = query.size ? `?${query.toString()}` : "";
    return spaceApiRequest(`/api/inventory${suffix}`);
}

export function createInventoryItem(data) {
    return spaceApiRequest("/api/inventory", {
        method: "POST",
        body: JSON.stringify(data)
    });
}

export function updateInventoryItem(itemId, data) {
    return spaceApiRequest(`/api/inventory/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(data)
    });
}

export function deleteInventoryItem(itemId) {
    return spaceApiRequest(`/api/inventory/${itemId}`, {
        method: "DELETE"
    });
}

export function migrateBrowserInventory(records) {
    return spaceApiRequest("/api/inventory-migrations/browser", {
        method: "POST",
        body: JSON.stringify({ records })
    });
}
