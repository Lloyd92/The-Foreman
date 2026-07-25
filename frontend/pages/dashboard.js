function getGreeting(hour) {
    if (hour < 12) {
        return "Good morning";
    }

    if (hour < 18) {
        return "Good afternoon";
    }

    return "Good evening";
}

function formatCurrentDate(date) {
    return new Intl.DateTimeFormat("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric"
    }).format(date);
}

export function initializeDashboard() {
    const greetingElement = document.getElementById("greeting");
    const dateElement = document.getElementById("current-date");

    if (!greetingElement || !dateElement) {
        console.warn("Dashboard greeting elements were not found.");
        return;
    }

    const now = new Date();

    greetingElement.textContent =
        `${getGreeting(now.getHours())}, Tyler.`;

    dateElement.textContent = formatCurrentDate(now);
}