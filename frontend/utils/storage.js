const STORAGE_KEY = "foreman-tasks";

export function getBrowserTasks() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
        return [];
    }
}
