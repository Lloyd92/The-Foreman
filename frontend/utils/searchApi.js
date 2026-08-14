import { spaceApiRequest } from "./spaceApi.js";


export function universalSearch(query) {
    const params = new URLSearchParams({
        q: String(query ?? "").trim()
    });

    return spaceApiRequest(
        `/api/search?${params.toString()}`
    );
}
