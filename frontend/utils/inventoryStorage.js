const INVENTORY_STORAGE_KEY = "foreman-inventory";

export function getInventoryItems() {
    try {
        const storedItems = localStorage.getItem(
            INVENTORY_STORAGE_KEY
        );

        return storedItems ? JSON.parse(storedItems) : [];
    } catch (error) {
        console.error("Unable to read inventory:", error);
        return [];
    }
}

export function saveInventoryItems(items) {
    try {
        localStorage.setItem(
            INVENTORY_STORAGE_KEY,
            JSON.stringify(items)
        );
    } catch (error) {
        console.error("Unable to save inventory:", error);
    }
}