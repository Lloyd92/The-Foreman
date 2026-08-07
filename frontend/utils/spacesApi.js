import { apiRequest } from "./api.js";
import { SPACE_CONTEXT_HEADER } from "./spaceContext.js";


export function listSpaces() {
    return apiRequest("/api/spaces");
}


export function getBackendActiveSpace(
    requestedSpaceId = null
) {
    const headers = new Headers();

    if (
        typeof requestedSpaceId === "string" &&
        requestedSpaceId.trim()
    ) {
        headers.set(
            SPACE_CONTEXT_HEADER,
            requestedSpaceId
        );
    }

    return apiRequest(
        "/api/spaces/active",
        { headers }
    );
}
