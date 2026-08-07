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
import { initializeRecoveryPage } from "./pages/recovery.js";
import { initializeModuleSettings } from "./pages/settings.js";
import {
    migrateProjectsAfterInventory
} from "./utils/migrationOrchestrator.js";
import { initializePwa } from "./utils/pwa.js";
import {
    createConnectionController,
    setActiveConnectionController
} from "./utils/connectionState.js";
import {
    initializeSpaceSelection
} from "./utils/spaceSelection.js";
import {
    initializeModuleContext,
    isModuleEnabled
} from "./utils/moduleContext.js";
import {
    applyModuleContributions
} from "./utils/modulePresentation.js";

async function initializeOperationalApplication() {
    await initializeSpaceSelection();
    await initializeModuleContext();
    applyModuleContributions();

    const workEnabled = isModuleEnabled("work");
    const inventoryEnabled = isModuleEnabled("inventory");

    // Inventory migration may still be required as continuity plumbing
    // for legacy Project material references even when its UI is disabled.
    const inventoryMigrationResult = (
        inventoryEnabled || workEnabled
    )
        ? await migrateLegacyInventory()
        : null;

    const projectMigrationResult = workEnabled
        ? await migrateProjectsAfterInventory(
            Promise.resolve(inventoryMigrationResult)
        )
        : null;

    const taskMigrationResult = workEnabled
        ? await migrateLegacyTasks(
            Promise.resolve(projectMigrationResult)
        )
        : null;

    initializeRouter();

    const initializers = [
        initializeDashboard({
            workEnabled,
            inventoryEnabled
        }),
        initializeRecoveryPage(),
        initializeModuleSettings(),
        initializeSystemStatus()
    ];

    if (inventoryEnabled) {
        initializers.push(
            initializeInventoryPage(
                Promise.resolve(inventoryMigrationResult)
            )
        );
    }

    if (workEnabled) {
        initializers.push(
            initializeTasksPage(
                Promise.resolve(taskMigrationResult)
            ),
            initializeProjectsPage(
                Promise.resolve(projectMigrationResult),
                { inventoryEnabled }
            )
        );
    }

    await Promise.all(initializers);
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
