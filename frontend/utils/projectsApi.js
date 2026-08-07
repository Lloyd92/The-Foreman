import { spaceApiRequest } from "./spaceApi.js";


export function listProjects(includeArchived = false) {
    const query = includeArchived ? "?includeArchived=true" : "";
    return spaceApiRequest(`/api/projects${query}`);
}


export function getProject(projectId) {
    return spaceApiRequest(`/api/projects/${encodeURIComponent(projectId)}`);
}


export function createProject(project) {
    return spaceApiRequest("/api/projects", {
        method: "POST",
        body: JSON.stringify(project)
    });
}


export function updateProject(projectId, changes) {
    return spaceApiRequest(
        `/api/projects/${encodeURIComponent(projectId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(changes)
        }
    );
}


export function deleteProject(projectId) {
    return spaceApiRequest(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "DELETE"
    });
}

export function addProjectMaterial(projectId, requirement) {
    return spaceApiRequest(
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
    return spaceApiRequest(
        `/api/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(inventoryItemId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(changes)
        }
    );
}


export function deleteProjectMaterial(projectId, inventoryItemId) {
    return spaceApiRequest(
        `/api/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(inventoryItemId)}`,
        { method: "DELETE" }
    );
}


export function migrateBrowserProject(project) {
    return spaceApiRequest("/api/project-migrations/browser", {
        method: "POST",
        body: JSON.stringify(project)
    });
}
