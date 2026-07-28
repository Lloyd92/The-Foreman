import { apiRequest } from "./api.js";


export function listProjects(includeArchived = false) {
    const query = includeArchived ? "?includeArchived=true" : "";
    return apiRequest(`/api/projects${query}`);
}


export function getProject(projectId) {
    return apiRequest(`/api/projects/${encodeURIComponent(projectId)}`);
}


export function createProject(project) {
    return apiRequest("/api/projects", {
        method: "POST",
        body: JSON.stringify(project)
    });
}


export function updateProject(projectId, changes) {
    return apiRequest(
        `/api/projects/${encodeURIComponent(projectId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(changes)
        }
    );
}


export function deleteProject(projectId) {
    return apiRequest(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "DELETE"
    });
}

export function addProjectMaterial(projectId, requirement) {
    return apiRequest(
        `/api/projects/${encodeURIComponent(projectId)}/materials`,
        {
            method: "POST",
            body: JSON.stringify(requirement)
        }
    );
}


export function updateProjectMaterial(
    projectId,
    inventoryItemId,
    changes
) {
    return apiRequest(
        `/api/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(inventoryItemId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(changes)
        }
    );
}


export function deleteProjectMaterial(projectId, inventoryItemId) {
    return apiRequest(
        `/api/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(inventoryItemId)}`,
        { method: "DELETE" }
    );
}


export function migrateBrowserProject(project) {
    return apiRequest("/api/project-migrations/browser", {
        method: "POST",
        body: JSON.stringify(project)
    });
}
