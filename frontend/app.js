import { initializeRouter } from "./utils/router.js";
import { initializeSystemStatus } from "./utils/api.js";
import { initializeDashboard } from "./pages/dashboard.js";
import { initializeTasksPage } from "./pages/tasks.js";
import { initializeInventoryPage } from "./pages/inventory.js";
import { initializeProjectsPage } from "./pages/projects.js";
import {
    migrateProjectsAfterInventory
} from "./utils/migrationOrchestrator.js";
import { initializePwa } from "./utils/pwa.js";

function initializeApplication() {
    initializeRouter();
    initializeDashboard();
    const inventoryMigration = initializeInventoryPage();
    const projectMigration = migrateProjectsAfterInventory(
        inventoryMigration
    );
    initializeTasksPage(projectMigration);
    initializeProjectsPage(projectMigration);
    initializeSystemStatus();
}

initializeApplication();
void initializePwa().catch(error => {
    console.error("Unable to initialize PWA support:", error);
});
