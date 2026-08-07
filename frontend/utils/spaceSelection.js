import { BackendApiError } from "./api.js";
import {
    clearPersistedSpaceId,
    persistActiveSpaceId,
    readPersistedSpaceId,
    setActiveSpace
} from "./spaceContext.js";
import {
    getBackendActiveSpace,
    listSpaces
} from "./spacesApi.js";


function validateSpaceList(spaces) {
    if (!Array.isArray(spaces)) {
        throw new TypeError("Space list must be an array.");
    }

    spaces.forEach(space => {
        if (
            !space ||
            typeof space.id !== "string" ||
            !space.id.trim() ||
            typeof space.name !== "string" ||
            !space.name.trim()
        ) {
            throw new TypeError(
                "Every listed Space requires nonempty id and name values."
            );
        }
    });

    return spaces;
}


async function resolveActiveSpace(storage) {
    const persistedSpaceId = readPersistedSpaceId(storage);

    if (!persistedSpaceId) {
        return getBackendActiveSpace();
    }

    try {
        return await getBackendActiveSpace(persistedSpaceId);
    } catch (error) {
        if (
            !(error instanceof BackendApiError) ||
            error.status !== 404
        ) {
            throw error;
        }

        clearPersistedSpaceId(storage);
        return getBackendActiveSpace();
    }
}


function renderSpaceSelector({
    activeSpace,
    spaces,
    storage,
    documentRef,
    windowRef
}) {
    const selector = documentRef?.getElementById(
        "active-space-select"
    );

    if (!selector) {
        throw new Error(
            "The active Space selector is missing from the shell."
        );
    }

    selector.innerHTML = "";

    spaces.forEach(space => {
        const option = documentRef.createElement("option");
        option.value = space.id;
        option.textContent = space.name;
        selector.appendChild(option);
    });

    if (!spaces.some(space => space.id === activeSpace.id)) {
        throw new Error(
            "The active Space is missing from the Space list."
        );
    }

    selector.value = activeSpace.id;
    selector.disabled = false;

    if (selector.dataset.spaceSelectorBound === "true") {
        return;
    }

    selector.dataset.spaceSelectorBound = "true";

    selector.addEventListener("change", event => {
        const selectedSpaceId = event.currentTarget.value;

        if (selectedSpaceId === activeSpace.id) {
            return;
        }

        const selectedSpace = spaces.find(
            space => space.id === selectedSpaceId
        );

        if (!selectedSpace) {
            event.currentTarget.value = activeSpace.id;
            return;
        }

        if (!persistActiveSpaceId(selectedSpace.id, storage)) {
            event.currentTarget.value = activeSpace.id;
            return;
        }

        // Keep the current in-memory context authoritative until the
        // document reloads. This prevents old page state from issuing
        // requests against a newly selected Space.
        event.currentTarget.disabled = true;
        windowRef?.location?.reload?.();
    });
}


export async function initializeSpaceSelection({
    storage = globalThis.localStorage,
    documentRef = globalThis.document,
    windowRef = globalThis.window
} = {}) {
    const activeSpace = setActiveSpace(
        await resolveActiveSpace(storage)
    );
    const spaces = validateSpaceList(
        await listSpaces()
    );

    // Persist the backend-resolved canonical selection when storage
    // is available. Failure to persist does not make HardHead unusable.
    persistActiveSpaceId(activeSpace.id, storage);

    renderSpaceSelector({
        activeSpace,
        spaces,
        storage,
        documentRef,
        windowRef
    });

    return {
        activeSpace,
        spaces
    };
}
