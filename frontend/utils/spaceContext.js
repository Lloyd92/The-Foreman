export const SPACE_CONTEXT_HEADER = "X-Foreman-Space-Id";
export const ACTIVE_SPACE_STORAGE_KEY =
    "foreman-active-space-id-v1";

let activeSpace = null;


function requireSpace(space) {
    if (
        !space ||
        typeof space !== "object" ||
        Array.isArray(space) ||
        typeof space.id !== "string" ||
        !space.id.trim() ||
        typeof space.name !== "string" ||
        !space.name.trim()
    ) {
        throw new TypeError(
            "Active Space requires nonempty id and name values."
        );
    }

    return Object.freeze({ ...space });
}


export function getActiveSpace() {
    return activeSpace;
}


export function getActiveSpaceId() {
    return activeSpace?.id ?? null;
}


export function setActiveSpace(space) {
    activeSpace = requireSpace(space);
    return activeSpace;
}


export function clearActiveSpace() {
    activeSpace = null;
}


export function readPersistedSpaceId(
    storage = globalThis.localStorage
) {
    if (!storage?.getItem) {
        return null;
    }

    try {
        const value = storage.getItem(ACTIVE_SPACE_STORAGE_KEY);

        return typeof value === "string" && value.trim()
            ? value
            : null;
    } catch (error) {
        console.error(
            "Unable to read the persisted active Space:",
            error
        );
        return null;
    }
}


export function persistActiveSpaceId(
    spaceId,
    storage = globalThis.localStorage
) {
    if (
        typeof spaceId !== "string" ||
        !spaceId.trim()
    ) {
        throw new TypeError(
            "Persisted Space ID must be a nonempty string."
        );
    }

    if (!storage?.setItem) {
        return false;
    }

    try {
        storage.setItem(
            ACTIVE_SPACE_STORAGE_KEY,
            spaceId
        );
        return true;
    } catch (error) {
        console.error(
            "Unable to persist the active Space:",
            error
        );
        return false;
    }
}


export function clearPersistedSpaceId(
    storage = globalThis.localStorage
) {
    if (!storage?.removeItem) {
        return false;
    }

    try {
        storage.removeItem(ACTIVE_SPACE_STORAGE_KEY);
        return true;
    } catch (error) {
        console.error(
            "Unable to clear the persisted active Space:",
            error
        );
        return false;
    }
}
