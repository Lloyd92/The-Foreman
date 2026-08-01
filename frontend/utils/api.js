import {
    assertBusinessRequestAllowed,
    isTransportError,
    isTransportStatus,
    verifyTransportFailure
} from "./connectionState.js";


export class BackendApiError extends Error {
    constructor(message, { status = 0, data = null } = {}) {
        super(message);
        this.name = "BackendApiError";
        this.status = status;
        this.data = data;
    }
}


function getBackendErrorMessage(data, status) {
    const detail = data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (
        detail &&
        typeof detail === "object" &&
        typeof detail.message === "string"
    ) {
        return detail.message;
    }

    return `Backend returned status ${status}`;
}


export async function apiResponse(path, options = {}) {
    assertBusinessRequestAllowed();

    const requestOptions = { ...options };
    const headers = new Headers(requestOptions.headers || {});

    if (
        typeof requestOptions.body === "string" &&
        !headers.has("Content-Type")
    ) {
        headers.set("Content-Type", "application/json");
    }

    requestOptions.headers = headers;
    requestOptions.cache = "no-store";

    let response;

    try {
        response = await fetch(path, requestOptions);
    } catch (error) {
        if (isTransportError(error)) {
            await verifyTransportFailure({ error });
        }

        throw error;
    }

    if (isTransportStatus(response.status)) {
        await verifyTransportFailure({ status: response.status });
    }

    if (!response.ok) {
        const data = await response.json().catch(() => null);

        throw new BackendApiError(
            getBackendErrorMessage(data, response.status),
            {
                status: response.status,
                data
            }
        );
    }

    return response;
}


export async function apiRequest(path, options = {}) {
    const response = await apiResponse(path, options);

    if (response.status === 204) {
        return null;
    }

    return response.json().catch(() => null);
}


async function fetchSystemStatus() {
    return apiRequest("/api/status");
}

function setOnlineStatus(data) {
    const statusDot = document.getElementById("status-dot");
    const systemStatus = document.getElementById("system-status");
    const appStatus = document.getElementById("app-status");
    const apiStatus = document.getElementById("api-status");
    const version = document.getElementById("version");
    const footerVersion = document.getElementById("footer-version");

    statusDot?.classList.add("online");

    if (systemStatus) {
        systemStatus.textContent = "System online";
    }

    if (appStatus) {
        appStatus.textContent = data.status.toUpperCase();
    }

    if (apiStatus) {
        apiStatus.textContent = "ONLINE";
    }

    if (version) {
        version.textContent = data.version;
    }

    if (footerVersion) {
        footerVersion.textContent = data.version;
    }
}

function setOfflineStatus() {
    const statusDot = document.getElementById("status-dot");
    const systemStatus = document.getElementById("system-status");
    const appStatus = document.getElementById("app-status");
    const apiStatus = document.getElementById("api-status");

    statusDot?.classList.remove("online");

    if (systemStatus) {
        systemStatus.textContent = "System offline";
    }

    if (appStatus) {
        appStatus.textContent = "OFFLINE";
    }

    if (apiStatus) {
        apiStatus.textContent = "OFFLINE";
    }
}

export async function initializeSystemStatus() {
    try {
        const data = await fetchSystemStatus();
        setOnlineStatus(data);
    } catch (error) {
        console.error("Unable to load system status:", error);
        setOfflineStatus();
    }
}
