import { apiRequest } from "./api.js";


export function listModules() {
    return apiRequest("/api/modules");
}


export function setModuleEnabled(moduleId, enabled) {
    return apiRequest(
        `/api/modules/${encodeURIComponent(moduleId)}`,
        {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ enabled })
        }
    );
}
