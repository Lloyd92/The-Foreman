import { apiRequest } from "./api.js";

export function getBackendTasks() {
    return apiRequest("/api/tasks");
}

export function createBackendTask(task) {
    return apiRequest("/api/tasks", {
        method: "POST",
        body: JSON.stringify(task)
    });
}

export function updateBackendTask(taskId, changes) {
    return apiRequest(`/api/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(changes)
    });
}

export function completeBackendTask(taskId) {
    return apiRequest(`/api/tasks/${taskId}/complete`, {
        method: "POST"
    });
}

export function reopenBackendTask(taskId) {
    return apiRequest(`/api/tasks/${taskId}/reopen`, {
        method: "POST"
    });
}

export function deleteBackendTask(taskId) {
    return apiRequest(`/api/tasks/${taskId}`, {
        method: "DELETE"
    });
}

export function migrateBrowserTasks(records) {
    return apiRequest("/api/task-migrations/browser", {
        method: "POST",
        body: JSON.stringify({ records })
    });
}
