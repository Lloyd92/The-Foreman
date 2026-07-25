async function fetchSystemStatus() {
    const response = await fetch("/api/status");

    if (!response.ok) {
        throw new Error(
            `Backend returned status ${response.status}`
        );
    }

    return response.json();
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