import { spaceApiRequest } from "./spaceApi.js";


function jsonOptions(method, data) {
    return {
        method,
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    };
}


export function listLibraryRecords({
    search = "",
    kind = "",
    sortBy = "title",
    sortDirection = "asc"
} = {}) {
    const params = new URLSearchParams();

    if (search.trim()) {
        params.set("search", search.trim());
    }

    if (kind) {
        params.set("kind", kind);
    }

    params.set("sortBy", sortBy);
    params.set("sortDirection", sortDirection);

    return spaceApiRequest(
        `/api/library?${params.toString()}`
    );
}


export function createLibraryRecord(data) {
    return spaceApiRequest(
        "/api/library",
        jsonOptions("POST", data)
    );
}


export function updateLibraryRecord(recordId, data) {
    return spaceApiRequest(
        `/api/library/${recordId}`,
        jsonOptions("PATCH", data)
    );
}


export function deleteLibraryRecord(recordId) {
    return spaceApiRequest(
        `/api/library/${recordId}`,
        { method: "DELETE" }
    );
}
