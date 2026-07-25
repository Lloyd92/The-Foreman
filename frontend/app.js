import { initializeRouter } from "./utils/router.js";
import { initializeTasksPage } from "./pages/tasks.js";

function updateGreeting() {
    const hour = new Date().getHours();
    let greeting = "Welcome back";

    if (hour < 12) {
        greeting = "Good morning";
    } else if (hour < 18) {
        greeting = "Good afternoon";
    } else {
        greeting = "Good evening";
    }

    document.getElementById("greeting").textContent =
        `${greeting}, Tyler.`;

    document.getElementById("current-date").textContent =
        new Intl.DateTimeFormat("en-US", {
            weekday: "long",
            month: "long",
            day: "numeric",
            year: "numeric"
        }).format(new Date());
}

async function loadSystemStatus() {
    const statusDot = document.getElementById("status-dot");
    const systemStatus = document.getElementById("system-status");
    const appStatus = document.getElementById("app-status");
    const apiStatus = document.getElementById("api-status");
    const version = document.getElementById("version");
    const footerVersion = document.getElementById("footer-version");

    try {
        const response = await fetch("/api/status");

        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}`);
        }

        const data = await response.json();

        statusDot.classList.add("online");
        systemStatus.textContent = "System online";
        appStatus.textContent = data.status.toUpperCase();
        apiStatus.textContent = "ONLINE";
        version.textContent = data.version;
        footerVersion.textContent = data.version;
    } catch (error) {
        console.error(error);

        systemStatus.textContent = "System offline";
        appStatus.textContent = "OFFLINE";
        apiStatus.textContent = "OFFLINE";
    }
}

initializeRouter();
initializeTasksPage();
updateGreeting();
loadSystemStatus();