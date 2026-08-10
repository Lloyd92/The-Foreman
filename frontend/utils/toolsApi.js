import { spaceApiRequest } from "./spaceApi.js";


function querySuffix(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
        if (
            value !== undefined &&
            value !== null &&
            value !== ""
        ) {
            query.set(key, value);
        }
    });

    return query.size ? `?${query.toString()}` : "";
}


export function listTools(params = {}) {
    return spaceApiRequest(
        `/api/tools${querySuffix(params)}`
    );
}


export function createTool(data) {
    return spaceApiRequest("/api/tools", {
        method: "POST",
        body: JSON.stringify(data)
    });
}


export function updateTool(toolId, data) {
    return spaceApiRequest(
        `/api/tools/${encodeURIComponent(toolId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(data)
        }
    );
}


export function deleteTool(toolId) {
    return spaceApiRequest(
        `/api/tools/${encodeURIComponent(toolId)}`,
        { method: "DELETE" }
    );
}


export function listToolMaintenance(toolId) {
    return spaceApiRequest(
        `/api/tools/${encodeURIComponent(toolId)}/maintenance`
    );
}


export function createToolMaintenance(toolId, data) {
    return spaceApiRequest(
        `/api/tools/${encodeURIComponent(toolId)}/maintenance`,
        {
            method: "POST",
            body: JSON.stringify(data)
        }
    );
}


export function updateToolMaintenance(
    toolId,
    maintenanceId,
    data
) {
    return spaceApiRequest(
        `/api/tools/${encodeURIComponent(toolId)}/maintenance/` +
        encodeURIComponent(maintenanceId),
        {
            method: "PATCH",
            body: JSON.stringify(data)
        }
    );
}


export function deleteToolMaintenance(
    toolId,
    maintenanceId
) {
    return spaceApiRequest(
        `/api/tools/${encodeURIComponent(toolId)}/maintenance/` +
        encodeURIComponent(maintenanceId),
        { method: "DELETE" }
    );
}
