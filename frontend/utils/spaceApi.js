import { apiRequest } from "./api.js";
import {
    getActiveSpaceId,
    SPACE_CONTEXT_HEADER
} from "./spaceContext.js";


export function spaceApiRequest(path, options = {}) {
    const requestOptions = { ...options };
    const headers = new Headers(requestOptions.headers || {});

    // Space ownership comes only from the resolved frontend context.
    // Never retain a stale or caller-supplied Space header.
    headers.delete(SPACE_CONTEXT_HEADER);

    const activeSpaceId = getActiveSpaceId();

    if (activeSpaceId) {
        headers.set(
            SPACE_CONTEXT_HEADER,
            activeSpaceId
        );
    }

    requestOptions.headers = headers;

    return apiRequest(path, requestOptions);
}
