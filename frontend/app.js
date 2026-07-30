import { initializeRouter } from "./utils/router.js";
import { initializeSystemStatus } from "./utils/api.js";
import { initializeDashboard } from "./pages/dashboard.js";
import {
    initializeTasksPage,
    migrateLegacyTasks
} from "./pages/tasks.js";
import {
    initializeInventoryPage,
    migrateLegacyInventory
} from "./pages/inventory.js";
import { initializeProjectsPage } from "./pages/projects.js";
import {
    migrateProjectsAfterInventory
} from "./utils/migrationOrchestrator.js";
import { initializePwa } from "./utils/pwa.js";
import {
    createConnectionController,
    setActiveConnectionController
} from "./utils/connectionState.js";

async function initializeOperationalApplication() {
    const inventoryMigrationResult = await migrateLegacyInventory();
    const projectMigrationResult = await migrateProjectsAfterInventory(
        Promise.resolve(inventoryMigrationResult)
    );
    const taskMigrationResult = await migrateLegacyTasks(
        Promise.resolve(projectMigrationResult)
    );

    initializeRouter();

    await Promise.all([
        initializeDashboard(),
        initializeInventoryPage(
            Promise.resolve(inventoryMigrationResult)
        ),
        initializeTasksPage(Promise.resolve(taskMigrationResult)),
        initializeProjectsPage(Promise.resolve(projectMigrationResult)),
        initializeSystemStatus()
    ]);
}

async function initializeApplication() {
    await initializePwa().catch(error => {
        console.error("Unable to initialize PWA support:", error);
    });

    const connectionController = createConnectionController({
        operationalStartup: initializeOperationalApplication
    });

    setActiveConnectionController(connectionController);
    await connectionController.initialize();
}

void initializeApplication().catch(error => {
    console.error("Unable to initialize The Foreman:", error);
});
