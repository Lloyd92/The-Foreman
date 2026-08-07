import { spaceApiRequest } from "./spaceApi.js";

export function getBackendTasks() {
    return spaceApiRequest("/api/tasks");
}

export function createBackendTask(task) {
    return spaceApiRequest("/api/tasks", {
        method: "POST",
        body: JSON.stringify(task)
    });
}

export function updateBackendTask(taskId, changes) {
    return spaceApiRequest(`/api/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(changes)
    });
}

export function completeBackendTask(taskId) {
    return spaceApiRequest(`/api/tasks/${taskId}/complete`, {
        method: "POST"
    });
}

export function reopenBackendTask(taskId) {
    return spaceApiRequest(`/api/tasks/${taskId}/reopen`, {
        method: "POST"
    });
}

export function deleteBackendTask(taskId) {
    return spaceApiRequest(`/api/tasks/${taskId}`, {
        method: "DELETE"
    });
}

export function migrateBrowserTasks(records) {
    return spaceApiRequest("/api/task-migrations/browser", {
        method: "POST",
        body: JSON.stringify({ records })
    });
}
