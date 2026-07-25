import { initializeRouter } from "./utils/router.js";
import { initializeSystemStatus } from "./utils/api.js";
import { initializeDashboard } from "./pages/dashboard.js";
import { initializeTasksPage } from "./pages/tasks.js";

function initializeApplication() {
    initializeRouter();
    initializeDashboard();
    initializeTasksPage();
    initializeSystemStatus();
}

initializeApplication();