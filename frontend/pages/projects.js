function showComingSoonMessage() {
    const message = document.getElementById(
        "projects-page-message"
    );

    if (!message) {
        return;
    }

    message.textContent =
        "Project creation will be activated in v0.6.2.";

    window.clearTimeout(showComingSoonMessage.timeoutId);

    showComingSoonMessage.timeoutId = window.setTimeout(() => {
        message.textContent = "";
    }, 4000);
}

export function initializeProjectsPage() {
    const addButton = document.getElementById(
        "add-project"
    );

    const emptyStateButton = document.getElementById(
        "empty-state-add-project"
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