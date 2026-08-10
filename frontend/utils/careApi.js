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


export function listCarePlans(params = {}) {
    return spaceApiRequest(
        `/api/care-plans${querySuffix(params)}`
    );
}


export function createCarePlan(data) {
    return spaceApiRequest("/api/care-plans", {
        method: "POST",
        body: JSON.stringify(data)
    });
}


export function updateCarePlan(carePlanId, data) {
    return spaceApiRequest(
        `/api/care-plans/${encodeURIComponent(carePlanId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(data)
        }
    );
}


export function deleteCarePlan(carePlanId) {
    return spaceApiRequest(
        `/api/care-plans/${encodeURIComponent(carePlanId)}`,
        { method: "DELETE" }
    );
}
