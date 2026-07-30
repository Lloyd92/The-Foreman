const INVENTORY_STORAGE_KEY = "foreman-inventory";

export function getBrowserInventoryRecords() {
    try {
        const storedItems = localStorage.getItem(
            INVENTORY_STORAGE_KEY
        );

        const parsedItems = storedItems
            ? JSON.parse(storedItems)
            : [];

        if (!Array.isArray(parsedItems)) {
            console.error(
                "Browser-local inventory is malformed and was retained."
            );
            return [];
        }

        return parsedItems;
    } catch (error) {
        console.error("Unable to read inventory:", error);
        return [];
    }
}
