export async function apiRequest(path, options = {}) {
    const requestOptions = { ...options };
    const headers = new Headers(requestOptions.headers || {});

    if (
        requestOptions.body &&
        !headers.has("Content-Type")
    ) {
        headers.set("Content-Type", "application/json");
    }

    requestOptions.headers = headers;

    const response = await fetch(path, requestOptions);

    if (response.status === 204) {
        return null;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const detail = data?.detail;
        const message = typeof detail === "string"
            ? detail
            : `Backend returned status ${response.status}`;

        throw new Error(message);
    }

    return data;
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
