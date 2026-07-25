function showComingSoonMessage() {
    const message = document.getElementById(
        "inventory-page-message"
    );

    if (!message) {
        return;
    }

    message.textContent =
        "The Add Item form will be activated in v0.5.2.";

    window.clearTimeout(showComingSoonMessage.timeoutId);

    showComingSoonMessage.timeoutId = window.setTimeout(() => {
        message.textContent = "";
    }, 4000);
}

export function initializeInventoryPage() {
    const addButton = document.getElementById(
        "add-inventory-item"
    );

    const emptyStateButton = document.getElementById(
        "empty-state-add-item"
    );

    addButton?.addEventListener(
        "click",
        showComingSoonMessage
    );

    emptyStateButton?.addEventListener(
        "click",
        showComingSoonMessage
    );
}